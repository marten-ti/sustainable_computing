# Online Boutique and observability configuration

Recorded deployment configuration for the preliminary study: Online Boutique `v0.10.4` at upstream revision `5f4ccc7d1c4312c72e97cba777c4f6a586026e59`, MicroK8s, Kepler 0.13.0 and kube-prometheus-stack chart 93.3.0. Application namespace: `online-boutique`; monitoring namespace: `monitoring`; Kepler namespace: `kepler`.

This directory contains the versioned application manifest, upstream license, image digest inventory, Helm values/chart snapshots, ServiceMonitor, Kepler configuration and Grafana dashboard (`boutique-energy`). It omits credentials and live cluster inventory exports.

## Deploy the application and dashboard

Requires kubectl access to a cluster where Kepler, Prometheus and Grafana are already installed with the recorded release names. Review values for your environment. The script checks these prerequisites and applies application/dashboard resources; it does not install monitoring releases.

```sh
cd infrastructure
bash scripts/deploy.sh
python3 scripts/verify.py
python3 scripts/verify_dashboard.py
```

Set `KUBECTL` if needed. The deployment keeps one replica per service, excludes the upstream load generator and external frontend service, and removes application resource limits while preserving requests. `verify.py` sends one mock shopping flow; `verify_dashboard.py` reads Grafana credentials from the cluster Secret in memory.

## Access locally

Run each tunnel in its own terminal:

```sh
kubectl -n monitoring port-forward svc/prometheus-grafana 3000:80
kubectl -n monitoring port-forward svc/prometheus-kube-prometheus-prometheus 9090:9090
kubectl -n online-boutique port-forward svc/frontend 8080:80
```

Grafana: http://localhost:3000/d/boutique-energy ; Prometheus: http://localhost:9090 ; shop: http://localhost:8080 . These local ports are examples, not public endpoints. Obtain the Grafana password through your cluster administrator or the existing Kubernetes Secret. Do not commit passwords or kubeconfig files.

For new research runs, direct private service connectivity avoids tunnel overhead. The original measured generator ran on the same node as the application. An external generator would change the experimental setup.

## Energy interpretation

Use `zone="package"` only when totaling CPU-package energy; package/core domains overlap. Active and idle accumulated counters reconstruct package totals but their split is modeled. Raw RAPL counters can wrap. Pod energy is attribution, not a separate meter. See the root README and full report for cutoff and attribution limitations.
