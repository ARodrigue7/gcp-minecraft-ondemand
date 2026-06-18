# upload-saves.ps1
# Helper script to upload local saves to the running GCP Compute Engine VM.

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$TerraformDir = Join-Path $ScriptDir "..\terraform"
$SavesDir = Join-Path $ScriptDir "..\saves"

Write-Host "=== Minecraft On-Demand: Upload Saves ===" -ForegroundColor Cyan

if (-not (Test-Path (Join-Path $TerraformDir ".terraform"))) {
    Write-Host "ERROR: Terraform is not initialized. Run 'terraform init' in $TerraformDir first." -ForegroundColor Red
    exit 1
}

Write-Host "Fetching infrastructure outputs from Terraform..."
$ProjectId = (terraform -chdir=$TerraformDir output -raw project_id)
$InstanceName = (terraform -chdir=$TerraformDir output -raw vm_instance_name)
$Zone = (terraform -chdir=$TerraformDir output -raw zone)

if ([string]::IsNullOrWhiteSpace($ProjectId) -or [string]::IsNullOrWhiteSpace($InstanceName) -or [string]::IsNullOrWhiteSpace($Zone)) {
    Write-Host "ERROR: Could not retrieve outputs from Terraform. Has 'terraform apply' been run?" -ForegroundColor Red
    exit 1
}

Write-Host "Configuration found:"
Write-Host "  - Project:  $ProjectId"
Write-Host "  - Instance: $InstanceName"
Write-Host "  - Zone:     $Zone"

# Check if saves folder has anything other than README.md
$Files = Get-ChildItem -Path $SavesDir -Exclude "README.md"
if ($Files.Count -eq 0) {
    Write-Host "WARNING: No save files found in $SavesDir (excluding README.md)." -ForegroundColor Yellow
    $Response = Read-Host "Are you sure you want to proceed with an empty upload? (y/N)"
    if ($Response -notmatch "^[Yy]") {
        Write-Host "Upload canceled."
        exit 0
    }
}

Write-Host "Checking instance status..."
$Status = gcloud compute instances describe $InstanceName --project=$ProjectId --zone=$Zone --format="value(status)" 2>$null
if (-not $?) { $Status = "NOT_FOUND" }

if ($Status -eq "NOT_FOUND") {
    Write-Host "ERROR: Compute instance $InstanceName not found in project $ProjectId, zone $Zone." -ForegroundColor Red
    exit 1
}

if ($Status -ne "RUNNING") {
    Write-Host "Instance is currently $Status. Starting VM..."
    gcloud compute instances start $InstanceName --project=$ProjectId --zone=$Zone
    
    Write-Host "Waiting for instance to boot and mount disk..."
    $Ready = $false
    for ($i = 1; $i -le 20; $i++) {
        gcloud compute ssh $InstanceName --project=$ProjectId --zone=$Zone --command="[ -d /mnt/disks/minecraft-data/data ]" 2>$null
        if ($?) {
            Write-Host "Instance is ready."
            $Ready = $true
            break
        }
        Start-Sleep -Seconds 3
    }
    if (-not $Ready) {
        Write-Host "ERROR: Timed out waiting for instance to be ready." -ForegroundColor Red
        exit 1
    }
}

Write-Host "Checking target directory permissions..."
gcloud compute ssh $InstanceName --project=$ProjectId --zone=$Zone --command="[ -w /mnt/disks/minecraft-data/data ]" 2>$null
if (-not $?) {
    Write-Host "ERROR: Target directory /mnt/disks/minecraft-data/data is not writable or doesn't exist yet. Wait a moment and retry." -ForegroundColor Red
    exit 1
}

Write-Host "Packaging local save files..."
$TempTar = "$env:TEMP\minecraft-upload-$(Get-Date -UFormat %s).tar.gz"

Push-Location $SavesDir
tar -czf $TempTar --exclude="README.md" .
Pop-Location

Write-Host "Uploading package to server..."
gcloud compute scp --project=$ProjectId --zone=$Zone $TempTar "$InstanceName`:/tmp/minecraft-upload.tar.gz"

Remove-Item $TempTar -Force

Write-Host "Extracting package on server..."
gcloud compute ssh $InstanceName --project=$ProjectId --zone=$Zone --command="sudo tar -xzf /tmp/minecraft-upload.tar.gz -C /mnt/disks/minecraft-data/data && sudo chown -R 1000:1000 /mnt/disks/minecraft-data/data && sudo chmod -R 755 /mnt/disks/minecraft-data/data && rm -f /tmp/minecraft-upload.tar.gz"

Write-Host "Files uploaded successfully."

Write-Host "Restarting Minecraft server container..."
gcloud compute ssh $InstanceName --project=$ProjectId --zone=$Zone --command="docker restart minecraft"

Write-Host "=== Upload complete! Minecraft server has been updated and restarted. ===" -ForegroundColor Green
