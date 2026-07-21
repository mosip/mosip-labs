#!/usr/bin/env bash
# seal-secrets.sh — Encrypt Server/.env into a SealedSecret for safe git storage.
#
# Prerequisites:
#   1. Install kubeseal CLI:
#        curl -L https://github.com/bitnami-labs/sealed-secrets/releases/latest/download/kubeseal-linux-amd64 \
#          -o /usr/local/bin/kubeseal && chmod +x /usr/local/bin/kubeseal
#   2. Install the Sealed Secrets controller in your cluster (one-time):
#        kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/latest/download/controller.yaml
#   3. Run this script from the repo root (where Server/.env exists):
#        bash Server/k8s/seal-secrets.sh
#
# Output: Server/k8s/02-sealed-secret.yaml — safe to commit to git.
# The plaintext Server/k8s/02-secret.yaml is a template only — never fill in real values there.

set -euo pipefail

ENV_FILE="Server/.env"
OUTPUT="Server/k8s/02-sealed-secret.yaml"
NAMESPACE="mosip-nexus"
SECRET_NAME="nexus-env"
CONTROLLER_NS="kube-system"
CONTROLLER_NAME="sealed-secrets-controller"

if [ ! -f "$ENV_FILE" ]; then
  echo "ERROR: $ENV_FILE not found. Run from the repo root." >&2
  exit 1
fi

# Use a unique temp file and clean it up on exit regardless of success/failure
CERT_FILE=$(mktemp)
trap 'rm -f "$CERT_FILE"' EXIT

echo "Fetching Sealed Secrets public key from cluster..."
kubeseal --fetch-cert \
  --controller-namespace "$CONTROLLER_NS" \
  --controller-name "$CONTROLLER_NAME" \
  > "$CERT_FILE"

echo "Creating and sealing the Kubernetes Secret..."
kubectl create secret generic "$SECRET_NAME" \
  --namespace "$NAMESPACE" \
  --from-env-file="$ENV_FILE" \
  --dry-run=client \
  -o yaml \
| kubeseal \
    --cert "$CERT_FILE" \
    --format yaml \
    --namespace "$NAMESPACE" \
  > "$OUTPUT"

echo ""
echo "Done: $OUTPUT"
echo "  → Apply with: kubectl apply -f $OUTPUT"
echo "  → Do NOT commit this file — it is cluster-specific and gitignored."
echo ""
echo "To rotate secrets later, update $ENV_FILE and re-run this script."
