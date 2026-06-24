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
else
  echo "Resizing $DISK_PATH if needed..."
  resize2fs "$DISK_PATH" || true
fi

# Mount disk
mkdir -p "$MOUNT_DIR"
if ! mountpoint -q "$MOUNT_DIR"; then
  echo "Mounting $DISK_PATH to $MOUNT_DIR..."
  mount -o discard,defaults,noatime "$DISK_PATH" "$MOUNT_DIR" || echo "WARNING: Mount command failed. The disk might already be mounted by systemd."
fi

# Add to fstab if not present
if ! grep -q "$MOUNT_DIR" /etc/fstab; then
  echo "$DISK_PATH $MOUNT_DIR ext4 discard,defaults,noatime,nofail 0 2" >> /etc/fstab
  systemctl daemon-reload || true
fi

# Prepare directories with container user ownership (uid/gid 1000) and secure permissions
mkdir -p "$MOUNT_DIR/data"
chown -R 1000:1000 "$MOUNT_DIR/data"
chmod -R 755 "$MOUNT_DIR/data"

# Update Dynamic DNS if using third-party dynamic DNS providers (DuckDNS or Dynu) on boot
if [ "${dns_provider}" = "duckdns" ] && [ -n "${dns_api_token}" ]; then
  # DuckDNS subdomain is the part of domain_name before .duckdns.org
  SUBDOMAIN=$(echo "${domain_name}" | cut -d'.' -f1)
  echo "Updating DuckDNS subdomain '$SUBDOMAIN'..."
  curl -s "https://www.duckdns.org/update?domains=$SUBDOMAIN&token=${dns_api_token}" || echo "WARNING: DuckDNS boot update failed."
elif [ "${dns_provider}" = "dynu" ] && [ -n "${dns_api_token}" ]; then
  echo "Updating Dynu domain '${domain_name}'..."
  curl -s "https://api.dynu.com/nic/update?hostname=${domain_name}&password=${dns_api_token}" || echo "WARNING: Dynu boot update failed."
fi

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
  -e ENABLE_WHITELIST=TRUE \
  -e ENFORCE_WHITELIST=TRUE \
  itzg/minecraft-server


# Render dynamic configuration variables for the watchdog script
cat <<EOF > /mnt/disks/minecraft-data/watchdog-config.env
INSTANCE_NAME="${instance_name}"
DISK_AUTO_EXPAND=${disk_auto_expand}
DISK_AUTO_EXPAND_MAX_GB=${disk_auto_expand_max_gb}
DISK_AUTO_EXPAND_THRESHOLD=${disk_auto_expand_threshold}
DNS_PROVIDER="${dns_provider}"
DOMAIN_NAME="${domain_name}"
DNS_API_TOKEN="${dns_api_token}"
EOF

# Create watchdog script in the persistent, executable disk directory
WATCHDOG_SCRIPT="/mnt/disks/minecraft-data/minecraft-watchdog.sh"

cat <<'EOF' > /mnt/disks/minecraft-data/minecraft-watchdog.sh
#!/bin/bash
PORT=25565
IDLE_LIMIT=${idle_timeout_seconds}
INITIAL_DELAY=600 # 10 minutes startup grace period

# Sourcing dynamic configuration if present
if [ -f /mnt/disks/minecraft-data/watchdog-config.env ]; then
  source /mnt/disks/minecraft-data/watchdog-config.env
fi

check_and_expand_disk() {
  if [ "$${DISK_AUTO_EXPAND:-false}" != "true" ]; then
    return 0
  fi

  DISK_DEV="/dev/disk/by-id/google-minecraft-data"
  MOUNT_POINT="/mnt/disks/minecraft-data"
  
  if [ ! -b "$DISK_DEV" ] || [ ! -d "$MOUNT_POINT" ]; then
    echo "ERROR: Disk device or mount point not found for scaling check."
    return 1
  fi

  # Get percentage disk usage
  USAGE_PERCENT=$(df -h "$MOUNT_POINT" | awk 'NR==2 {print $5}' | tr -d '%')
  echo "Current disk usage: $USAGE_PERCENT% (Threshold: $${DISK_AUTO_EXPAND_THRESHOLD:-80}%)"

  if [ "$USAGE_PERCENT" -ge "$${DISK_AUTO_EXPAND_THRESHOLD:-80}" ]; then
    echo "Disk usage of $USAGE_PERCENT% exceeds threshold of $${DISK_AUTO_EXPAND_THRESHOLD:-80}%. Initiating auto-expansion..."
    
    # Get current disk size in GB
    CURRENT_SIZE_BYTES=$(blockdev --getsize64 "$DISK_DEV")
    CURRENT_SIZE_GB=$((CURRENT_SIZE_BYTES / 1024 / 1024 / 1024))
    
    # Expand by 5GB
    NEW_SIZE_GB=$((CURRENT_SIZE_GB + 5))
    MAX_SIZE_GB=$${DISK_AUTO_EXPAND_MAX_GB:-25}
    
    if [ "$NEW_SIZE_GB" -gt "$MAX_SIZE_GB" ]; then
      echo "WARNING: Target expansion size ($NEW_SIZE_GB GB) exceeds configured maximum disk limit ($MAX_SIZE_GB GB). Capping to $MAX_SIZE_GB GB."
      NEW_SIZE_GB=$MAX_SIZE_GB
    fi
    
    if [ "$NEW_SIZE_GB" -gt "$CURRENT_SIZE_GB" ]; then
      VM_ZONE_FULL=$(curl -s -H "Metadata-Flavor: Google" http://metadata.google.internal/computeMetadata/v1/instance/zone)
      VM_ZONE=$(basename "$VM_ZONE_FULL")
      DISK_NAME="$${INSTANCE_NAME}-data"
      
      echo "Calling GCP API to resize disk $DISK_NAME to $NEW_SIZE_GB GB in zone $VM_ZONE..."
      if gcloud compute disks resize "$DISK_NAME" --size="$NEW_SIZE_GB" --zone="$VM_ZONE" --quiet; then
        echo "GCP disk successfully resized to $NEW_SIZE_GB GB. Resizing local filesystem..."
        # Wait a moment for OS/kernel to register change
        sleep 2
        if resize2fs "$DISK_DEV"; then
          echo "Local filesystem successfully expanded to match new disk size!"
        else
          echo "ERROR: resize2fs failed."
        fi
      else
        echo "ERROR: gcloud compute disks resize command failed."
      fi
    else
      echo "Disk is already at the maximum allowed size ($CURRENT_SIZE_GB GB). Cannot expand further."
    fi
  fi
}

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

# Run the disk expansion check
check_and_expand_disk || echo "WARNING: Disk expansion check failed"

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
