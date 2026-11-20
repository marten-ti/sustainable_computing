#!/usr/bin/env python3
"""Observe quiet CPU-package energy; never starts load or changes services."""
import collections,csv,datetime,json,math,pathlib,platform,subprocess,sys,time,urllib.parse,urllib.request
import numpy as np
import psutil
ROOT=pathlib.Path(__file__).resolve().parent
STUDY=ROOT.parents[1]
sys.path.insert(0,str(STUDY/'research'))
from experiment import counter_window,temperatures
K='/snap/microk8s/current/kubectl'
PROM='http://10.152.183.218:9090'
METRICS={
 'node_active':'kepler_node_cpu_active_joules_total{zone="package"}',
 'node_idle':'kepler_node_cpu_idle_joules_total{zone="package"}',
 'node_power':'kepler_node_cpu_watts{zone="package"}',
 'node_usage':'kepler_node_cpu_usage_ratio',
 'app_energy':'kepler_pod_cpu_joules_total{pod_namespace="online-boutique",zone="package",state="running"}',
 'node_raw':'kepler_node_cpu_joules_total{zone="package"}',
 'dram_power':'kepler_node_cpu_watts{zone="dram"}',
}
def save(name,obj):(ROOT/name).write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n')
def query(q,at):
 with urllib.request.urlopen(PROM+'/api/v1/query?'+urllib.parse.urlencode({'query':q,'time':at}),timeout=20) as r:d=json.load(r)
 assert d['status']=='success',d
 return d['data']['result']
def active_locust():
 found=[]
 for p in psutil.process_iter(['pid','name','cmdline']):
  c=p.info['cmdline'] or []
  if p.info['name']=='locust' or (len(c)>1 and c[1].endswith('/bin/locust')):found.append(p.pid)
 return found

def main():
 assert not (ROOT/'measurement.json').exists(),'Refusing to overwrite previous measurement'
 assert not active_locust(),'A load generator is active; no process will be killed automatically'
 before={'time_epoch':time.time(),'kernel':platform.release(),'boot_id':pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'temperature_c':temperatures(),'loadavg':list(__import__('os').getloadavg())}
 save('environment_before.json',before)
 print('Settling for 60 seconds; no workload will be launched.',flush=True)
 time.sleep(60)
 assert not active_locust(),'Locust started during settling'
 start=time.time();windows=[];observations=[]
 print('START quiet observation',datetime.datetime.now(datetime.timezone.utc).isoformat(),'three consecutive 120-second windows',flush=True)
 for index in range(3):
  wstart=start+120*index;wend=wstart+120
  while time.time()<wend:
   time.sleep(min(30,max(0,wend-time.time())))
   found=active_locust();observations.append({'epoch':time.time(),'locust_pids':found})
   assert not found,'Locust became active; refusing to describe this as quiet'
  windows.append({'window':index+1,'start_epoch':wstart,'end_epoch':wend,'duration_s':120})
  print('Window',index+1,'complete',flush=True)
 end=windows[-1]['end_epoch']
 after={'time_epoch':time.time(),'kernel':platform.release(),'boot_id':pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'temperature_c':temperatures(),'loadavg':list(__import__('os').getloadavg())}
 assert before['boot_id']==after['boot_id'],'Host rebooted'
 save('environment_after.json',after)
 time.sleep(11) # quiet state continues; allow post-cutoff scrapes to arrive
 at=time.time();lookback=math.ceil(at-start+20)
 raw={name:query(expr+f'[{lookback}s]',at) for name,expr in METRICS.items()}
 save('raw_prometheus.json',{'query_epoch':at,'metrics':raw})
 # Save only aggregate frontend activity, not sessions or client identifiers.
 log=subprocess.check_output([K,'--request-timeout=20s','logs','-n','online-boutique','deploy/frontend','--since-time='+datetime.datetime.fromtimestamp(start-1,datetime.timezone.utc).isoformat().replace('+00:00','Z')],text=True)
 traffic=[]
 for line in log.splitlines():
  try:x=json.loads(line)
  except ValueError:continue
  if x.get('message')!='request complete':continue
  ts=x.get('timestamp')
  try:t=datetime.datetime.fromisoformat(ts.replace('Z','+00:00')).timestamp()
  except (ValueError,AttributeError):continue
  if start<=t<end:traffic.append({'epoch':t,'path':x.get('http.req.path','unknown'),'status':x.get('http.resp.status')})
 save('frontend_activity.json',{'records':traffic,'scope':'completed frontend requests in quiet observation; health probes classified separately'})
 summary=[]
 for w in windows:
  a=counter_window(raw['node_active'],w['start_epoch'],w['end_epoch']);i=counter_window(raw['node_idle'],w['start_epoch'],w['end_epoch'])
  ae=float(a[-1,1]-a[0,1]);ie=float(i[-1,1]-i[0,1]);total=ae+ie
  watts=[float(v) for s in raw['node_power'] for t,v in s['values'] if w['start_epoch']<=float(t)<w['end_epoch']]
  usage=[float(v) for s in raw['node_usage'] for t,v in s['values'] if w['start_epoch']<=float(t)<w['end_epoch']]
  assert len(watts)>=20 and len(usage)>=20,'Insufficient samples'
  health=[r for r in traffic if w['start_epoch']<=r['epoch']<w['end_epoch'] and r['path']=='/_healthz']
  other=[r for r in traffic if w['start_epoch']<=r['epoch']<w['end_epoch'] and r['path']!='/_healthz']
  summary.append({**w,'package_energy_j':total,'mean_package_power_w':total/120,
   'modeled_active_energy_j':ae,'modeled_idle_energy_j':ie,
   'modeled_active_power_w':ae/120,'modeled_idle_power_w':ie/120,
   'cpu_usage_mean_pct':100*np.mean(usage),'cpu_usage_max_pct':100*max(usage),
   'power_gauge_sd_w':float(np.std(watts,ddof=1)),'power_gauge_min_w':min(watts),'power_gauge_max_w':max(watts),
   'scrape_samples':len(watts),'health_probe_requests':len(health),'non_health_frontend_requests':len(other),
   'quiet_traffic_check_passed':not other})
 with (ROOT/'windows.csv').open('w',newline='') as f:
  writer=csv.DictWriter(f,fieldnames=list(summary[0]));writer.writeheader();writer.writerows(summary)
 powers=np.array([r['mean_package_power_w'] for r in summary]);energies=np.array([r['package_energy_j'] for r in summary])
 save('measurement.json',{'start_epoch':start,'end_epoch':end,'settle_seconds':60,'windows':summary,'locust_checks':observations,
  'mean_package_power_w':float(powers.mean()),'total_package_energy_j':float(energies.sum()),
  'between_window_sd_w':float(powers.std(ddof=1)),'between_window_cv_pct':float(100*powers.std(ddof=1)/powers.mean()),
  'traffic_check_passed':all(r['quiet_traffic_check_passed'] for r in summary),
  'note':'Three adjacent windows, not independent repetitions. Stack stays deployed; health probes and normal background activity remain. This observation is hours after the earlier loaded campaign, not a paired before/after baseline.'})
 print('DONE',json.dumps({'mean_package_power_w':float(powers.mean()),'traffic_check_passed':all(r['quiet_traffic_check_passed'] for r in summary)}),flush=True)
if __name__=='__main__':main()
