#!/bin/bash
# Installs / upgrades the MOSIP Nexus UI (React + nginx)
## Usage: ./install.sh [kubeconfig] [values-file]
##
## Prerequisite: deploy/nexus-server/install.sh already ran successfully in
## the same namespace — this chart's nginx proxies same-origin /api/* to the
## "nexus-api" Service created by that release.
## Installs from the published chart (mosip/nexus-ui @ https://mosip.github.io/mosip-helm).
## Env: ROLLOUT_TIMEOUT  max time to wait for the rollout (default 10m).

if [ $# -ge 1 ] && [ -n "$1" ] ; then
  export KUBECONFIG=$1
fi

NS=mosip-nexus
RELEASE=nexus-ui
CHART_REPO=mosip
CHART_REPO_URL=https://mosip.github.io/mosip-helm
CHART_NAME=nexus-ui
ROLLOUT_TIMEOUT="${ROLLOUT_TIMEOUT:-10m}"
VALUES_ARGS=()
if [ $# -ge 2 ] && [ -n "$2" ] ; then
  VALUES_ARGS=(-f "$2")
fi

function installing_nexus_ui() {
  if ! kubectl -n "$NS" get svc nexus-api >/dev/null 2>&1 ; then
    echo "ERROR: Service 'nexus-api' not found in namespace '$NS'."
    echo "Run deploy/nexus-server/install.sh first — the UI proxies /api/* to it."
    exit 1
  fi

  echo "Creating $NS namespace (no-op if it already exists)"
  kubectl create ns "$NS" --dry-run=client -o yaml | kubectl apply -f -

  echo "Adding/updating the '$CHART_REPO' Helm repo ($CHART_REPO_URL)"
  helm repo add "$CHART_REPO" "$CHART_REPO_URL" >/dev/null 2>&1 || true
  helm repo update "$CHART_REPO" >/dev/null

  echo "Installing/upgrading $RELEASE from $CHART_REPO/$CHART_NAME (published chart)"
  helm -n "$NS" upgrade --install "$RELEASE" "$CHART_REPO/$CHART_NAME" "${VALUES_ARGS[@]}" --wait

  kubectl -n "$NS" rollout status deployment/nexus-ui --timeout="$ROLLOUT_TIMEOUT"
  echo "Installed $RELEASE"
  return 0
}

# set commands for error handling.
set -e
set -o errexit   ## set -e : exit the script if any statement returns a non-true return value
set -o nounset   ## set -u : exit the script if you try to use an uninitialised variable
set -o errtrace  # trace ERR through 'time command' and other functions
set -o pipefail  # trace ERR through pipes
installing_nexus_ui   # calling function
