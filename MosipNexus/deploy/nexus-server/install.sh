#!/bin/bash
# Installs / upgrades the MOSIP Nexus Server (RAG API, postgres, crawlers/jobs, MCP)
## Usage: ./install.sh [kubeconfig] [extra-secrets-env-file] [values-file]
##   kubeconfig              optional path to a kubeconfig (defaults to $KUBECONFIG /
##                           ~/.kube/config)
##   extra-secrets-env-file  optional local, gitignored dotenv file (KEY=value lines,
##                           same keys as Server/.env.example) for OPTIONAL secret.env
##                           keys — GITHUB_TOKEN, GROQ_API_KEY, SMTP_*, AWS_*, ... Only
##                           read the first time the "nexus-env" Secret is created.
##   values-file              optional local values override for NON-secret settings
##                           (storageClassName, image.tag, routing.mode=nginx, ...)
## Env: ROLLOUT_TIMEOUT  max time to wait for the rollout (default 10m) —
##      `kubectl rollout status` has no timeout by default and would otherwise
##      block indefinitely if the Deployment can't become ready.
##      POSTGRES_PASSWORD  skip the interactive password prompt (e.g. for CI).
##      Only consulted the first time the "nexus-env" Secret is created.
##
## Secrets: POSTGRES_PASSWORD/PG_CONNECTION are never stored in a values file or
## passed via `--set` (shell history / CI logs). The "nexus-env" Secret is
## created directly with `kubectl` — NOT by Helm (`secret.create=false` +
## `secret.existingSecret=nexus-env`) — so `helm uninstall` / `./delete.sh`
## never deletes it. Re-running this script checks whether the Secret already
## exists first; if so nothing is prompted, generated, or overwritten.

if [ $# -ge 1 ] && [ -n "$1" ] ; then
  export KUBECONFIG=$1
fi

NS=mosip-nexus
RELEASE=nexus-server
CHART_REPO=mosip
CHART_REPO_URL=https://mosip.github.io/mosip-helm
CHART_NAME=nexus-server
SECRET_NAME=nexus-env
ROLLOUT_TIMEOUT="${ROLLOUT_TIMEOUT:-10m}"
EXTRA_SECRETS_FILE="${2:-}"
VALUES_ARGS=()
if [ $# -ge 3 ] && [ -n "$3" ] ; then
  VALUES_ARGS=(-f "$3")
fi

# Pure-bash percent-encoding — POSTGRES_PASSWORD can contain characters
# (@ : / # ?) that would otherwise corrupt the derived PG_CONNECTION URL.
function urlencode() {
  local s="$1" out="" c i
  for (( i=0; i<${#s}; i++ )); do
    c="${s:$i:1}"
    case "$c" in
      [a-zA-Z0-9.~_-]) out+="$c" ;;
      *) printf -v hex '%%%02X' "'$c"
         out+="$hex" ;;
    esac
  done
  printf '%s' "$out"
}

function ensure_secret() {
  if kubectl -n "$NS" get secret "$SECRET_NAME" >/dev/null 2>&1 ; then
    echo "Secret '$SECRET_NAME' already exists in namespace '$NS' — leaving it as-is."
    return 0
  fi

  echo "Secret '$SECRET_NAME' not found in namespace '$NS' — creating it now (one-time)."
  local password="${POSTGRES_PASSWORD:-}"
  if [ -z "$password" ] ; then
    if [ -t 0 ] ; then
      while [ -z "$password" ] ; do
        read -rs -p "Enter a PostgreSQL password for the 'mosip' user: " password
        echo
      done
    else
      # `|| true`: `head -c32` closing the pipe early SIGPIPEs `tr`, which
      # pipefail would otherwise treat as a failure and abort the script.
      password=$(LC_ALL=C tr -dc 'A-Za-z0-9' < /dev/urandom | head -c 32) || true
      echo "Non-interactive shell and \$POSTGRES_PASSWORD unset — generated a random password (not printed)."
    fi
  fi

  local pg_connection="postgresql+psycopg://mosip:$(urlencode "$password")@nexus-postgres:5432/mosipnexus"

  if [ -n "$EXTRA_SECRETS_FILE" ] && [ ! -f "$EXTRA_SECRETS_FILE" ] ; then
    echo "WARNING: extra-secrets-env-file '$EXTRA_SECRETS_FILE' not found — skipping it." >&2
  fi

  # `kubectl create secret` rejects combining --from-env-file with
  # --from-literal, so merge everything into one temp dotenv file instead.
  local tmp_env
  tmp_env=$(mktemp)
  trap 'rm -f "$tmp_env"' RETURN
  {
    printf 'POSTGRES_PASSWORD=%s\n' "$password"
    printf 'PG_CONNECTION=%s\n' "$pg_connection"
    if [ -n "$EXTRA_SECRETS_FILE" ] && [ -f "$EXTRA_SECRETS_FILE" ] ; then
      cat "$EXTRA_SECRETS_FILE"
    fi
  } > "$tmp_env"

  kubectl -n "$NS" create secret generic "$SECRET_NAME" --from-env-file="$tmp_env"
  echo "Created Secret '$SECRET_NAME'."
}

function installing_nexus_server() {
  echo "Creating $NS namespace (no-op if it already exists)"
  kubectl create ns "$NS" --dry-run=client -o yaml | kubectl apply -f -

  echo "Adding/updating the '$CHART_REPO' Helm repo ($CHART_REPO_URL)"
  helm repo add "$CHART_REPO" "$CHART_REPO_URL" >/dev/null 2>&1 || true
  helm repo update "$CHART_REPO" >/dev/null

  ensure_secret

  echo "Installing/upgrading $RELEASE from $CHART_REPO/$CHART_NAME (published chart)"
  helm -n "$NS" upgrade --install "$RELEASE" "$CHART_REPO/$CHART_NAME" \
    "${VALUES_ARGS[@]}" \
    --set secret.create=false \
    --set secret.existingSecret="$SECRET_NAME" \
    --wait

  kubectl -n "$NS" rollout status deployment/nexus-api --timeout="$ROLLOUT_TIMEOUT"
  echo "Installed $RELEASE"
  return 0
}

# set commands for error handling.
set -e
set -o errexit   ## set -e : exit the script if any statement returns a non-true return value
set -o nounset   ## set -u : exit the script if you try to use an uninitialised variable
set -o errtrace  # trace ERR through 'time command' and other functions
set -o pipefail  # trace ERR through pipes
installing_nexus_server   # calling function
