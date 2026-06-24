# Terraform Provider and Main Infrastructure Definitions

terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.0"
    }
    local = {
      source  = "hashicorp/local"
      version = "~> 2.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

# ==========================================
# 💾 PERSISTENT STORAGE
# ==========================================

resource "google_compute_disk" "minecraft_data" {
  name = "${var.instance_name}-data"
  type = "pd-balanced"
  zone = var.zone
  size = var.disk_size_gb
}

# Storage Bucket for versioned backups
resource "google_storage_bucket" "minecraft_backups" {
  name                        = "${var.project_id}-backups"
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = true

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      num_newer_versions = 5
      with_state         = "ARCHIVED"
    }
    action {
      type = "Delete"
    }
  }
}

# ==========================================
# 🖥️ COMPUTE ENGINE VM (MINECRAFT SERVER)
# ==========================================

# Dedicated Service Account for the Minecraft VM
resource "google_service_account" "minecraft_sa" {
  account_id   = "${var.instance_name}-sa"
  display_name = "Minecraft VM Service Account"
}

# Grant VM permissions to write logs
resource "google_project_iam_member" "vm_logging" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.minecraft_sa.email}"
}

# Grant VM permissions to write metrics
resource "google_project_iam_member" "vm_monitoring" {
  project = var.project_id
  role    = "roles/monitoring.metricWriter"
  member  = "serviceAccount:${google_service_account.minecraft_sa.email}"
}

# Grant VM permissions to write backups to GCS
resource "google_storage_bucket_iam_member" "vm_backups_admin" {
  bucket = google_storage_bucket.minecraft_backups.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.minecraft_sa.email}"
}

# Grant VM permissions to modify metadata (to clear command queue)
resource "google_project_iam_member" "vm_compute_admin" {
  project = var.project_id
  role    = "roles/compute.instanceAdmin.v1"
  member  = "serviceAccount:${google_service_account.minecraft_sa.email}"
}

# Firewall Rule to allow Minecraft traffic (Port 25565)
resource "google_compute_firewall" "minecraft_firewall" {
  name    = "allow-minecraft"
  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["25565"]
  }

  target_tags   = ["minecraft-server"]
  source_ranges = ["0.0.0.0/0"]
}

# Compute Engine Instance running Container-Optimized OS
resource "google_compute_instance" "minecraft" {
  name         = var.instance_name
  machine_type = var.machine_type
  zone         = var.zone
  tags         = ["minecraft-server"]

  boot_disk {
    initialize_params {
      image = "cos-cloud/cos-stable"
    }
  }

  # Attached persistent data disk
  attached_disk {
    source      = google_compute_disk.minecraft_data.id
    device_name = "minecraft-data"
    mode        = "READ_WRITE"
  }

  network_interface {
    network = "default"
    access_config {
      # Ephemeral public IP address (avoids cost of idle static IP)
    }
  }

  metadata = {
    # Render the startup script template containing the watchdog configuration
    startup-script = templatefile("${path.module}/startup.sh", {
      idle_timeout_seconds       = var.idle_timeout_seconds
      backups_bucket             = google_storage_bucket.minecraft_backups.name
      minecraft_version          = var.minecraft_version
      instance_name              = var.instance_name
      disk_auto_expand           = var.disk_auto_expand
      disk_auto_expand_max_gb    = var.disk_auto_expand_max_gb
      disk_auto_expand_threshold = var.disk_auto_expand_threshold
      dns_provider               = var.dns_provider
      domain_name                = var.domain_name
      dns_api_token              = var.dns_api_token
    })
    approved-whitelist = ""
    pending-whitelist  = ""
    pending-commands   = ""
    online-players     = ""
    backup-status      = ""
  }

  service_account {
    email  = google_service_account.minecraft_sa.email
    scopes = ["cloud-platform"]
  }

  lifecycle {
    ignore_changes = [
      metadata["approved-whitelist"],
      metadata["pending-whitelist"],
      metadata["pending-commands"],
      metadata["online-players"],
      metadata["backup-status"]
    ]
  }
}

# ==========================================
# 🌐 CLOUD DNS CONFIGURATION
# ==========================================

# Managed Public DNS Zone for mc.yourdomain.com (conditional)
resource "google_dns_managed_zone" "minecraft_zone" {
  count       = var.dns_provider == "google" ? 1 : 0
  name        = var.dns_zone_name
  dns_name    = "${var.domain_name}."
  description = "Managed zone for Minecraft server on-demand resolution"
  visibility  = "public"

  cloud_logging_config {
    enable_logging = true
  }
}

# Placeholder A-Record pointing to 127.0.0.1 initially (conditional)
resource "google_dns_record_set" "minecraft_a_record" {
  count        = var.dns_provider == "google" ? 1 : 0
  name         = google_dns_managed_zone.minecraft_zone[0].dns_name
  managed_zone = google_dns_managed_zone.minecraft_zone[0].name
  type         = "A"
  ttl          = 60
  rrdatas      = ["127.0.0.1"]

  lifecycle {
    ignore_changes = [rrdatas]
  }
}

# ==========================================
# 📣 LOG ROUTING & PUBSUB
# ==========================================

# Pub/Sub Topic for DNS query event alerts
resource "google_pubsub_topic" "dns_query_topic" {
  name = "minecraft-dns-query-topic"
}

# Log Sink to route DNS query logs for mc.yourdomain.com to the Pub/Sub topic
resource "google_logging_project_sink" "dns_query_sink" {
  count                  = (var.enable_dns_autostart && var.dns_provider == "google") ? 1 : 0
  name                   = "minecraft-dns-query-sink"
  destination            = "pubsub.googleapis.com/${google_pubsub_topic.dns_query_topic.id}"
  filter                 = "resource.type=\"dns_query\" AND jsonPayload.queryName=\"${var.domain_name}.\""
  unique_writer_identity = true
}

# IAM policy to allow the Log Sink to publish events to Pub/Sub
resource "google_pubsub_topic_iam_member" "dns_query_sink_publisher" {
  count  = (var.enable_dns_autostart && var.dns_provider == "google") ? 1 : 0
  topic  = google_pubsub_topic.dns_query_topic.name
  role   = "roles/pubsub.publisher"
  member = google_logging_project_sink.dns_query_sink[0].writer_identity
}

# ==========================================
# ⚡ CLOUD FUNCTION (AUTOSTART & DNS UPDATE)
# ==========================================

# Storage Bucket to stage Cloud Function source zip
resource "google_storage_bucket" "function_bucket" {
  name                        = "${var.project_id}-cf-source"
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = true
}

# Package the function code
data "archive_file" "function_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../functions"
  output_path = "${path.module}/files/function.zip"
}

# Upload zipped source code
resource "google_storage_bucket_object" "function_zip_object" {
  name   = "function-${data.archive_file.function_zip.output_md5}.zip"
  bucket = google_storage_bucket.function_bucket.name
  source = data.archive_file.function_zip.output_path
}

# Service Account for the Cloud Function
resource "google_service_account" "cf_sa" {
  account_id   = "minecraft-cf-sa"
  display_name = "Minecraft Cloud Function Service Account"
}

# Custom IAM Role for Cloud Function to manage the Minecraft VM
resource "google_project_iam_custom_role" "cf_compute_controller" {
  role_id     = "minecraftInstanceController"
  title       = "Minecraft Instance Controller"
  description = "Allows getting, starting, and setting metadata on the Minecraft VM instance"
  permissions = [
    "compute.instances.get",
    "compute.instances.start",
    "compute.instances.setMetadata"
  ]
}

# Grant Cloud Function permissions to start/stop the GCE instance (using custom role)
resource "google_project_iam_member" "cf_compute" {
  project = var.project_id
  role    = google_project_iam_custom_role.cf_compute_controller.id
  member  = "serviceAccount:${google_service_account.cf_sa.email}"
}

# Grant Cloud Function service account user permission on the VM service account (required to update VM metadata)
resource "google_service_account_iam_member" "cf_sa_user" {
  service_account_id = google_service_account.minecraft_sa.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.cf_sa.email}"
}

# Grant Cloud Function permissions to update DNS A-Records
resource "google_project_iam_member" "cf_dns" {
  project = var.project_id
  role    = "roles/dns.admin"
  member  = "serviceAccount:${google_service_account.cf_sa.email}"
}

# Grant Cloud Function permissions to list/read backups
resource "google_storage_bucket_iam_member" "cf_backups_viewer" {
  bucket = google_storage_bucket.minecraft_backups.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.cf_sa.email}"
}

# Grant Cloud Function permissions to read container logs from Cloud Logging
resource "google_project_iam_member" "cf_logging_viewer" {
  project = var.project_id
  role    = "roles/logging.viewer"
  member  = "serviceAccount:${google_service_account.cf_sa.email}"
}

# Grant Cloud Run invoker permission to the function service account (for Eventarc Pub/Sub trigger)
resource "google_project_iam_member" "cf_run_invoker" {
  project = var.project_id
  role    = "roles/run.invoker"
  member  = "serviceAccount:${google_service_account.cf_sa.email}"
}

# Grant Eventarc event receiver permission to the function service account (for Eventarc Pub/Sub trigger)
resource "google_project_iam_member" "cf_event_receiver" {
  project = var.project_id
  role    = "roles/eventarc.eventReceiver"
  member  = "serviceAccount:${google_service_account.cf_sa.email}"
}

# ==========================================
# 🔐 SECRET MANAGER (For Sensitive Configurations)
# ==========================================

resource "google_secret_manager_secret" "whitelist_secret" {
  secret_id = "minecraft-whitelist-secret"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "whitelist_secret_val" {
  secret      = google_secret_manager_secret.whitelist_secret.id
  secret_data = random_id.whitelist_secret.hex
}

resource "google_secret_manager_secret" "admin_passcode" {
  secret_id = "minecraft-admin-passcode"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "admin_passcode_val" {
  secret      = google_secret_manager_secret.admin_passcode.id
  secret_data = var.admin_passcode
}

resource "google_secret_manager_secret" "discord_webhook" {
  secret_id = "minecraft-discord-webhook"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "discord_webhook_val" {
  secret      = google_secret_manager_secret.discord_webhook.id
  secret_data = var.discord_webhook_url
}

resource "google_secret_manager_secret" "dns_api_token" {
  secret_id = "minecraft-dns-api-token"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "dns_api_token_val" {
  secret      = google_secret_manager_secret.dns_api_token.id
  secret_data = var.dns_api_token
}

# IAM Permissions for Service Account to access these secrets
resource "google_secret_manager_secret_iam_member" "cf_sa_whitelist_accessor" {
  secret_id = google_secret_manager_secret.whitelist_secret.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.cf_sa.email}"
}

resource "google_secret_manager_secret_iam_member" "cf_sa_admin_accessor" {
  secret_id = google_secret_manager_secret.admin_passcode.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.cf_sa.email}"
}

resource "google_secret_manager_secret_iam_member" "cf_sa_discord_accessor" {
  secret_id = google_secret_manager_secret.discord_webhook.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.cf_sa.email}"
}

resource "google_secret_manager_secret_iam_member" "cf_sa_dns_accessor" {
  secret_id = google_secret_manager_secret.dns_api_token.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.cf_sa.email}"
}

# Cloud Function resource triggered by DNS logs via Pub/Sub (2nd Gen)
resource "google_cloudfunctions2_function" "minecraft_starter" {
  name        = "minecraft-starter"
  location    = var.region
  description = "Starts Minecraft GCE VM and updates Cloud DNS record on player request"

  build_config {
    runtime     = "python310"
    entry_point = "start_minecraft"
    source {
      storage_source {
        bucket = google_storage_bucket.function_bucket.name
        object = google_storage_bucket_object.function_zip_object.name
      }
    }
  }

  service_config {
    max_instance_count    = 3
    min_instance_count    = 0
    available_memory      = "256Mi"
    timeout_seconds       = 60
    service_account_email = google_service_account.cf_sa.email

    environment_variables = {
      PROJECT_ID         = var.project_id
      ZONE               = var.zone
      INSTANCE_NAME      = var.instance_name
      DNS_ZONE_NAME      = var.dns_zone_name
      DOMAIN_NAME        = var.domain_name
      DNS_PROVIDER       = var.dns_provider
      CLOUDFLARE_ZONE_ID = var.cloudflare_zone_id
    }

    secret_environment_variables {
      key        = "DNS_API_TOKEN"
      project_id = var.project_id
      secret     = google_secret_manager_secret.dns_api_token.secret_id
      version    = "latest"
    }
  }

  event_trigger {
    trigger_region        = var.region
    event_type            = "google.cloud.pubsub.topic.v1.messagePublished"
    pubsub_topic          = google_pubsub_topic.dns_query_topic.id
    retry_policy          = "RETRY_POLICY_DO_NOT_RETRY"
    service_account_email = google_service_account.cf_sa.email
  }
}

# Secret key for whitelisting HMAC generation
resource "random_id" "whitelist_secret" {
  byte_length = 32
}

# HTTP-triggered Cloud Function for status checking and whitelist requests (2nd Gen)
resource "google_cloudfunctions2_function" "minecraft_status" {
  name        = "minecraft-status"
  location    = var.region
  description = "Returns Minecraft GCE VM status and handles whitelist requests via Discord"

  build_config {
    runtime     = "python310"
    entry_point = "get_status_http"
    source {
      storage_source {
        bucket = google_storage_bucket.function_bucket.name
        object = google_storage_bucket_object.function_zip_object.name
      }
    }
  }

  service_config {
    max_instance_count    = 3
    min_instance_count    = 0
    available_memory      = "256Mi"
    timeout_seconds       = 60
    service_account_email = google_service_account.cf_sa.email

    environment_variables = {
      PROJECT_ID         = var.project_id
      ZONE               = var.zone
      INSTANCE_NAME      = var.instance_name
      DNS_ZONE_NAME      = var.dns_zone_name
      DOMAIN_NAME        = var.domain_name
      FUNCTION_REGION    = var.region
      BACKUPS_BUCKET     = google_storage_bucket.minecraft_backups.name
      INSTANCE_ID        = google_compute_instance.minecraft.instance_id
      DNS_PROVIDER       = var.dns_provider
      CLOUDFLARE_ZONE_ID = var.cloudflare_zone_id
    }

    secret_environment_variables {
      key        = "WHITELIST_SECRET"
      project_id = var.project_id
      secret     = google_secret_manager_secret.whitelist_secret.secret_id
      version    = "latest"
    }

    secret_environment_variables {
      key        = "ADMIN_PASSCODE"
      project_id = var.project_id
      secret     = google_secret_manager_secret.admin_passcode.secret_id
      version    = "latest"
    }

    secret_environment_variables {
      key        = "DISCORD_WEBHOOK_URL"
      project_id = var.project_id
      secret     = google_secret_manager_secret.discord_webhook.secret_id
      version    = "latest"
    }

    secret_environment_variables {
      key        = "DNS_API_TOKEN"
      project_id = var.project_id
      secret     = google_secret_manager_secret.dns_api_token.secret_id
      version    = "latest"
    }
  }
}

# Allow public (unauthenticated) access to the status function (2nd Gen via Cloud Run IAM)
resource "google_cloud_run_service_iam_member" "status_invoker" {
  project  = google_cloudfunctions2_function.minecraft_status.project
  location = google_cloudfunctions2_function.minecraft_status.location
  service  = google_cloudfunctions2_function.minecraft_status.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Generate frontend config.js automatically on terraform apply
resource "local_file" "frontend_config" {
  filename = "${path.module}/../docs/config.js"
  content = "window.serverConfig = ${jsonencode({
    statusUrl  = google_cloudfunctions2_function.minecraft_status.service_config[0].uri
    domainName = var.domain_name
  })};"
}
