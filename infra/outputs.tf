output "external_ip" {
  description = "Static external IPv4 address for the VM."
  value       = google_compute_address.windiq.address
}

output "site_domain" {
  description = "Hostname to set as SITE_DOMAIN in the VM's .env file."
  value       = "${google_compute_address.windiq.address}.sslip.io"
}

output "ssh_command" {
  description = "SSH command using the deployment key."
  value       = "ssh -i ~/.ssh/windiq_deploy windiq@${google_compute_address.windiq.address}"
}
