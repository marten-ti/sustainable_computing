import argparse
import subprocess
import time
import requests
import sys

# Configuration Constants
PROMETHEUS_URL = "http://localhost:9090"
NAMESPACE = "monitoring"
APP_HOST = "http://localhost:8080"


def query_prometheus(prom_url, query):
    try:
        response = requests.get(f"{prom_url}/api/v1/query", params={"query": query}, timeout=10)
        response.raise_for_status()
        data = response.json()
        result = data.get("data", {}).get("result", [])
        if not result:
            print(f"[WARNING] No data returned for query: {query}")
            return 0
        total_val = sum(float(item["value"][1]) for item in result)
        return total_val
    except Exception as e:
        print(f"[ERROR] Failed to query Prometheus: {e}")
        sys.exit(1)


def get_total_energy_joules():
    query = f'sum(kepler_container_joules_total{{namespace="{NAMESPACE}"}})'
    return query_prometheus(PROMETHEUS_URL, query)


def run_pipeline(variant: str, run_workload: bool, duration_seconds: int, warmup_seconds: int):
    print(f"\n==================================================")
    print(f" Start pipeline")
    print(f" Variant / Commit : {variant}")
    print(f" Namespace        : {NAMESPACE}")
    print(f" Workload Enabled : {run_workload}")
    print(f"==================================================\n")

    print(f"1. Applying/verifying variant '{variant}' in Kubernetes...")
    subprocess.run(["kubectl", "apply", "-f", "release/kubernetes-manifests.yaml", "-n", NAMESPACE], check=True)

    print(f"2. Warm-up phase ({warmup_seconds}s)...")
    if run_workload:
        #Locust warm-up
        pass
    time.sleep(warmup_seconds)

    print(f"3. Capturing initial energy state from Prometheus/Kepler...")
    energy_start = get_total_energy_joules()
    start_time = time.time()
    print(f" -> Initial Energy Counter: {energy_start:.2f} Joules")

    if run_workload:
        print(f"4. Running Locust headless workload for {duration_seconds}s...")
        locust_cmd = [
            "locust",
            "-f", "locustfile.py",
            "--headless",
            "-u", "50",
            "-r", "10",
            "--run-time", f"{duration_seconds}s",
            "--host", APP_HOST
        ]
        try:
            subprocess.run(locust_cmd, check=True)
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Locust execution failed: {e}")
            sys.exit(1)
    else:
        print(f"4. Skipping workload. Measuring idle consumption for {duration_seconds}s...")
        time.sleep(duration_seconds)

    end_time = time.time()
    actual_duration = end_time - start_time
    energy_end = get_total_energy_joules()
    energy_consumed = energy_end - energy_start

    print(f"\n Benchmark Complete")
    print(f"--------------------------------------------------")
    print(f" Measured Duration : {actual_duration:.2f} seconds")
    print(f" Start Energy      : {energy_start:.2f} J")
    print(f" End Energy        : {energy_end:.2f} J")
    print(f" Total Energy Delta: {energy_consumed:.2f} Joules ({energy_consumed / 3600:.4f} Wh)")
    print(f"--------------------------------------------------\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manual Energy CI/CD Pipeline for Online Boutique")
    parser.add_argument("--variant", type=str, default="baseline", help="Git branch or commit variant name")
    parser.add_argument("--workload", action="store_true", help="Run Locust workload during the test")
    parser.add_argument("--duration", type=int, default=60, help="Test run duration in seconds")
    parser.add_argument("--warmup", type=int, default=10, help="Warm-up period in seconds to exclude")
    
    args = parser.parse_args()
    run_pipeline(
        variant=args.variant,
        run_workload=args.workload,
        duration_seconds=args.duration,
        warmup_seconds=args.warmup
    )