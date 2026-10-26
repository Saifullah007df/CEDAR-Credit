#!/bin/sh
set -eu
# Run on a connected build machine after source/dependency review.
# Exports prebuilt images; destination does NOT need external APIs for runtime.
docker compose build api worker
docker pull postgres:17-alpine
docker save cedar-v6:local postgres:17-alpine -o cedar-v6-images.tar
sha256sum cedar-v6-images.tar > cedar-v6-images.tar.sha256
printf '%s\n' 'On offline host: sha256sum -c cedar-v6-images.tar.sha256 && docker load -i cedar-v6-images.tar'
