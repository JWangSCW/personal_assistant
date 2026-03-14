scw registry login   
echo "c87f18df-2c0c-4d6c-aa31-141effce4948" | docker login rg.fr-par.scw.cloud/travel-agent -u nologin --password-stdin
# docker build -f deploy/docker/Dockerfile -t personal-assistant .
# docker tag personal-assistant:latest rg.fr-par.scw.cloud/travel-agent/personal-assistant:latest
# docker push rg.fr-par.scw.cloud/travel-agent/personal-assistant:latest
docker buildx build --platform linux/amd64 -t rg.fr-par.scw.cloud/travel-agent/personal-assistant-ui:latest -f deploy/docker/Dockerfile.ui . --push