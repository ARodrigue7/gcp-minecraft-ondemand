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
  type = "pd-standard"
  zone = var.zone
  size = var.disk_size_gb
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
      idle_timeout_seconds = var.idle_timeout_seconds
    })
  }

  service_account {
    email  = google_service_account.minecraft_sa.email
    scopes = ["cloud-platform"]
  }
}

# ==========================================
# 🌐 CLOUD DNS CONFIGURATION
# ==========================================

# Managed Public DNS Zone for mc.pitcomi.com
resource "google_dns_managed_zone" "minecraft_zone" {
  name        = var.dns_zone_name
  dns_name    = "${var.domain_name}."
  description = "Managed zone for Minecraft server on-demand resolution"
  visibility  = "public"

  cloud_logging_config {
    enable_logging = true
  }
}

# Placeholder A-Record pointing to 127.0.0.1 initially (updated dynamically by Cloud Function)
resource "google_dns_record_set" "minecraft_a_record" {
  name         = google_dns_managed_zone.minecraft_zone.dns_name
  managed_zone = google_dns_managed_zone.minecraft_zone.name
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

# Log Sink to route DNS query logs for mc.pitcomi.com to the Pub/Sub topic
resource "google_logging_project_sink" "dns_query_sink" {
  name                   = "minecraft-dns-query-sink"
  destination            = "pubsub.googleapis.com/${google_pubsub_topic.dns_query_topic.id}"
  filter                 = "resource.type=\"dns_query\" AND jsonPayload.queryName=\"${var.domain_name}.\""
  unique_writer_identity = true
}

# IAM policy to allow the Log Sink to publish events to Pub/Sub
resource "google_pubsub_topic_iam_member" "dns_query_sink_publisher" {
  topic  = google_pubsub_topic.dns_query_topic.name
  role   = "roles/pubsub.publisher"
  member = google_logging_project_sink.dns_query_sink.writer_identity
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

# Grant Cloud Function permissions to start/stop the GCE instance
resource "google_project_iam_member" "cf_compute" {
  project = var.project_id
  role    = "roles/compute.instanceAdmin.v1"
  member  = "serviceAccount:${google_service_account.cf_sa.email}"
}

# Grant Cloud Function permissions to update DNS A-Records
resource "google_project_iam_member" "cf_dns" {
  project = var.project_id
  role    = "roles/dns.admin"
  member  = "serviceAccount:${google_service_account.cf_sa.email}"
}

# Cloud Function resource triggered by DNS logs via Pub/Sub
resource "google_cloudfunctions_function" "minecraft_starter" {
  name        = "minecraft-starter"
  description = "Starts Minecraft GCE VM and updates Cloud DNS record on player request"
  runtime     = "python310"

  available_memory_mb   = 256
  source_archive_bucket = google_storage_bucket.function_bucket.name
  source_archive_object = google_storage_bucket_object.function_zip_object.name
  entry_point           = "start_minecraft"

  event_trigger {
    event_type = "google.pubsub.topic.publish"
    resource   = google_pubsub_topic.dns_query_topic.id
  }

  environment_variables = {
    PROJECT_ID    = var.project_id
    ZONE          = var.zone
    INSTANCE_NAME = var.instance_name
    DNS_ZONE_NAME = var.dns_zone_name
    DOMAIN_NAME   = var.domain_name
  }

  service_account_email = google_service_account.cf_sa.email
}
