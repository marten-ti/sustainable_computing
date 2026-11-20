#!/usr/bin/env python3
"""Local preliminary experiments against an already deployed application.

Never deploys/reset pods, never starts CI, and aborts on invalid measurement.
"""
import argparse,csv,datetime,hashlib,json,math,os,pathlib,random,resource,subprocess,sys,time
import urllib.parse,urllib.request
import numpy as np

ROOT=pathlib.Path(__file__).resolve().parents[1]
METRICS={
 'node_active':'kepler_node_cpu_active_joules_total{zone="package"}',
 'node_idle':'kepler_node_cpu_idle_joules_total{zone="package"}',
 'node_raw':'kepler_node_cpu_joules_total{zone="package"}',
 'node_power':'kepler_node_cpu_watts{zone="package"}',
 'dram_power':'kepler_node_cpu_watts{zone="dram"}',
 'node_usage':'kepler_node_cpu_usage_ratio',
 'app_energy':'kepler_pod_cpu_joules_total{pod_namespace="online-boutique",zone="package",state="running"}',
 'app_power':'kepler_pod_cpu_watts{pod_namespace="online-boutique",zone="package",state="running"}',
 'namespace_power':'kepler_pod_cpu_watts{zone="package",state="running"}',
}
def json_get(url):
 with urllib.request.urlopen(url,timeout=20) as r:return json.load(r)
def write_json(path,obj):path.write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n')
def series_sum(matrix):
 grouped={}
 for series in matrix:
  for ts,value in series['values']:grouped[float(ts)]=grouped.get(float(ts),0)+float(value)
 return np.array(sorted(grouped.items()),dtype=float)
def clip_series(points,start,end):
 assert len(points)>=2,'Insufficient energy samples'
 assert points[0,0]<=start and points[-1,0]>=end,'No energy samples bracketing full measurement window'
 a=points[np.r_[True,np.diff(points[:,0])>0]]
 before=np.searchsorted(a[:,0],start,side='right')-1;after=np.searchsorted(a[:,0],end,side='left')
 assert np.max(np.diff(a[before:after+1,0]))<=10.5,'Energy scrape gap exceeds 10.5 seconds'
 inside=a[(a[:,0]>start)&(a[:,0]<end)]
 return np.vstack(([start,np.interp(start,a[:,0],a[:,1])],inside,[end,np.interp(end,a[:,0],a[:,1])]))
def counter_window(matrix,start,end):
 assert matrix,'Missing energy metric (never interpreted as zero)'
 for s in matrix:
  vals=np.array(s['values'],dtype=float)
  sub=vals[(vals[:,0]>=start-10)&(vals[:,0]<=end+10)]
  assert len(sub)>=2 and np.all(np.diff(sub[:,1])>=-1e-6),'Counter reset or missing series'
 return clip_series(series_sum(matrix),start,end)
def interpolate_at(points,t):return float(np.interp(t,points[:,0],points[:,1]))
def temperatures():
 result={}
 for d in pathlib.Path('/sys/class/hwmon').glob('hwmon*'):
  name=(d/'name').read_text().strip()
  for p in d.glob('temp*_input'):
   try:result[f'{name}/{p.stem}']=int(p.read_text())/1000
   except (ValueError,OSError):pass
 return result

def fetch_measurement(prom,out,run):
 start=run['start_epoch'];end=run['end_epoch_target'];query_time=time.time()
 window=math.ceil(query_time-run['warmup_start_epoch']+15)
 raw={}
 for name,expr in METRICS.items():
  q=json_get(prom+'/api/v1/query?'+urllib.parse.urlencode({'query':f'{expr}[{window}s]','time':query_time}))
  assert q['status']=='success',q
  raw[name]=q['data']['result']
 write_json(out/'prometheus_raw.json',{'queried_at':query_time,'metrics':raw})
 active=counter_window(raw['node_active'],start,end);idle=counter_window(raw['node_idle'],start,end)
 assert len(raw['app_energy'])==11,'Missing or unexpected application pod energy series'
 app=counter_window(raw['app_energy'],start,end)
 # The two node counters share scrapes; union is robust to any label-specific timestamps.
 knots=sorted(set(active[:,0])|set(idle[:,0]))
 package=np.array([[t,interpolate_at(active,t)+interpolate_at(idle,t)] for t in knots])
 energy=package[-1,1]-package[0,1];app_energy=app[-1,1]-app[0,1]
 assert energy>0 and app_energy>0,'Non-positive energy'
 with (out/'requests.csv').open() as f:requests=list(csv.DictReader(f))
 completed=np.array([float(x['completed_epoch']) for x in requests]); bins=[]
 for a,b in zip(package[:-1],package[1:]):
  count=int(np.count_nonzero((completed>=a[0])&(completed<b[0])))
  joules=b[1]-a[1];dt=b[0]-a[0]
  bins.append({'start_epoch':a[0],'end_epoch':b[0],'duration_s':dt,'node_package_j':joules,
               'node_package_w':joules/dt,'requests':count,'j_per_request':joules/count if count else None})
 with (out/'energy_intervals.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(bins[0]));w.writeheader();w.writerows(bins)
 # Uniform one-second power grid avoids unequal boundary-bin weighting in temporal sigma.
 midpoints=np.arange(start+.5,end,1)
 rates=np.diff(package[:,1])/np.diff(package[:,0])
 indexes=np.clip(np.searchsorted(package[1:,0],midpoints,side='right'),0,len(rates)-1)
 sigma=float(np.std(rates[indexes],ddof=1)) if len(midpoints)>1 else 0.0
 full_intervals=[b for b in bins if b['duration_s']>=4 and b['requests']>0]
 ep95=float(np.percentile([b['j_per_request'] for b in full_intervals],95)) if full_intervals else None
 primary=raw['node_active'][0]['values'];scrapes=[float(t) for t,v in primary if start<=float(t)<=end]
 summary={**run,'node_package_j':float(energy),'app_attributed_package_j':float(app_energy),
          'mean_node_package_w':float(energy/(end-start)),
          'node_j_per_request':float(energy/run['requests']),
          'app_attributed_j_per_request':float(app_energy/run['requests']),
          'temporal_power_sd_w':sigma,'p95_interval_j_per_request':ep95,
          'p95_interval_count':len(full_intervals),'energy_samples_inside_window':len(scrapes),
          'counter_resets':0,'measurement_valid':True,
          'p95_energy_semantics':'95th percentile of ~5-second interval energy/completed-request ratios; NOT individual-request energy percentile'}
 write_json(out/'summary.json',summary)
 return summary

def one_run(args,run_id,stage,duration,users,block=None):
 out=ROOT/'results'/run_id;out.mkdir(parents=True,exist_ok=False)
 before=resource.getrusage(resource.RUSAGE_CHILDREN);cpu0=before.ru_utime+before.ru_stime
 cmd=[args.locust,'-f',str(ROOT/'locustfile.py'),'--headless','--host',args.host,
      '--users',str(users),'--spawn-rate',str(users),'--run-time',str(duration+args.warmup+30)+'s',
      '--measurement-duration',str(duration),'--warmup-seconds',str(args.warmup),
      '--workload-seed',str(args.seed),'--run-directory',str(out),
      '--stop-timeout','0','--only-summary','--csv',str(out/'locust'),
      '--html',str(out/'locust_report.html')]
 host_before={'temperature_c':temperatures(),'loadavg':list(os.getloadavg())}
 began=time.time();print(json.dumps({'event':'start','id':run_id,'duration':duration,'users':users,'epoch':began}),flush=True)
 with (out/'console.log').open('w') as log:
  result=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,timeout=duration+args.warmup+60)
 ended=time.time();after=resource.getrusage(resource.RUSAGE_CHILDREN)
 if not (out/'run.json').exists():raise RuntimeError(f'{run_id} missing run metadata; see {out}/console.log')
 run=json.loads((out/'run.json').read_text());run.update(run_id=run_id,stage=stage,block=block,
    locust_exit_code=result.returncode,wall_time_including_startup_s=ended-began,
    generator_cpu_s=after.ru_utime+after.ru_stime-cpu0,host_before=host_before,
    host_after={'temperature_c':temperatures(),'loadavg':list(os.getloadavg())},command=cmd)
 assert run['requests']>0,f'{run_id}: no requests'
 assert result.returncode==0 and run['failure_rate']<=.001,f'{run_id}: failed smoke/quality gate: {run["first_errors"]}'
 assert abs(run['actual_duration_s']-duration)<.5,'Measurement window timing drift'
 # Wait for at least two post-cutoff scrapes, not part of the measured window.
 time.sleep(11)
 summary=fetch_measurement(args.prometheus,out,run)
 assert summary['energy_samples_inside_window']>=2,'Too few energy samples'
 print(json.dumps({'event':'complete','id':run_id,'requests':run['requests'],'failures':run['failures'],
                   'rps':run['rps'],'package_j':summary['node_package_j'],'package_w':summary['mean_node_package_w']}),flush=True)
 return summary

def select_smoke_load():
 candidates=[]
 for p in sorted((ROOT/'results').glob('smoke-*/summary.json')):
  s=json.loads(p.read_text());raw=json.loads((p.parent/'prometheus_raw.json').read_text())['metrics']
  cpu=[float(v) for x in raw['node_usage'] for t,v in x['values'] if s['start_epoch']<=float(t)<=s['end_epoch_target']]
  candidates.append({'run_id':s['run_id'],'users':s['users'],'failures':s['failures'],'rps':s['rps'],'p95_latency_ms':s['p95_latency_ms'],'peak_node_cpu_fraction':max(cpu)})
 eligible=[r for r in candidates if r['failures']==0 and r['peak_node_cpu_fraction']<=.75 and r['p95_latency_ms']<100]
 assert eligible,'No load level passed the quality gate'
 selected=max(r['users'] for r in eligible)
 write_json(ROOT/'results/smoke_gate.json',{'passed':True,'users_selected':selected,'candidates':candidates,'selection_rule':'Highest tested user count with zero failures, observed peak node CPU <=75%, p95 latency <100 ms','checks':['complete shopping flows','zero failures','real energy data bracketing measurement','counter continuity','timing within 0.5 seconds']})
 return selected

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--host',default='http://10.152.183.142')
 p.add_argument('--prometheus',default='http://10.152.183.218:9090')
 p.add_argument('--locust',default=str(ROOT.parents[1]/'work/locust-venv/bin/locust'))
 p.add_argument('--seed',type=int,default=20261119)
 p.add_argument('--warmup',type=int,default=15)
 p.add_argument('--mode',choices=['smoke','campaign'],required=True)
 p.add_argument('--users',type=int,default=5)
 p.add_argument('--repetitions',type=int,default=8)
 p.add_argument('--durations',type=int,nargs='+',default=[15,30,60,120])
 args=p.parse_args()
 assert pathlib.Path(args.locust).exists(),args.locust
 if args.mode=='smoke':
  plans=[('smoke-u1',15,1),('smoke-u3',20,3),('smoke-u5',30,5)]
  for rid,d,u in plans:one_run(args,rid,'smoke',d,u)
  select_smoke_load()
 else:
  gate=json.loads((ROOT/'results/smoke_gate.json').read_text())
  assert gate['passed'],'Smoke gate not passed'
  assert args.users==gate['users_selected'],'Campaign load must match smoke-selected load'
  rng=random.Random(args.seed);plan=[]
  for block in range(1,args.repetitions+1):
   durations=list(args.durations);rng.shuffle(durations)
   for d in durations:plan.append({'block':block,'duration':d,'run_id':f'block{block:02d}-{d:03d}s'})
  write_json(ROOT/'results/campaign_plan.json',{'args':vars(args),'plan':plan,'randomization':'one run of each duration per randomized block','variant':'unchanged baseline only; A/A study, no injected regression'})
  summaries=[]
  for row in plan:
   summaries.append(one_run(args,row['run_id'],'campaign',row['duration'],args.users,row['block']))
   write_json(ROOT/'results/campaign_progress.json',{'completed':len(summaries),'total':len(plan),'latest':row,'started_epoch':summaries[0]['warmup_start_epoch']})
  write_json(ROOT/'results/campaign_complete.json',{'completed':len(summaries),'total':len(plan),'ended_epoch':time.time()})
if __name__=='__main__':main()
