#!/bin/bash
set -e

# build and push
docker buildx build --platform linux/amd64 -t caserver:latest --load .
docker tag caserver:latest ghcr.io/group-h-security/caserver:latest
docker push ghcr.io/group-h-security/caserver:latest

# pull latest image
docker pull ghcr.io/group-h-security/caserver:latest

# start docker compose for caddy
docker compose down
docker compose up -d --build

