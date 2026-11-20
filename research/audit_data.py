#!/usr/bin/env python3
"""Independently cross-check saved timing, request totals and interval energy."""
import argparse,csv,hashlib,json,math,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument("--require-same-boot",action="store_true",help="Only for an immediate audit on the original measurement host")
 args=parser.parse_args()
 provenance=json.loads((ROOT/'results/provenance.json').read_text())
 for name,expected in provenance['source_sha256'].items():
  assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==expected,('Source changed after campaign start',name)
 runs=[]
 for p in sorted((ROOT/'results').glob('block*/summary.json')):
  s=json.loads(p.read_text());folder=p.parent
  requests=list(csv.DictReader((folder/'requests.csv').open()))
  bins=list(csv.DictReader((folder/'energy_intervals.csv').open()))
  stats=list(csv.DictReader((folder/'measured_stats.csv').open()))
  total=next(x for x in stats if x['operation']=='Aggregated')
  assert len(requests)==s['requests']==int(total['requests'])
  assert sum(int(x['failed']) for x in requests)==s['failures']==0
  assert s['locust_failures']==0,('Guard-inclusive Locust errors',s['run_id'])
  assert all(s['start_epoch']<=float(x['completed_epoch'])<s['end_epoch_target'] for x in requests)
  assert sum(int(x['requests']) for x in bins)==s['requests']
  assert math.isclose(sum(float(x['node_package_j']) for x in bins),s['node_package_j'],abs_tol=1e-6)
  assert s['guard_end_epoch']>=s['end_epoch_target']+10.9
  assert 'Traceback' not in (folder/'console.log').read_text(),s['run_id']
  runs.append(s)
 assert len(runs)==32
 ordered=sorted(runs,key=lambda x:x['warmup_start_epoch'])
 assert all(b['warmup_start_epoch']>=a['guard_end_epoch'] for a,b in zip(ordered[:-1],ordered[1:]))
 assert all(sum(x['requested_duration_s']==d for x in runs)==8 for d in [15,30,60,120])
 if args.require_same_boot:
  assert pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip()==json.loads((ROOT/'results/environment.json').read_text())['boot_id']
 result={'passed':True,'runs':len(runs),'requests':sum(x['requests'] for x in runs),'failures':sum(x['failures'] for x in runs),'checks':['frozen source hashes','request-count CSV agreement','all request timestamps inside cutoffs','interval energy sums','loaded guard duration','no overlapping runs','no Locust errors/tracebacks','eight repetitions per duration','host boot unchanged' if args.require_same_boot else 'offline audit; original boot recorded in environment.json']}
 (ROOT/'results/audit.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(result,indent=2))
if __name__=='__main__':main()
