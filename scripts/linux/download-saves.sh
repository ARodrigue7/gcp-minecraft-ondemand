#!/bin/bash
# Helper script to download saves (backup) from the running GCP Compute Engine VM.

set -euo pipefail

# Get directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TERRAFORM_DIR="$SCRIPT_DIR/../../terraform"
SAVES_DIR="$SCRIPT_DIR/../../saves"

echo "=== Minecraft On-Demand: Download Saves (Backup) ==="

# Check if terraform is initialized
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
  echo "Instance is currently $STATUS. Starting VM to access files..."
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

# Create tarball on the server
echo "Creating backup archive on the server..."
gcloud compute ssh "$INSTANCE_NAME" \
  --project="$PROJECT_ID" \
  --zone="$ZONE" \
  --command="sudo tar -czf /tmp/minecraft-saves.tar.gz -C /mnt/disks/minecraft-data/data ."

# Download tarball
echo "Downloading archive..."
TEMP_TAR="/tmp/minecraft-saves-$(date +%s).tar.gz"
gcloud compute scp --project="$PROJECT_ID" --zone="$ZONE" \
  "$INSTANCE_NAME":/tmp/minecraft-saves.tar.gz "$TEMP_TAR"

# Clean up remote tarball
echo "Cleaning up server archive..."
gcloud compute ssh "$INSTANCE_NAME" \
  --project="$PROJECT_ID" \
  --zone="$ZONE" \
  --command="rm -f /tmp/minecraft-saves.tar.gz"

# Extract locally
echo "Extracting backup to $SAVES_DIR..."
# Ensure the saves directory exists
mkdir -p "$SAVES_DIR"
tar -xzf "$TEMP_TAR" -C "$SAVES_DIR"

# Clean up local tarball
rm -f "$TEMP_TAR"

echo "=== Backup complete! Local saves directory has been updated. ==="
