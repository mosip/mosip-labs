#!/bin/bash
# Installs / upgrades the MOSIP Nexus UI (React + nginx)
## Usage: ./install.sh [kubeconfig]
##
## Prerequisite: deploy/nexus-server/install.sh already ran successfully in
## the same namespace — this chart's nginx proxies same-origin /api/* to the
## "nexus-api" Service created by that release.
## Installs from the published chart (mosip/nexus-ui @ https://mosip.github.io/mosip-helm).
## Requires my-values.yaml (local, gitignored, non-secret overrides — image.tag, ...)
## to exist in this directory — run from deploy/nexus-ui/, not elsewhere.
## Env: ROLLOUT_TIMEOUT  max time to wait for the rollout (default 10m).
##      CHART_VERSION   published nexus-ui chart version to install (default
##      1.0.0). A routine redeploy always gets exactly this version, not
##      whatever happens to be newest — bump it deliberately when you
##      actually want to upgrade, after checking the new chart's changelog.
##
## Hostname: prompted interactively every run — routing is always Istio-based
## (routing.mode: istio), so this always sets routing.istio.hosts[0], never
## routing.ingress.host.

if [ $# -ge 1 ] && [ -n "$1" ] ; then
  export KUBECONFIG=$1
fi

NS=nexus
RELEASE=nexus-ui
CHART_REPO=mosip
CHART_REPO_URL=https://mosip.github.io/mosip-helm
CHART_NAME=nexus-ui
CHART_VERSION="${CHART_VERSION:-1.0.0}"
ROLLOUT_TIMEOUT="${ROLLOUT_TIMEOUT:-10m}"

function prompt_hostname() {
  if [ ! -t 0 ] ; then
    echo "ERROR: this shell isn't interactive — can't prompt for the UI hostname." >&2
    echo "Run this script interactively so it can ask for it." >&2
    return 1
  fi

  # --ignore-not-found distinguishes "no existing VirtualService" (empty
  # output, exit 0 — fresh install) from a real kubectl error (Forbidden,
  # timeout, wrong kubeconfig, ...), same pattern as nexus-server's
  # postgres-data PVC check.
  local current_host
  if ! current_host=$(kubectl -n "$NS" get virtualservice nexus-ui --ignore-not-found -o jsonpath='{.spec.hosts[0]}') ; then
    echo "ERROR: Could not determine the currently deployed hostname" >&2
    echo "(kubectl error above) — refusing to guess. Fix cluster access and retry." >&2
    return 1
  fi
  if [ -n "$current_host" ] ; then
    echo "Currently deployed hostname: $current_host"
  else
    echo "No existing nexus-ui VirtualService found — this looks like a fresh install."
  fi

  local hostname=""
  while [ -z "$hostname" ] ; do
    if ! read -r -p "Enter the hostname for accessing the UI (routing.istio.hosts[0]): " hostname ; then
      echo "ERROR: failed to read hostname input (EOF or interrupted)." >&2
      return 1
    fi
  done

  if [ -n "$current_host" ] && [ "$hostname" != "$current_host" ] ; then
    echo "WARNING: this changes the hostname from '$current_host' to '$hostname'." >&2
    echo "Make sure DNS/TLS for '$hostname' is already set up before confirming." >&2
    local confirm=""
    read -r -p "Type YES to confirm this hostname change: " confirm
    if [ "$confirm" != "YES" ] ; then
      echo "Aborted. Re-run and enter '$current_host' to keep the current hostname." >&2
      return 1
    fi
  fi

  UI_HOSTNAME="$hostname"
}

function installing_nexus_ui() {
  if ! kubectl -n "$NS" get svc nexus-api >/dev/null 2>&1 ; then
    echo "ERROR: Service 'nexus-api' not found in namespace '$NS'."
    echo "Run deploy/nexus-server/install.sh first — the UI proxies /api/* to it."
    exit 1
  fi

  echo "Creating $NS namespace (no-op if it already exists)"
  kubectl create ns "$NS" --dry-run=client -o yaml | kubectl apply -f -

  prompt_hostname

  echo "Adding/updating the '$CHART_REPO' Helm repo ($CHART_REPO_URL)"
  # --force-update + no `|| true`: if a "$CHART_REPO" entry already exists
  # pointing at a DIFFERENT url, silently ignoring the add failure would
  # leave that other, unintended repository in place for the install below.
  if ! helm repo add "$CHART_REPO" "$CHART_REPO_URL" --force-update >/dev/null ; then
    echo "ERROR: Could not configure Helm repository '$CHART_REPO' ($CHART_REPO_URL)." >&2
    exit 1
  fi
  helm repo update "$CHART_REPO" >/dev/null

  echo "Installing/upgrading $RELEASE from $CHART_REPO/$CHART_NAME @ $CHART_VERSION (published chart)"
  helm -n "$NS" upgrade --install "$RELEASE" "$CHART_REPO/$CHART_NAME" \
    --version "$CHART_VERSION" -f my-values.yaml \
    --set routing.istio.hosts[0]="$UI_HOSTNAME" \
    --wait

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
