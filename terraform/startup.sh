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
  mount -o discard,defaults "$DISK_PATH" "$MOUNT_DIR"
fi

# Add to fstab if not present
if ! grep -q "$MOUNT_DIR" /etc/fstab; then
  echo "$DISK_PATH $MOUNT_DIR ext4 discard,defaults,nofail 0 2" >> /etc/fstab
fi

# Prepare directories with permissive access for the Docker container
mkdir -p "$MOUNT_DIR/data"
chmod -R 777 "$MOUNT_DIR/data"

# Run the Minecraft server container (only if it doesn't already exist)
if ! docker ps -a --format '{{.Names}}' | grep -Eq "^minecraft\$"; then
  docker run -d \
    --name minecraft \
    --restart always \
    -p 25565:25565 \
    -v "$MOUNT_DIR/data:/data" \
    -e EULA=TRUE \
    -e TYPE=PAPER \
    -e VERSION=LATEST \
    -e MEMORY=3G \
    itzg/minecraft-server
fi

# Create watchdog script in the persistent, executable disk directory
WATCHDOG_SCRIPT="/mnt/disks/minecraft-data/minecraft-watchdog.sh"

cat <<'EOF' > /mnt/disks/minecraft-data/minecraft-watchdog.sh
#!/bin/bash
PORT=25565
IDLE_LIMIT=${idle_timeout_seconds}
INITIAL_DELAY=600 # 10 minutes startup grace period

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

# Get uptime in seconds
UPTIME=$(cat /proc/uptime | awk '{print $1}')
UPTIME=$${UPTIME%.*}

if [ $UPTIME -lt $INITIAL_DELAY ]; then
  echo "Uptime $UPTIME is less than initial delay $INITIAL_DELAY. Skipping check."
  exit 0
fi

# Count active TCP connections on port 25565
ACTIVE_CONNS=$(ss -t -H state established '( sport = :'$PORT' )' | wc -l)
echo "Active connections: $ACTIVE_CONNS"

if [ "$ACTIVE_CONNS" -gt 0 ]; then
  rm -f /tmp/minecraft-idle-since
  echo "Connections active. Idle timer reset."
else
  if [ ! -f /tmp/minecraft-idle-since ]; then
    date +%s > /tmp/minecraft-idle-since
    echo "No connections. Idle timer started."
  else
    IDLE_SINCE=$(cat /tmp/minecraft-idle-since)
    NOW=$(date +%s)
    IDLE_TIME=$((NOW - IDLE_SINCE))
    echo "Idle for $IDLE_TIME seconds."
    if [ $IDLE_TIME -ge $IDLE_LIMIT ]; then
      echo "Minecraft server has been idle for $IDLE_TIME seconds. Shutting down VM..."
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
