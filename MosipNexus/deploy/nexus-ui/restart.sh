#!/bin/bash
# Restarts the nexus-ui Deployment (rolling restart, picks up a new image)
## Usage: ./restart.sh [kubeconfig]

if [ $# -ge 1 ] && [ -n "$1" ] ; then
  export KUBECONFIG=$1
fi

NS=mosip-nexus

function restarting_nexus_ui() {
  kubectl -n "$NS" rollout restart deploy nexus-ui
  kubectl -n "$NS" rollout status deploy nexus-ui
  echo "Restarted nexus-ui"
  return 0
}

# set commands for error handling.
set -e
set -o errexit   ## set -e : exit the script if any statement returns a non-true return value
set -o nounset   ## set -u : exit the script if you try to use an uninitialised variable
set -o errtrace  # trace ERR through 'time command' and other functions
set -o pipefail  # trace ERR through pipes
restarting_nexus_ui   # calling function
