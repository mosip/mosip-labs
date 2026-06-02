#!/bin/bash
# Uninstalls all GH-Tracker helm chart
## Usage: ./delete.sh [kubeconfig]

if [ $# -ge 1 ] ; then
  export KUBECONFIG=$1
fi

function deleting_gh_tracker() {
  NS=gh-tracker
  while true; do
      read -p "Are you sure you want to delete GH-Tracker service and GH-Tracker-UI?(Y/n) " yn
      if [ $yn = "Y" ]
        then
          helm -n $NS delete gh-tracker
          helm -n $NS delete gh-tracker-ui
          break
        else
          break
      fi
  done
  return 0
}

# set commands for error handling.
set -e
set -o errexit   ## set -e : exit the script if any statement returns a non-true return value
set -o nounset   ## set -u : exit the script if you try to use an uninitialised variable
set -o errtrace  # trace ERR through 'time command' and other functions
set -o pipefail  # trace ERR through pipes
deleting_gh_tracker   # calling function
