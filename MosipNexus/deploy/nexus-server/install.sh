#!/bin/bash
# Installs / upgrades the MOSIP Nexus Server (RAG API, postgres, crawlers/jobs, MCP)
## Usage: ./install.sh [kubeconfig] [values-file]
##   kubeconfig   optional path to a kubeconfig (defaults to $KUBECONFIG / ~/.kube/config)
##   values-file  optional local, gitignored values override (e.g. real secrets,
##                a specific storageClassName, routing.mode=nginx, ...)

if [ $# -ge 1 ] && [ -n "$1" ] ; then
  export KUBECONFIG=$1
fi

NS=mosip-nexus
RELEASE=nexus-server
CHART_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../helm/nexus-server" && pwd)"
VALUES_ARGS=()
if [ $# -ge 2 ] && [ -n "$2" ] ; then
  VALUES_ARGS=(-f "$2")
fi

function installing_nexus_server() {
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
installing_nexus_server   # calling function
