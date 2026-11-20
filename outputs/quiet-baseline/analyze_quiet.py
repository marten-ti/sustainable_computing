#!/usr/bin/env python3
"""Report the quiet observation without treating it as a paired load experiment."""
import os,pathlib,json,datetime,csv,sys
os.environ.setdefault('MPLCONFIGDIR','/tmp/energy-study-mpl-0')
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from zoneinfo import ZoneInfo
ROOT=pathlib.Path(__file__).resolve().parent
m=json.loads((ROOT/'measurement.json').read_text());raw=json.loads((ROOT/'raw_prometheus.json').read_text())['metrics']
w=pd.read_csv(ROOT/'windows.csv')
assert m['traffic_check_passed'] and w.quiet_traffic_check_passed.all()
assert all(not x['locust_pids'] for x in m['locust_checks'])
assert (w.package_energy_j>0).all() and w.non_health_frontend_requests.sum()==0
assert np.allclose(w.modeled_active_energy_j+w.modeled_idle_energy_j,w.package_energy_j)
sys.path.insert(0,str(ROOT.parents[1]/'research'))
from experiment import counter_window
for key,col in [('node_active','modeled_active_energy_j'),('node_idle','modeled_idle_energy_j')]:
 points=counter_window(raw[key],m['start_epoch'],m['end_epoch'])
 assert np.isclose(points[-1,1]-points[0,1],w[col].sum(),atol=1e-6)
loaded=pd.read_csv(ROOT.parents[1]/'results/duration_summary.csv')
loadsplit=pd.read_csv(ROOT.parent/'active-idle-analysis/summary.csv')
l120=loaded[loaded.duration_s==120].iloc[0];s120=loadsplit[loadsplit.duration_s==120].iloc[0]
start=datetime.datetime.fromtimestamp(m['start_epoch'],ZoneInfo('Europe/Berlin'));end=datetime.datetime.fromtimestamp(m['end_epoch'],ZoneInfo('Europe/Berlin'))
quiet_active=w.modeled_active_power_w.mean();quiet_idle=w.modeled_idle_power_w.mean()
comparison=pd.DataFrame([
 {'quantity':'observed quiet CPU-package power','condition':'quiet observation, morning','power_w':m['mean_package_power_w'],'measurement_type':'counter-derived package total'},
 {'quantity':'modeled idle under quiet conditions','condition':'quiet observation, morning','power_w':quiet_idle,'measurement_type':'utilization-based partition'},
 {'quantity':'modeled idle under earlier load','condition':'earlier night session, 120-second runs','power_w':s120.mean_idle_w,'measurement_type':'utilization-based partition'},
 {'quantity':'observed package power under earlier load','condition':'earlier night session, 120-second runs','power_w':l120.mean_power_w,'measurement_type':'counter-derived package total, includes Locust'},
])
comparison.to_csv(ROOT/'comparison.csv',index=False)
points=[]
for series in raw['node_power']:
 for t,v in series['values']:
  if m['start_epoch']<=float(t)<m['end_epoch']:points.append({'epoch':float(t),'elapsed_s':float(t)-m['start_epoch'],'package_power_w':float(v)})
power=pd.DataFrame(points).sort_values('epoch');power.to_csv(ROOT/'power_samples.csv',index=False)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
fig,axes=plt.subplots(1,2,figsize=(12,4.7),layout='constrained')
axes[0].plot(power.elapsed_s,power.package_power_w,marker='.',linewidth=1,color='#377eb8')
axes[0].axhline(m['mean_package_power_w'],color='#333',linestyle='--',label=f'Overall mean {m["mean_package_power_w"]:.2f} W')
for t in [120,240]:axes[0].axvline(t,color='#bbb',linestyle=':')
axes[0].set(xlabel='Seconds from observation start',ylabel='CPU-package power (W)',title='Quiet state still contains normal background activity');axes[0].legend()
labels=['Observed quiet\npackage total','Modeled idle\nunder earlier load','Observed total\nunder earlier load']
values=[m['mean_package_power_w'],s120.mean_idle_w,l120.mean_power_w]
axes[1].bar(range(3),values,color=['#377eb8','#ffaf45','#666666'])
for i,v in enumerate(values):axes[1].text(i,v+.5,f'{v:.2f} W',ha='center')
axes[1].set(xticks=range(3),xticklabels=labels,ylabel='Power (W)',title='Different quantities and sessions — not a paired A/B test');axes[1].set_ylim(0,max(values)*1.15)
fig.suptitle('Quiet CPU-package baseline — application and monitoring remained running',fontsize=13)
for ext in ['png','svg','pdf']:fig.savefig(ROOT/('quiet_baseline.'+ext),dpi=180,bbox_inches='tight')
plt.close(fig)
table='| Window | Duration | Package energy | Mean package power | Mean CPU utilization | Non-health frontend requests |\n|---|---:|---:|---:|---:|---:|\n'
for _,r in w.iterrows():table+=f'| {int(r.window)} | 120 s | {r.package_energy_j:.1f} J | {r.mean_package_power_w:.3f} W | {r.cpu_usage_mean_pct:.2f}% | {int(r.non_health_frontend_requests)} |\n'
text=f'''# Quiet CPU-package baseline — 19 November 2026

Observation: **{start.strftime('%H:%M:%S')}–{end.strftime('%H:%M:%S')} Europe/Berlin**, after 60 seconds of settling. Three consecutive 120-second windows; six measured minutes in total. No load generator was started. Online Boutique, Redis, Kubernetes, Kepler, Prometheus and Grafana stayed deployed and running.

## Results

{table}

Mean CPU-package power: **{m['mean_package_power_w']:.3f} W**. Total measured package energy: **{m['total_package_energy_j']:.1f} J over 360 seconds**. SD of the three window-average powers: {m['between_window_sd_w']:.3f} W; descriptive CV: {m['between_window_cv_pct']:.2f}%. These adjacent windows are not independent experimental repetitions, and no population stability claim or confidence bound is inferred from them.

Across the native approximately five-second power-gauge samples, values ranged from {power.package_power_w.min():.2f} to {power.package_power_w.max():.2f} W. Quiet means no intentional shopping workload, not zero activity. Average Kepler CPU utilization remained approximately {w.cpu_usage_mean_pct.mean():.2f}%, with normal control-plane, monitoring, app background work and health probes.

![Quiet baseline](quiet_baseline.png)

## Traffic and health verification

No local Locust process was found at precheck, after settling or during repeated process checks. The frontend recorded {int(w.health_probe_requests.sum())} health-probe requests and zero completed non-health requests inside the measured interval. Pod identities and restart counts were unchanged, every pod was Ready at both checks, and all Prometheus targets were healthy afterward. Kernel/boot and CPU-governor checks matched the earlier campaign.

Energy came from the same package-only active + idle accumulated Kepler counters as the earlier study. Raw scrape samples bracket every cutoff; missing samples, excessive gaps and resets are rejected. Counter deltas over adjacent windows reconstruct the full observation delta. No sum of overlapping package/core zones is used. This is CPU-package energy, not whole-server wall power.

## Measured quiet baseline versus modeled idle

The quiet package total averaged **{m['mean_package_power_w']:.2f} W**. Under these quiet conditions, Kepler partitioned it into approximately **{quiet_active:.2f} W modeled active** and **{quiet_idle:.2f} W modeled idle**. The earlier loaded 120-second cohort averaged **{l120.mean_power_w:.2f} W package total**, of which approximately **{s120.mean_idle_w:.2f} W was labeled modeled idle**.

This illustrates the distinction: Kepler's loaded idle term is a utilization-based partition of loaded package energy, not a separately measured unloaded power baseline. The two values need not agree.

An illustrative difference between earlier loaded power and this quiet reference is {l120.mean_power_w-m['mean_package_power_w']:.2f} W. **That is not isolated application power**: the loaded study included co-located Locust, changed host activity and different CPU operating states. It was also measured hours earlier, so this is not a controlled paired before/after comparison. The quiet reference must not silently be subtracted from old runs to claim validated application energy or revised detection rates.

The earlier loaded 120-second runs had a package-energy SD of {l120.sd_energy_j:.2f} J and CV of {l120.cv_energy_pct:.2f}%, whereas these quiet windows had an energy SD of {w.package_energy_j.std(ddof=1):.2f} J and CV of {m['between_window_cv_pct']:.2f}%. A larger relative CV can coexist with smaller absolute variation because the quiet-state mean is much smaller. Sample sizes and observation periods differ, so this is descriptive rather than a variance comparison test.

## Limitations and next use

This observation was taken in the morning, hours after the loaded session; system maintenance may have run between sessions. Kernel, governor configuration and app pod identities were consistent, but that does not establish identical thermal or background conditions. Temperature snapshots were taken before the settling period and after observation; continuous thermal stability was not established. No services or security controls were stopped to force an artificial idle state.

For a controlled follow-up, take quiet windows immediately before and after randomized load blocks, keep the generator external, and record CPU frequency, temperatures and background activity. A predeclared baseline subtraction can estimate incremental package energy above quiet operation, with baseline uncertainty retained; it cannot by itself assign that energy exclusively to the application.

## Files

- `windows.csv`: measured window totals, power, CPU utilization and traffic counts.
- `power_samples.csv`: native quiet power-gauge samples.
- `comparison.csv`: explicitly labeled quiet/loaded and modeled/measured quantities.
- `raw_prometheus.json`: raw counter/power/utilization samples.
- `measurement.json`, environment/configuration and pod/target snapshots: timing and verification evidence.
- `measure_quiet.py`, `analyze_quiet.py`: measurement and reporting code. The measurement script refuses to overwrite an existing result and never launches Locust.
'''
(ROOT/'README.md').write_text(text)
print('Report complete. Mean quiet package power:',m['mean_package_power_w'],'W. Traffic check:',m['traffic_check_passed'])
