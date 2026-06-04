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
