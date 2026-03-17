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
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
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

resource "random_password" "redis_password" {
  length           = 20
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
  min_lower        = 2
  min_upper        = 2
  min_numeric      = 2
  min_special      = 2
}

resource "scaleway_redis_cluster" "assistant" {
  name         = "redis-assistant"
  version      = "8.4.0"
  node_type    = "RED1-MICRO"
  user_name    = "travelagent"
  password     = random_password.redis_password.result
  cluster_size = 1
  tls_enabled  = true

  private_network {
    id = scaleway_vpc_private_network.assistant.id
  }

  tags = ["assistant", "redis"]

  depends_on = [
    scaleway_vpc_private_network.assistant
  ]
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
          env {
            name  = "REDIS_HOST"
            value = tolist(one(scaleway_redis_cluster.assistant.private_network).ips)[0]
          }

          env {
            name  = "REDIS_PORT"
            value = tostring(one(scaleway_redis_cluster.assistant.private_network).port)
          }

          env {
            name  = "REDIS_USERNAME"
            value = scaleway_redis_cluster.assistant.user_name
          }

          env {
            name  = "REDIS_TLS"
            value = tostring(scaleway_redis_cluster.assistant.tls_enabled)
          }

          env {
            name = "REDIS_PASSWORD"
            value_from {
              secret_key_ref {
                name = "redis-config-from-sm"
                key  = "REDIS_PASSWORD"
              }
            }
          }

          env {
            name = "REDIS_CA_CERT"
            value_from {
              secret_key_ref {
                name = "redis-config-from-sm"
                key  = "REDIS_CA_CERT"
              }
            }
          }
        }
      }
    }
  }
  depends_on = [
    kubernetes_manifest.redis_external_secret
  ]
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
            value = "http://travel-agent"
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



resource "scaleway_secret" "redis_password" {
  name       = "assistant-redis-password"
  project_id = var.project_id
}

resource "scaleway_secret_version" "redis_password_v1" {
  secret_id = scaleway_secret.redis_password.id
  data      = random_password.redis_password.result
}

resource "scaleway_secret" "redis_ca_cert" {
  name       = "assistant-redis-ca-cert"
  project_id = var.project_id
}

resource "scaleway_secret_version" "redis_ca_cert_v1" {
  secret_id = scaleway_secret.redis_ca_cert.id
  data      = scaleway_redis_cluster.assistant.certificate
}

resource "helm_release" "external_secrets" {
  name             = "external-secrets"
  namespace        = "external-secrets"
  create_namespace = true

  repository = "https://charts.external-secrets.io"
  chart      = "external-secrets"
  version    = "0.14.4"

  set {
    name  = "installCRDs"
    value = "true"
  }

  depends_on = [
    scaleway_k8s_cluster.assistant
  ]
}

resource "kubernetes_secret" "scwsm_secret" {
  metadata {
    name      = "scwsm-secret"
    namespace = kubernetes_namespace.assistant.metadata[0].name
  }

  data = {
    "access-key"        = var.access_key
    "secret-access-key" = var.secret_key
  }

  type = "Opaque"
}

resource "kubernetes_manifest" "secret_store" {
  manifest = {
    apiVersion = "external-secrets.io/v1beta1"
    kind       = "SecretStore"
    metadata = {
      name      = "scaleway-secret-store"
      namespace = kubernetes_namespace.assistant.metadata[0].name
    }
    spec = {
      provider = {
        scaleway = {
          region    = var.region
          projectId = var.project_id
          accessKey = {
            secretRef = {
              name = kubernetes_secret.scwsm_secret.metadata[0].name
              key  = "access-key"
            }
          }
          secretKey = {
            secretRef = {
              name = kubernetes_secret.scwsm_secret.metadata[0].name
              key  = "secret-access-key"
            }
          }
        }
      }
    }
  }

  depends_on = [
    helm_release.external_secrets,
    kubernetes_secret.scwsm_secret
  ]
}

resource "kubernetes_manifest" "redis_external_secret" {
  manifest = {
    apiVersion = "external-secrets.io/v1beta1"
    kind       = "ExternalSecret"
    metadata = {
      name      = "redis-external-secret"
      namespace = kubernetes_namespace.assistant.metadata[0].name
    }
    spec = {
      refreshInterval = "1m"
      secretStoreRef = {
        kind = "SecretStore"
        name = "scaleway-secret-store"
      }
      target = {
        name           = "redis-config-from-sm"
        creationPolicy = "Owner"
      }
      data = [
        {
          secretKey = "REDIS_PASSWORD"
          remoteRef = {
            key     = "id:${element(split("/", scaleway_secret.redis_password.id), 1)}"
            version = "latest_enabled"
          }
        },
        {
          secretKey = "REDIS_CA_CERT"
          remoteRef = {
            key     = "id:${element(split("/", scaleway_secret.redis_ca_cert.id), 1)}"
            version = "latest_enabled"
          }
        }
      ]
    }
  }
}

resource "kubernetes_deployment" "travel_worker" {
  metadata {
    name      = "travel-worker"
    namespace = kubernetes_namespace.assistant.metadata[0].name
    labels = {
      app = "travel-worker"
    }
  }

  spec {
    replicas = 1

    selector {
      match_labels = {
        app = "travel-worker"
      }
    }

    template {
      metadata {
        labels = {
          app = "travel-worker"
        }
      }

      spec {
        container {
          name    = "travel-worker"
          image   = "rg.fr-par.scw.cloud/travel-agent/personal-assistant:latest"
          command = ["python", "worker.py"]

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

          env {
            name  = "REDIS_HOST"
            value = tolist(one(scaleway_redis_cluster.assistant.private_network).ips)[0]
          }

          env {
            name  = "REDIS_PORT"
            value = tostring(one(scaleway_redis_cluster.assistant.private_network).port)
          }

          env {
            name  = "REDIS_USERNAME"
            value = scaleway_redis_cluster.assistant.user_name
          }

          env {
            name  = "REDIS_TLS"
            value = tostring(scaleway_redis_cluster.assistant.tls_enabled)
          }

          env {
            name = "REDIS_PASSWORD"
            value_from {
              secret_key_ref {
                name = "redis-config-from-sm"
                key  = "REDIS_PASSWORD"
              }
            }
          }

          env {
            name = "REDIS_CA_CERT"
            value_from {
              secret_key_ref {
                name = "redis-config-from-sm"
                key  = "REDIS_CA_CERT"
              }
            }
          }
        }
      }
    }
  }

  depends_on = [
    kubernetes_manifest.redis_external_secret
  ]
}

output "redis_cluster_id" {
  value = scaleway_redis_cluster.assistant.id
}

output "redis_user_name" {
  value = scaleway_redis_cluster.assistant.user_name
}

output "registry_url" {
  value = scaleway_registry_namespace.assistant.endpoint
}
