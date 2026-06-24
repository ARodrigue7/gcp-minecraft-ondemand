# Terraform Variables

variable "project_id" {
  description = "The GCP Project ID where resources will be deployed"
  type        = string
}

variable "region" {
  description = "The GCP region for regional resources"
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "The GCP zone for the compute instance"
  type        = string
  default     = "us-central1-a"
}

variable "instance_name" {
  description = "Name of the Minecraft server instance"
  type        = string
  default     = "minecraft-server"
}

variable "domain_name" {
  description = "The domain name for the Minecraft server (e.g. mc.yourdomain.com or yourname.duckdns.org)"
  type        = string
  default     = ""
}

variable "dns_zone_name" {
  description = "The name of the Google Cloud DNS managed zone (only needed if using 'google' DNS provider)"
  type        = string
  default     = ""
}

variable "disk_size_gb" {
  description = "Size of the persistent data disk in GB"
  type        = number
  default     = 20
}

variable "disk_auto_expand" {
  description = "Enable automatic persistent disk scaling when usage is high"
  type        = bool
  default     = true
}

variable "disk_auto_expand_max_gb" {
  description = "Maximum size in GB the persistent disk can automatically scale to"
  type        = number
  default     = 25
}

variable "disk_auto_expand_threshold" {
  description = "Percentage of disk space usage that triggers auto-expansion"
  type        = number
  default     = 80
}

variable "machine_type" {
  description = "Compute Engine machine type for the Minecraft server"
  type        = string
  default     = "e2-medium"
}

variable "minecraft_version" {
  description = "The version of Minecraft server to run (e.g. 26.2 or LATEST)"
  type        = string
  default     = "LATEST"
}

variable "idle_timeout_seconds" {
  description = "Idle timeout in seconds before the VM shuts down automatically"
  type        = number
  default     = 600
}

variable "discord_webhook_url" {
  description = "The Discord Webhook URL to push whitelist requests"
  type        = string
  sensitive   = true
}



variable "admin_passcode" {
  description = "Passcode required to access the admin portal and run console commands"
  type        = string
  sensitive   = true
}

variable "enable_dns_autostart" {
  description = "Enable autostarting the server whenever the domain is queried/resolved. Only applicable if dns_provider is 'google'."
  type        = bool
  default     = true
}

variable "dns_provider" {
  description = "Dynamic DNS provider to use. Supported: 'google', 'cloudflare', 'duckdns', 'dynu', or 'none'."
  type        = string
  default     = "google"
}

variable "dns_api_token" {
  description = "API token or credentials for the dynamic DNS service (Cloudflare, DuckDNS, or Dynu)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "cloudflare_zone_id" {
  description = "Zone ID for Cloudflare DNS (only needed if using 'cloudflare' DNS provider)"
  type        = string
  default     = ""
}

