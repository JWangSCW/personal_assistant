terraform {
  required_providers {
    scaleway = {
      source  = "scaleway/scaleway"
      version = "~> 2.70"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.0"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.0"
    }
  }
}

provider "scaleway" {
  access_key = var.access_key
  secret_key = var.secret_key
  project_id = var.project_id
  region     = var.region
}

resource "scaleway_vpc" "assistant" {
  name = "vpc-assistant"
  tags = ["assistant"]
}

resource "scaleway_vpc_private_network" "assistant" {
  name   = "kapsule-private-net-assistant"
  region = var.region
  vpc_id = scaleway_vpc.assistant.id
}

resource "scaleway_k8s_cluster" "assistant" {
  name                        = "cluster-assistant"
  type                        = "kapsule"
  region                      = var.region
  version                     = var.k8s_version
  cni                         = "cilium"
  tags                        = ["assistant"]
  private_network_id          = scaleway_vpc_private_network.assistant.id
  delete_additional_resources = true
}

resource "scaleway_k8s_pool" "assistant" {
  name                   = "pool-assistant"
  zone                   = var.zone
  tags                   = ["assistant"]
  cluster_id             = scaleway_k8s_cluster.assistant.id
  node_type              = var.node_type
  size                   = 1
  autoscaling            = false
  autohealing            = false
  container_runtime      = "containerd"
  root_volume_size_in_gb = 32
}

provider "kubernetes" {
  host                   = scaleway_k8s_cluster.assistant.kubeconfig[0].host
  token                  = scaleway_k8s_cluster.assistant.kubeconfig[0].token
  cluster_ca_certificate = base64decode(scaleway_k8s_cluster.assistant.kubeconfig[0].cluster_ca_certificate)
}

provider "helm" {
  kubernetes {
    host                   = scaleway_k8s_cluster.assistant.kubeconfig[0].host
    token                  = scaleway_k8s_cluster.assistant.kubeconfig[0].token
    cluster_ca_certificate = base64decode(scaleway_k8s_cluster.assistant.kubeconfig[0].cluster_ca_certificate)
  }
}

resource "scaleway_registry_namespace" "assistant" {
  name = "travel-agent"
}

output "registry_url" {
  value = scaleway_registry_namespace.assistant.endpoint
}


resource "kubernetes_namespace" "assistant" {
  metadata {
    name = "assistant"
  }
}

resource "kubernetes_deployment" "travel_agent" {
  metadata {
    name      = "travel-agent"
    namespace = kubernetes_namespace.assistant.metadata[0].name
    labels = {
      app = "travel-agent"
    }
  }

  spec {
    replicas = 1

    selector {
      match_labels = {
        app = "travel-agent"
      }
    }

    template {
      metadata {
        labels = {
          app = "travel-agent"
        }
      }

      spec {
        container {
          name  = "travel-agent"
          image = "rg.fr-par.scw.cloud/travel-agent/personal-assistant:latest"

          port {
            container_port = 8000
          }

          env {
            name  = "SCW_SECRET_KEY"
            value = var.secret_key
          }

          env {
            name  = "SCW_MODEL"
            value = "llama-3.1-8b-instruct"
          }

          env {
            name  = "SCW_EMBEDDING_MODEL"
            value = "bge-multilingual-gemma2"
          }
        }
      }
    }
  }
}

resource "kubernetes_service" "travel_agent" {
  metadata {
    name      = "travel-agent"
    namespace = kubernetes_namespace.assistant.metadata[0].name
  }

  spec {
    selector = {
      app = "travel-agent"
    }

    port {
      port        = 80
      target_port = 8000
    }

    type = "ClusterIP"
  }
}


resource "kubernetes_deployment" "travel_ui" {
  metadata {
    name      = "travel-ui"
    namespace = kubernetes_namespace.assistant.metadata[0].name
    labels = {
      app = "travel-ui"
    }
  }

  spec {
    replicas = 1

    selector {
      match_labels = {
        app = "travel-ui"
      }
    }

    template {
      metadata {
        labels = {
          app = "travel-ui"
        }
      }

      spec {
        container {
          name  = "travel-ui"
          image = "rg.fr-par.scw.cloud/travel-agent/personal-assistant-ui:latest"

          port {
            container_port = 8501
          }

          env {
            name  = "API_URL"
            value = "http://travel-agent/plan-trip"
          }
        }
      }
    }
  }
}

resource "kubernetes_service" "travel_ui" {
  metadata {
    name      = "travel-ui"
    namespace = kubernetes_namespace.assistant.metadata[0].name
  }

  spec {
    selector = {
      app = "travel-ui"
    }

    port {
      port        = 80
      target_port = 8501
    }

    type = "LoadBalancer"
  }
}
