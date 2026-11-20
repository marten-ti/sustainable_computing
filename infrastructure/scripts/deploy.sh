#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
KUBECTL="${KUBECTL:-kubectl}"
# Reuse existing monitoring; never install or replace it as a side effect.
"$KUBECTL" get prometheus prometheus-kube-prometheus-prometheus -n monitoring >/dev/null
"$KUBECTL" get daemonset kepler -n kepler >/dev/null
"$KUBECTL" get deployment prometheus-grafana -n monitoring >/dev/null
"$KUBECTL" apply -f application/namespace.json
"$KUBECTL" apply --dry-run=server -k application
"$KUBECTL" apply -k application
"$KUBECTL" apply -f monitoring/dashboard-configmap.json
"$KUBECTL" wait --for=condition=Available deployment --all -n online-boutique --timeout=300s
KUBECTL="$KUBECTL" python3 scripts/verify.py
