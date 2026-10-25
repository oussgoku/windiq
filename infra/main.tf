terraform {
  required_version = ">= 1.7.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 7.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_project_service" "compute" {
  project            = var.project_id
  service            = "compute.googleapis.com"
  disable_on_destroy = false
}

resource "google_compute_network" "windiq" {
  name                    = "windiq-network"
  auto_create_subnetworks = false
  depends_on              = [google_project_service.compute]
}

resource "google_compute_subnetwork" "windiq" {
  name          = "windiq-subnet"
  ip_cidr_range = "10.42.0.0/24"
  region        = var.region
  network       = google_compute_network.windiq.id
}

resource "google_compute_firewall" "web" {
  name          = "windiq-web"
  network       = google_compute_network.windiq.name
  target_tags   = ["windiq-web"]
  source_ranges = ["0.0.0.0/0"]

  allow {
    protocol = "tcp"
    ports    = ["80", "443"]
  }
}

resource "google_compute_firewall" "ssh" {
  name          = "windiq-ssh"
  network       = google_compute_network.windiq.name
  target_tags   = ["windiq-web"]
  source_ranges = var.ssh_source_ranges

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }
}

resource "google_compute_address" "windiq" {
  name       = "windiq-ip"
  region     = var.region
  depends_on = [google_project_service.compute]
}

resource "google_compute_instance" "windiq" {
  name         = "windiq"
  machine_type = var.machine_type
  zone         = var.zone
  tags         = ["windiq-web"]

  boot_disk {
    auto_delete = true
    initialize_params {
      image = "ubuntu-os-cloud/ubuntu-2404-lts-amd64"
      size  = var.boot_disk_gb
      type  = "pd-balanced"
    }
  }

  network_interface {
    subnetwork = google_compute_subnetwork.windiq.id
    access_config {
      nat_ip = google_compute_address.windiq.address
    }
  }

  metadata = {
    "ssh-keys"               = "windiq:${trimspace(var.ssh_public_key)}"
    "block-project-ssh-keys" = "TRUE"
  }
}
