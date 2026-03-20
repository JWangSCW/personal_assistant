scw registry login   
echo "c87f18df-2c0c-4d6c-aa31-141effce4948" | docker login rg.fr-par.scw.cloud/travel-agent -u nologin --password-stdin
# docker build -f deploy/docker/Dockerfile -t personal-assistant .
# docker tag personal-assistant:latest rg.fr-par.scw.cloud/travel-agent/personal-assistant:latest
# docker push rg.fr-par.scw.cloud/travel-agent/personal-assistant:latest
docker buildx build --platform linux/amd64 -t rg.fr-par.scw.cloud/travel-agent/personal-assistant-ui:latest -f deploy/docker/Dockerfile.ui . --push


docker buildx build --platform linux/amd64 -t rg.fr-par.scw.cloud/travel-agent/personal-assistant-ui:latest -f deploy/docker/Dockerfile.ui . --push
kubectl rollout restart deployment/travel-ui -n assistant
kubectl rollout status deployment/travel-ui -n assistant


docker buildx build --platform linux/amd64 -t rg.fr-par.scw.cloud/travel-agent/personal-assistant:latest -f deploy/docker/Dockerfile . --push                                                              
kubectl rollout restart deployment/travel-agent -n assistant
kubectl rollout status deployment/travel-agent -n assistant
kubectl logs deployment/travel-agent -n assistant --tail=100

docker buildx build --platform linux/amd64 -t rg.fr-par.scw.cloud/travel-agent/personal-assistant:latest -f deploy/docker/Dockerfile . --push                                                              
kubectl rollout restart deployment/travel-worker -n assistant
kubectl rollout status deployment/travel-worker -n assistant
kubectl logs deployment/travel-worker -n assistant --tail=100

source /Users/jwang/jwangscw/personal_assistant/venv/bin/activate
kubectl -n assistant port-forward svc/travel-agent 8000:80     
curl -X POST "http://localhost:8000/plan-trip" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Plan a 2-day trip in Paris with my family",
    "session_id": "test-session-1"
  }'
curl "http://localhost:8000/jobs/c0edfb6c-64ce-4a16-b329-8ec379a8f64c" 