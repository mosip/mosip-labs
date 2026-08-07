#!/bin/bash
# Uninstalls the MOSIP Nexus UI helm release
## Usage: ./delete.sh [kubeconfig]
##
## Does NOT delete the "mosip-nexus" namespace (shared with nexus-server) or
## touch the nexus-server release.

if [ $# -ge 1 ] && [ -n "$1" ] ; then
  export KUBECONFIG=$1
fi

NS=mosip-nexus
RELEASE=nexus-ui

function deleting_nexus_ui() {
  IFS= read -r -p "Are you sure you want to delete the $RELEASE helm release in namespace $NS? (y/N) " yn
  if [[ "$yn" =~ ^[Yy]$ ]] ; then
    helm -n "$NS" delete "$RELEASE"
  else
    echo "Aborted."
  fi
  return 0
}

# set commands for error handling.
set -e
set -o errexit   ## set -e : exit the script if any statement returns a non-true return value
set -o nounset   ## set -u : exit the script if you try to use an uninitialised variable
set -o errtrace  # trace ERR through 'time command' and other functions
set -o pipefail  # trace ERR through pipes
deleting_nexus_ui   # calling function
