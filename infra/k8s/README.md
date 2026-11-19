# Kubernetes (local, free): kind or minikube

Everything runs on your laptop in a one-node cluster. Needs Docker Desktop with **≥ 10 GB RAM**
assigned (Ollama alone requests 5 Gi). Low on RAM? Set `LLM_MODEL: qwen2.5:3b-instruct` in
`base.yaml` and lower the Ollama memory request to `3Gi`.

## Objects at a glance
| File | Objects | Why |
|---|---|---|
| `base.yaml` | Namespace, ConfigMap | isolation + non-secret config |
| `secret.example.yaml` | Secret (template) | passwords/keys — copy to `secret.yaml`, never commit |
| `data.yaml` | Postgres **StatefulSet** + headless Service, MinIO Deployment + PVC + bucket **Job**, Ollama Deployment + PVC + model-pull **Job** | stateful backing services |
| `apps.yaml` | ai / api / frontend **Deployments** + Services (frontend = NodePort 30000) | the app; probes + resource limits |
| `kustomization.yaml` | — | `kubectl apply -k` applies everything with common labels |

## Run with kind
```bash
# 0. tools: https://kind.sigs.k8s.io/  and  kubectl
kind create cluster --name mockai --config infra/k8s/kind-config.yaml

# 1. build images and load them into the cluster (no registry needed)
docker build -t mockai-ai:local ai
docker build -t mockai-api:local api
docker build -t mockai-frontend:local frontend
kind load docker-image mockai-ai:local mockai-api:local mockai-frontend:local --name mockai

# 2. secrets (edit values first!)
cp infra/k8s/secret.example.yaml infra/k8s/secret.yaml
kubectl apply -f infra/k8s/base.yaml          # creates the namespace
kubectl apply -f infra/k8s/secret.yaml

# 3. everything else
kubectl apply -k infra/k8s
kubectl -n mockai get pods -w                 # wait for Running / Completed
kubectl -n mockai logs job/ollama-pull-model  # model download (~5 GB, first time only)

# 4. open http://localhost:3000
```

## Run with minikube
Same steps, but: `minikube start --memory 10g --cpus 4`, load images with
`minikube image load mockai-ai:local` (etc.), and open the app with
`minikube service -n mockai frontend`.

## Useful commands
```bash
kubectl -n mockai describe pod <name>        # why is it Pending / CrashLooping?
kubectl -n mockai port-forward svc/minio 9001  # MinIO console on localhost:9001
kubectl -n mockai rollout restart deploy/ai    # reload after installing a new model
kubectl -n mockai scale deploy/api --replicas 3
kind delete cluster --name mockai              # clean up
```

## Validated in CI
`.github/workflows/ci.yml` → job `k8s`: renders with kustomize, validates schemas with kubeconform,
then creates a throwaway kind cluster and runs `kubectl apply --dry-run=server` (the real API server
checks every object; no images are pulled).
