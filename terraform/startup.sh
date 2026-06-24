#!/bin/bash
set -euo pipefail

echo "=== Starting Minecraft VM setup ==="

DISK_PATH="/dev/disk/by-id/google-minecraft-data"
MOUNT_DIR="/mnt/disks/minecraft-data"

# Wait for disk device to appear
for i in {1..30}; do
  if [ -b "$DISK_PATH" ]; then
    break
  fi
  echo "Waiting for disk device $DISK_PATH..."
  sleep 1
done

if [ ! -b "$DISK_PATH" ]; then
  echo "ERROR: Disk $DISK_PATH not found."
  exit 1
fi

# Check and format disk if no filesystem exists
if ! blkid "$DISK_PATH"; then
  echo "Formatting $DISK_PATH with ext4..."
  mkfs.ext4 -m 0 -E lazy_itable_init=0,lazy_journal_init=0,discard "$DISK_PATH"
fi

# Mount disk
mkdir -p "$MOUNT_DIR"
if ! mountpoint -q "$MOUNT_DIR"; then
  # ⚡ Bolt Optimization: Add noatime,nodiratime to reduce disk write cycles and GCP IOPS cost
  mount -o discard,defaults,noatime,nodiratime "$DISK_PATH" "$MOUNT_DIR"
fi

# Add to fstab if not present
if ! grep -q "$MOUNT_DIR" /etc/fstab; then
  # ⚡ Bolt Optimization: Persist noatime,nodiratime to fstab to minimize write ops
  echo "$DISK_PATH $MOUNT_DIR ext4 discard,defaults,noatime,nodiratime,nofail 0 2" >> /etc/fstab
fi

# Prepare directories with container user ownership (uid/gid 1000) and secure permissions
mkdir -p "$MOUNT_DIR/data"
chown -R 1000:1000 "$MOUNT_DIR/data"
chmod -R 755 "$MOUNT_DIR/data"

# Run the Minecraft server container (recreate on boot to ensure fresh config/logs)
if docker ps -a --format '{{.Names}}' | grep -Eq "^minecraft\$"; then
  echo "Removing existing minecraft container..."
  docker stop minecraft || true
  docker rm minecraft || true
fi

echo "Starting fresh Minecraft server container..."
docker run -d \
  --name minecraft \
  --restart always \
  --log-driver=gcplogs \
  -p 25565:25565 \
  -v "$MOUNT_DIR/data:/data" \
  -e EULA=TRUE \
  -e TYPE=PAPER \
  -e VERSION=${minecraft_version} \
  -e MEMORY=3G \
  itzg/minecraft-server


# Create watchdog script in the persistent, executable disk directory
WATCHDOG_SCRIPT="/mnt/disks/minecraft-data/minecraft-watchdog.sh"

cat <<'EOF' > /mnt/disks/minecraft-data/minecraft-watchdog.sh
#!/bin/bash
PORT=25565
IDLE_LIMIT=${idle_timeout_seconds}
INITIAL_DELAY=600 # 10 minutes startup grace period

create_backup() {
  echo "Starting Minecraft backup sequence..."
  if docker ps --format '{{.Names}}' | grep -Eq "^minecraft$"; then
    echo "Freezing auto-saves..."
    docker exec minecraft mc-send-to-rcon save-off >/dev/null 2>&1 || true
    docker exec minecraft mc-send-to-rcon save-all flush >/dev/null 2>&1 || true
    sleep 2
    
    echo "Creating world archive..."
    tar -czf /tmp/rolling_backup.tar.gz -C /mnt/disks/minecraft-data/data world world_nether world_the_end >/dev/null 2>&1 || true
    
    echo "Resuming auto-saves..."
    docker exec minecraft mc-send-to-rcon save-on >/dev/null 2>&1 || true
    
    if [ -f /tmp/rolling_backup.tar.gz ]; then
      echo "Uploading backup to GCS..."
      gsutil cp /tmp/rolling_backup.tar.gz gs://${backups_bucket}/rolling_backup.tar.gz >/dev/null 2>&1 || true
      rm -f /tmp/rolling_backup.tar.gz
      echo "Backup uploaded successfully!"
    else
      echo "ERROR: Backup archive creation failed."
    fi
  else
    echo "ERROR: Minecraft container is not running, skipping backup."
  fi
}

# Sync approved whitelist from GCE instance metadata attributes
APPROVED_WHITELIST=$(curl -s -f -H "Metadata-Flavor: Google" http://metadata.google.internal/computeMetadata/v1/instance/attributes/approved-whitelist || echo "")
if [ -n "$APPROVED_WHITELIST" ]; then
  IFS=',' read -ra PLAYERS <<< "$APPROVED_WHITELIST"
  if docker ps --format '{{.Names}}' | grep -Eq "^minecraft$"; then
    for player in "$${PLAYERS[@]}"; do
      if [ -n "$player" ]; then
        echo "Syncing whitelist for player: $player"
        docker exec minecraft mc-send-to-rcon whitelist add "$player" >/dev/null 2>&1 || true
      fi
    done
  fi
fi

# Process pending admin commands from GCE metadata
PENDING_COMMANDS=$(curl -s -f -H "Metadata-Flavor: Google" http://metadata.google.internal/computeMetadata/v1/instance/attributes/pending-commands || echo "")
if [ -n "$PENDING_COMMANDS" ]; then
  echo "Found pending admin commands: $PENDING_COMMANDS"
  IFS=',' read -ra CMDS <<< "$PENDING_COMMANDS"
  for cmd in "$${CMDS[@]}"; do
    if [ -n "$cmd" ]; then
      cmd=$(echo "$cmd" | xargs)
      echo "Executing command: $cmd"
      if [ "$cmd" = "backup" ]; then
        create_backup
      else
        docker exec minecraft mc-send-to-rcon "$cmd" >/dev/null 2>&1 || true
      fi
    fi
  done
  
  VM_NAME=$(curl -s -H "Metadata-Flavor: Google" http://metadata.google.internal/computeMetadata/v1/instance/name)
  VM_ZONE_FULL=$(curl -s -H "Metadata-Flavor: Google" http://metadata.google.internal/computeMetadata/v1/instance/zone)
  VM_ZONE=$(basename "$VM_ZONE_FULL")
  echo "Clearing pending commands metadata..."
  gcloud compute instances add-metadata "$VM_NAME" --zone="$VM_ZONE" --metadata=pending-commands="" >/dev/null 2>&1 || true
fi

# Get uptime in seconds
UPTIME=$(cat /proc/uptime | awk '{print $1}')
UPTIME=$${UPTIME%.*}

if [ $UPTIME -lt $INITIAL_DELAY ]; then
  echo "Uptime $UPTIME is less than initial delay $INITIAL_DELAY. Skipping check."
  exit 0
fi

# Count active players online using RCON command
ONLINE_PLAYERS=0
PLAYER_LIST="none"
if docker ps --format '{{.Names}}' | grep -Eq "^minecraft$"; then
  RCON_OUT=$(docker exec minecraft mc-send-to-rcon list 2>/dev/null || echo "")
  if [[ "$RCON_OUT" =~ There\ are\ ([0-9]+) ]]; then
    ONLINE_PLAYERS="$${BASH_REMATCH[1]}"
  fi
  if [ "$ONLINE_PLAYERS" -gt 0 ] && [[ "$RCON_OUT" =~ online:\ (.*) ]]; then
    PLAYER_LIST="$${BASH_REMATCH[1]}"
    PLAYER_LIST=$(echo "$PLAYER_LIST" | tr -d ' ')
  fi
fi
echo "Active players: $ONLINE_PLAYERS ($PLAYER_LIST)"

# Sync online-players list to GCE metadata
VM_NAME=$(curl -s -H "Metadata-Flavor: Google" http://metadata.google.internal/computeMetadata/v1/instance/name)
VM_ZONE_FULL=$(curl -s -H "Metadata-Flavor: Google" http://metadata.google.internal/computeMetadata/v1/instance/zone)
VM_ZONE=$(basename "$VM_ZONE_FULL")
gcloud compute instances add-metadata "$VM_NAME" --zone="$VM_ZONE" --metadata=online-players="$PLAYER_LIST" >/dev/null 2>&1 || true

if [ "$ONLINE_PLAYERS" -gt 0 ]; then
  rm -f /tmp/minecraft-idle-since
  echo "Players active. Idle timer reset."
else
  if [ ! -f /tmp/minecraft-idle-since ]; then
    date +%s > /tmp/minecraft-idle-since
    echo "No players online. Idle timer started."
  else
    IDLE_SINCE=$(cat /tmp/minecraft-idle-since)
    NOW=$(date +%s)
    IDLE_TIME=$((NOW - IDLE_SINCE))
    echo "Idle for $IDLE_TIME seconds."
    if [ $IDLE_TIME -ge $IDLE_LIMIT ]; then
      echo "Minecraft server has been idle for $IDLE_TIME seconds. Auto-backing up before shutdown..."
      create_backup
      docker stop -t 30 minecraft
      sudo poweroff
    fi
  fi
fi
EOF

chmod +x /mnt/disks/minecraft-data/minecraft-watchdog.sh

# Create systemd service for watchdog
cat <<'EOF' > /etc/systemd/system/minecraft-watchdog.service
[Unit]
Description=Minecraft Idle Watchdog Service
After=docker.service

[Service]
Type=oneshot
ExecStart=/mnt/disks/minecraft-data/minecraft-watchdog.sh
EOF

# Create systemd timer for watchdog (runs every minute)
cat <<'EOF' > /etc/systemd/system/minecraft-watchdog.timer
[Unit]
Description=Run Minecraft Idle Watchdog every minute

[Timer]
OnBootSec=5min
OnUnitActiveSec=1min

[Install]
WantedBy=timers.target
EOF

# Reload systemd and enable timer
systemctl daemon-reload
systemctl enable minecraft-watchdog.timer
systemctl start minecraft-watchdog.timer

echo "=== Minecraft VM setup completed ==="
