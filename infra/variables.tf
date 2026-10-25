variable "project_id" {
  description = "Google Cloud project ID."
  type        = string
  default     = "windiq"
}

variable "region" {
  description = "Region for the network and static IP."
  type        = string
  default     = "europe-west10"
}

variable "zone" {
  description = "Zone for the VM; it must belong to the selected region."
  type        = string
  default     = "europe-west10-a"
}

variable "machine_type" {
  description = "Compute Engine machine type."
  type        = string
  default     = "e2-medium"
}

variable "boot_disk_gb" {
  description = "Boot disk size in GB. Destroying the VM deletes this disk."
  type        = number
  default     = 20
}

variable "ssh_public_key" {
  description = "Ed25519 public key for the windiq deployment account."
  type        = string
}

variable "ssh_source_ranges" {
  description = "CIDR ranges allowed to SSH to the VM. GitHub-hosted deploy runners need a reachable range."
  type        = list(string)

  validation {
    condition     = length(var.ssh_source_ranges) > 0
    error_message = "Provide at least one SSH source CIDR range."
  }
}
