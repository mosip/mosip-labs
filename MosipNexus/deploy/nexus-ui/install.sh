#!/bin/bash
# Installs / upgrades the MOSIP Nexus UI (React + nginx)
## Usage: ./install.sh [kubeconfig] [values-file]
##
## Prerequisite: deploy/nexus-server/install.sh already ran successfully in
## the same namespace — this chart's nginx proxies same-origin /api/* to the
## "nexus-api" Service created by that release.

if [ $# -ge 1 ] && [ -n "$1" ] ; then
  export KUBECONFIG=$1
fi

NS=mosip-nexus
RELEASE=nexus-ui
CHART_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../helm/nexus-ui" && pwd)"
VALUES_ARGS=()
if [ $# -ge 2 ] && [ -n "$2" ] ; then
  VALUES_ARGS=(-f "$2")
fi

function installing_nexus_ui() {
  if ! kubectl -n "$NS" get svc nexus-api >/dev/null 2>&1 ; then
    echo "WARNING: Service 'nexus-api' not found in namespace '$NS'."
    echo "Run deploy/nexus-server/install.sh first, or the UI will 502 on /api/*."
  fi

  echo "Creating $NS namespace (no-op if it already exists)"
  kubectl create ns "$NS" --dry-run=client -o yaml | kubectl apply -f -

  echo "Installing/upgrading $RELEASE from $CHART_DIR"
  helm -n "$NS" upgrade --install "$RELEASE" "$CHART_DIR" "${VALUES_ARGS[@]}" --wait

  kubectl -n "$NS" get deploy -o name | xargs -r -n1 -t kubectl -n "$NS" rollout status
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
