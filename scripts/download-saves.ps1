# download-saves.ps1
# Helper script to download saves from the running GCP Compute Engine VM to the local machine.

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$TerraformDir = Join-Path $ScriptDir "..\terraform"
$SavesDir = Join-Path $ScriptDir "..\saves"

Write-Host "=== Minecraft On-Demand: Download Saves ===" -ForegroundColor Cyan

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

Write-Host "Checking instance status..."
$Status = gcloud compute instances describe $InstanceName --project=$ProjectId --zone=$Zone --format="value(status)" 2>$null
if (-not $?) { $Status = "NOT_FOUND" }

if ($Status -eq "NOT_FOUND") {
    Write-Host "ERROR: Compute instance $InstanceName not found in project $ProjectId, zone $Zone." -ForegroundColor Red
    exit 1
}

if ($Status -ne "RUNNING") {
    Write-Host "Instance is currently $Status. Starting VM to download saves..."
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

Write-Host "Packaging server save files..."
gcloud compute ssh $InstanceName --project=$ProjectId --zone=$Zone --command="cd /mnt/disks/minecraft-data/data && tar -czf /tmp/minecraft-download.tar.gz ."

Write-Host "Downloading package from server..."
$TempTar = "$env:TEMP\minecraft-download-$(Get-Date -UFormat %s).tar.gz"
gcloud compute scp --project=$ProjectId --zone=$Zone "$InstanceName`:/tmp/minecraft-download.tar.gz" $TempTar

Write-Host "Cleaning up server temp file..."
gcloud compute ssh $InstanceName --project=$ProjectId --zone=$Zone --command="rm -f /tmp/minecraft-download.tar.gz"

Write-Host "Extracting package to local saves directory..."
Get-ChildItem -Path $SavesDir -Exclude "README.md" | Remove-Item -Recurse -Force

Push-Location $SavesDir
tar -xzf $TempTar
Pop-Location

Remove-Item $TempTar -Force

Write-Host "=== Download complete! Save files are now in your local saves/ directory. ===" -ForegroundColor Green
