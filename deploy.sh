docker buildx build --platform linux/amd64 -t caserver:latest --load .
docker tag caserver:latest ghcr.io/group-h-security/caserver:latest
docker push ghcr.io/group-h-security/caserver:latest

