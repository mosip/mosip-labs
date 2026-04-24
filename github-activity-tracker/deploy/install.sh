#!/bin/bash
# Installs the GH-Tracker
# Make sure you have updated ui_values.yaml
## Usage: ./install.sh [kubeconfig]

if [ $# -ge 1 ] ; then
  export KUBECONFIG=$1
fi

NS=gh-tracker
CHART_VERSION=0.0.1-develop

echo Create $NS namespace
kubectl create ns $NS

function installing_gh_tracker() {
  echo Istio label
  kubectl label ns $NS istio-injection=enabled --overwrite
  helm repo update

  read -p "Please enter the GH_TRACKER_HOST : " gh_tracker_host
  if [ -z "$gh_tracker_host" ]; then
     echo "ERROR: gh_tracker_host cannot be empty; EXITING;";
     exit 1;
  fi

  API_HOST=$(kubectl get cm global -o jsonpath={.data.mosip-api-internal-host})

  echo Installing GH-Tracker service. Will wait till service gets installed.
  helm -n $NS install gh-tracker ../helm/gh-tracker-service --set istio.corsPolicy.allowOrigins\[0\].prefix=https://$gh_tracker_host --wait --version $CHART_VERSION -f gh-tracker-values.yaml

  echo Installing GH-Tracker-UI. Will wait till the UI gets installed.
  helm -n $NS install gh-tracker-ui ../helm/gh-tracker-ui --set istio.hosts\[0\]=$gh_tracker_host --version $CHART_VERSION -f gh-tracker-ui-values.yaml

  kubectl -n $NS  get deploy -o name |  xargs -n1 -t  kubectl -n $NS rollout status

  echo Installed gh-tracker and gh-tracker-ui.

  echo "GH-Tracker portal URL: https://$gh_tracker_host/"
  return 0
}

# set commands for error handling.
set -e
set -o errexit   ## set -e : exit the script if any statement returns a non-true return value
set -o nounset   ## set -u : exit the script if you try to use an uninitialised variable
set -o errtrace  # trace ERR through 'time command' and other functions
set -o pipefail  # trace ERR through pipes
installing_gh_tracker   # calling function
