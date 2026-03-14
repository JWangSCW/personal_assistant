# --- Scaleway Authentication ---

variable "access_key" {
  type        = string
  description = "Scaleway Access Key used for API authentication."
}

variable "secret_key" {
  type        = string
  description = "Scaleway Secret Key. This value is marked as sensitive and will be masked in console logs."
  sensitive   = true #
}

variable "project_id" {
  type        = string
  description = "The ID of the Scaleway project where resources are deployed."
}

variable "region" {
  type        = string
  description = "The Scaleway region used (e.g., fr-par)."
}

variable "zone" {
  type        = string
  description = "The Scaleway az used (e.g., fr-par-2)."
}

variable "k8s_version" {
  type        = string
  description = "The Kubernetes version to use for the cluster."
}

variable "node_type" {
  type = string
}


