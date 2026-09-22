#!/usr/bin/env bash
# Cycle d'une image sur le registry Docker local : build -> tag -> push -> pull.
# Même enchaînement que vers un registry distant type ECR, à petite échelle.
#
# Usage : ./scripts/registry_cycle.sh [version]   (défaut : v1)

set -euo pipefail

VERSION="${1:-v1}"
REGISTRY="${REGISTRY:-localhost:5001}"
IMAGE_NAME="analyse-de-docs-app"
LOCAL_TAG="${IMAGE_NAME}:local"
REMOTE_TAG="${REGISTRY}/${IMAGE_NAME}:${VERSION}"

cd "$(dirname "$0")/.."

echo "==> 0. Démarrage du registry local"
docker compose up -d registry
until curl -sf "http://${REGISTRY}/v2/" >/dev/null; do
    echo "    en attente de ${REGISTRY}..."
    sleep 1
done

echo "==> 1. build : construire l'image depuis le Dockerfile"
docker build -t "${LOCAL_TAG}" .

echo "==> 2. tag : nommer l'image pour le registry"
echo "    ${LOCAL_TAG} -> ${REMOTE_TAG}"
docker tag "${LOCAL_TAG}" "${REMOTE_TAG}"

echo "==> 3. push : envoyer l'image vers ${REGISTRY}"
docker push "${REMOTE_TAG}"

echo "==> 4. suppression de la référence locale (pour vérifier que le pull la ramène)"
docker image rm "${REMOTE_TAG}" >/dev/null

echo "==> 5. pull : récupérer l'image depuis ${REGISTRY}"
docker pull "${REMOTE_TAG}"

echo
echo "==> Contenu du registry"
echo -n "    dépôts : "
curl -s "http://${REGISTRY}/v2/_catalog"
echo -n "    tags   : "
curl -s "http://${REGISTRY}/v2/${IMAGE_NAME}/tags/list"
echo
echo "Pour lancer la stack depuis cette image :"
echo "    APP_IMAGE=${REMOTE_TAG} docker compose up -d api worker"
