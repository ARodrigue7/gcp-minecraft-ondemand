# Terraform Outputs

output "project_id" {
  value       = var.project_id
  description = "The GCP Project ID"
}

output "region" {
  value       = var.region
  description = "The GCP Region"
}

output "dns_name_servers" {
  value       = google_dns_managed_zone.minecraft_zone.name_servers
  description = "The name servers assigned to the Cloud DNS zone. Add NS records in Cloudflare pointing to these."
}

output "vm_instance_name" {
  value       = google_compute_instance.minecraft.name
  description = "The name of the Minecraft Compute Engine instance"
}

output "pubsub_topic" {
  value       = google_pubsub_topic.dns_query_topic.name
  description = "The Pub/Sub topic triggering the Cloud Function"
}

output  "minecraft_domain" {
  value       = var.domain_name
  description = "The domain name players will use to connect"
}

output "zone" {
  value       = var.zone
  description = "The GCP zone where the VM instance resides"
}

output "status_function_url" {
  value       = google_cloudfunctions2_function.minecraft_status.service_config[0].uri
  description = "The HTTP URL to check the server status"
}


