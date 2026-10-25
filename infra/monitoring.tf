resource "google_project_service" "monitoring" {
  project            = var.project_id
  service            = "monitoring.googleapis.com"
  disable_on_destroy = false
}

resource "google_monitoring_uptime_check_config" "ready" {
  display_name = "WindIQ API readiness"
  period       = "300s"
  timeout      = "10s"

  http_check {
    path         = "/ready"
    port         = 443
    use_ssl      = true
    validate_ssl = true
  }

  monitored_resource {
    type = "uptime_url"
    labels = {
      project_id = var.project_id
      host       = "${google_compute_address.windiq.address}.sslip.io"
    }
  }

  depends_on = [google_project_service.monitoring]
}

resource "google_monitoring_uptime_check_config" "ingestion" {
  display_name = "WindIQ ingestion freshness"
  period       = "300s"
  timeout      = "10s"

  http_check {
    path         = "/health/ingestion"
    port         = 443
    use_ssl      = true
    validate_ssl = true
  }

  monitored_resource {
    type = "uptime_url"
    labels = {
      project_id = var.project_id
      host       = "${google_compute_address.windiq.address}.sslip.io"
    }
  }

  depends_on = [google_project_service.monitoring]
}

resource "google_monitoring_notification_channel" "email" {
  count        = var.alert_email == null ? 0 : 1
  display_name = "WindIQ operations email"
  type         = "email"
  labels = {
    email_address = var.alert_email
  }
  depends_on = [google_project_service.monitoring]
}

resource "google_monitoring_alert_policy" "unhealthy" {
  display_name = "WindIQ public health check failed"
  combiner     = "OR"

  conditions {
    display_name = "API readiness failed"
    condition_threshold {
      filter          = "metric.type=\"monitoring.googleapis.com/uptime_check/check_passed\" AND metric.label.check_id=\"${basename(google_monitoring_uptime_check_config.ready.id)}\" AND resource.type=\"uptime_url\""
      comparison      = "COMPARISON_GT"
      threshold_value = 1
      duration        = "600s"
      aggregations {
        alignment_period     = "1200s"
        per_series_aligner   = "ALIGN_NEXT_OLDER"
        cross_series_reducer = "REDUCE_COUNT_FALSE"
        group_by_fields      = ["resource.label.*"]
      }
      trigger {
        count = 1
      }
    }
  }

  conditions {
    display_name = "Ingestion freshness failed"
    condition_threshold {
      filter          = "metric.type=\"monitoring.googleapis.com/uptime_check/check_passed\" AND metric.label.check_id=\"${basename(google_monitoring_uptime_check_config.ingestion.id)}\" AND resource.type=\"uptime_url\""
      comparison      = "COMPARISON_GT"
      threshold_value = 1
      duration        = "600s"
      aggregations {
        alignment_period     = "1200s"
        per_series_aligner   = "ALIGN_NEXT_OLDER"
        cross_series_reducer = "REDUCE_COUNT_FALSE"
        group_by_fields      = ["resource.label.*"]
      }
      trigger {
        count = 1
      }
    }
  }

  notification_channels = google_monitoring_notification_channel.email[*].name
  depends_on            = [google_project_service.monitoring]
}
