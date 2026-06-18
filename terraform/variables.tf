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
  description = "The fully qualified domain name for the Minecraft server (e.g. mc.yourdomain.com)"
  type        = string
  default     = "mc.yourdomain.com"
}

variable "dns_zone_name" {
  description = "The name of the Cloud DNS managed zone"
  type        = string
  default     = "mc-yourdomain-com"
}

variable "disk_size_gb" {
  description = "Size of the persistent data disk in GB"
  type        = number
  default     = 10
}

variable "machine_type" {
  description = "Compute Engine machine type for the Minecraft server"
  type        = string
  default     = "e2-medium"
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

variable "discord_public_key" {
  description = "The Discord Bot Application Public Key for interaction verification"
  type        = string
  sensitive   = true
}

variable "wakeup_passcode" {
  description = "Passcode required to wake up the server via the web portal (leave empty to allow wake up without a password check)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "admin_passcode" {
  description = "Passcode required to access the admin portal and run console commands"
  type        = string
  sensitive   = true
}

variable "enable_dns_autostart" {
  description = "Enable autostarting the server whenever the domain is queried/resolved. Set to false to require manual portal starts."
  type        = bool
  default     = true
}

