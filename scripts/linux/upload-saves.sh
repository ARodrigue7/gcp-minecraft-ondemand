#!/bin/bash
# Helper script to upload local saves to the running GCP Compute Engine VM.

set -euo pipefail

# Get directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TERRAFORM_DIR="$SCRIPT_DIR/../../terraform"
SAVES_DIR="$SCRIPT_DIR/../../saves"

echo "=== Minecraft On-Demand: Upload Saves ==="

# Check if terraform is initialized and applied
if [ ! -d "$TERRAFORM_DIR/.terraform" ]; then
  echo "ERROR: Terraform is not initialized. Run 'terraform init' in $TERRAFORM_DIR first."
  exit 1
fi

echo "Fetching infrastructure outputs from Terraform..."
PROJECT_ID=$(terraform -chdir="$TERRAFORM_DIR" output -raw project_id)
INSTANCE_NAME=$(terraform -chdir="$TERRAFORM_DIR" output -raw vm_instance_name)
ZONE=$(terraform -chdir="$TERRAFORM_DIR" output -raw zone)

if [ -z "$PROJECT_ID" ] || [ -z "$INSTANCE_NAME" ] || [ -z "$ZONE" ]; then
  echo "ERROR: Could not retrieve outputs from Terraform. Has 'terraform apply' been run?"
  exit 1
fi

echo "Configuration found:"
echo "  - Project:  $PROJECT_ID"
echo "  - Instance: $INSTANCE_NAME"
echo "  - Zone:     $ZONE"

# Check if saves folder has anything other than README.md
FILES_COUNT=$(find "$SAVES_DIR" -mindepth 1 ! -name "README.md" | wc -l)
if [ "$FILES_COUNT" -eq 0 ]; then
  echo "WARNING: No save files found in $SAVES_DIR (excluding README.md)."
  read -p "Are you sure you want to proceed with an empty upload? (y/N) " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Upload canceled."
    exit 0
  fi
fi

# Check VM status
echo "Checking instance status..."
STATUS=$(gcloud compute instances describe "$INSTANCE_NAME" \
  --project="$PROJECT_ID" \
  --zone="$ZONE" \
  --format="value(status)" 2>/dev/null || echo "NOT_FOUND")

if [ "$STATUS" = "NOT_FOUND" ]; then
  echo "ERROR: Compute instance $INSTANCE_NAME not found in project $PROJECT_ID, zone $ZONE."
  exit 1
fi

if [ "$STATUS" != "RUNNING" ]; then
  echo "Instance is currently $STATUS. Starting VM..."
  gcloud compute instances start "$INSTANCE_NAME" --project="$PROJECT_ID" --zone="$ZONE"
  
  echo "Waiting for instance to boot and mount disk..."
  # Wait for SSH to become available and the directory to be ready
  for i in {1..20}; do
    if gcloud compute ssh "$INSTANCE_NAME" \
      --project="$PROJECT_ID" \
      --zone="$ZONE" \
      --command="[ -d /mnt/disks/minecraft-data/data ]" 2>/dev/null; then
      echo "Instance is ready."
      break
    fi
    sleep 3
  done
fi

# Double check if directory is writeable
echo "Checking target directory permissions..."
if ! gcloud compute ssh "$INSTANCE_NAME" \
  --project="$PROJECT_ID" \
  --zone="$ZONE" \
  --command="[ -w /mnt/disks/minecraft-data/data ]" 2>/dev/null; then
  echo "ERROR: Target directory /mnt/disks/minecraft-data/data is not writable or doesn't exist yet. Wait a moment and retry."
  exit 1
fi

# Upload files using a tarball for speed (Minecraft has many small region files)
echo "Packaging local save files..."
TEMP_UPLOAD_TAR="/tmp/minecraft-upload-$(date +%s).tar.gz"

# Package files excluding README.md
cd "$SAVES_DIR"
tar -czf "$TEMP_UPLOAD_TAR" --exclude="README.md" .

echo "Uploading package to server..."
gcloud compute scp --project="$PROJECT_ID" --zone="$ZONE" \
  "$TEMP_UPLOAD_TAR" "$INSTANCE_NAME":/tmp/minecraft-upload.tar.gz

# Clean up local temp file
rm -f "$TEMP_UPLOAD_TAR"

echo "Extracting package on server..."
gcloud compute ssh "$INSTANCE_NAME" \
  --project="$PROJECT_ID" \
  --zone="$ZONE" \
  --command="sudo tar -xzf /tmp/minecraft-upload.tar.gz -C /mnt/disks/minecraft-data/data && sudo chown -R 1000:1000 /mnt/disks/minecraft-data/data && sudo chmod -R 755 /mnt/disks/minecraft-data/data && rm -f /tmp/minecraft-upload.tar.gz"

echo "Files uploaded successfully."

# Restart the Minecraft docker container to pick up changes
echo "Restarting Minecraft server container..."
gcloud compute ssh "$INSTANCE_NAME" \
  --project="$PROJECT_ID" \
  --zone="$ZONE" \
  --command="docker restart minecraft"

echo "=== Upload complete! Minecraft server has been updated and restarted. ==="

