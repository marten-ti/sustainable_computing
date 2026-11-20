#!/usr/bin/env python3
"""Decompose saved Kepler counters; no new workloads or metric queries."""
import os,pathlib,json,sys
os.environ.setdefault('MPLCONFIGDIR','/tmp/energy-study-mpl-0')
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=pathlib.Path(__file__).resolve().parent
DATA=ROOT.parents[1]/'results'
sys.path.insert(0,str(ROOT.parents[1]/'research'))
from experiment import counter_window
rows=[]
for p in sorted(DATA.glob('block*/summary.json')):
 s=json.loads(p.read_text());raw=json.loads((p.parent/'prometheus_raw.json').read_text())['metrics']
 start=s['start_epoch'];end=s['end_epoch_target'];duration=end-start
 active=counter_window(raw['node_active'],start,end);idle=counter_window(raw['node_idle'],start,end)
 a=float(active[-1,1]-active[0,1]);i=float(idle[-1,1]-idle[0,1])
 assert np.isclose(a+i,s['node_package_j'],rtol=0,atol=1e-6)
 usage=[float(v) for z in raw['node_usage'] for t,v in z['values'] if start<=float(t)<=end]
 rows.append({'run_id':s['run_id'],'block':s['block'],'duration_s':duration,
  'active_j':a,'idle_j':i,'total_j':a+i,'active_w':a/duration,'idle_w':i/duration,
  'total_w':(a+i)/duration,'active_share_pct':100*a/(a+i),
  'mean_cpu_usage_pct':100*np.mean(usage),'app_attributed_j':s['app_attributed_package_j'],
  'rps':s['rps']})
df=pd.DataFrame(rows);assert len(df)==32
df.to_csv(ROOT/'per_run.csv',index=False)
summary=[]
for d,g in df.groupby('duration_s',sort=True):
 a=g.active_j.to_numpy();i=g.idle_j.to_numpy();t=g.total_j.to_numpy()
 va=float(a.var(ddof=1));vi=float(i.var(ddof=1));cov=float(np.cov(a,i,ddof=1)[0,1]);vt=float(t.var(ddof=1))
 assert np.isclose(va+vi+2*cov,vt,atol=1e-6)
 summary.append({'duration_s':d,'n':len(g),'mean_active_j':a.mean(),'mean_idle_j':i.mean(),'mean_total_j':t.mean(),
  'mean_active_w':g.active_w.mean(),'mean_idle_w':g.idle_w.mean(),'mean_total_w':g.total_w.mean(),
  'active_share_pct':g.active_share_pct.mean(),'active_cv_pct':100*a.std(ddof=1)/a.mean(),
  'idle_cv_pct':100*i.std(ddof=1)/i.mean(),'total_cv_pct':100*t.std(ddof=1)/t.mean(),
  'active_sd_j':a.std(ddof=1),'idle_sd_j':i.std(ddof=1),'total_sd_j':t.std(ddof=1),
  'active_idle_correlation':np.corrcoef(a,i)[0,1],'active_variance_j2':va,
  'idle_variance_j2':vi,'twice_covariance_j2':2*cov,'total_variance_j2':vt})
stats=pd.DataFrame(summary);stats.to_csv(ROOT/'summary.csv',index=False)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
fig,axes=plt.subplots(1,3,figsize=(15,4.8),layout='constrained')
x=np.arange(len(stats));durations=stats.duration_s.to_numpy()
axes[0].bar(x,stats.mean_active_w,label='Modeled active',color='#377eb8')
axes[0].bar(x,stats.mean_idle_w,bottom=stats.mean_active_w,label='Modeled idle',color='#ffaf45')
for pos,s in stats.iterrows():axes[0].text(pos,s.mean_active_w/2,f'{s.active_share_pct:.1f}%',ha='center',va='center',color='white')
axes[0].set(xticks=x,xticklabels=[str(int(d)) for d in durations],xlabel='Duration (s)',ylabel='Mean CPU-package power (W)',title='Similar modeled split at every duration');axes[0].legend(loc='upper right')
for col,label,color,marker in [('total_cv_pct','Package total','#333333','o'),('active_cv_pct','Modeled active','#377eb8','s'),('idle_cv_pct','Modeled idle','#ed9425','^')]:
 axes[1].plot(x,stats[col],marker=marker,label=label,color=color)
axes[1].set(xticks=x,xticklabels=[str(int(d)) for d in durations],xlabel='Duration (s)',ylabel='Across-run energy CV (%)',title='Removing modeled idle does not restore a trend');axes[1].legend()
colors=plt.get_cmap('viridis')(np.linspace(.1,.85,4))
for d,color in zip(durations,colors):
 g=df[df.duration_s==d];a=g.active_w-g.active_w.mean();i=g.idle_w-g.idle_w.mean()
 axes[2].scatter(a,i,label=f'{int(d)} s',color=color,s=40)
axes[2].axhline(0,color='#bbb',lw=.7);axes[2].axvline(0,color='#bbb',lw=.7)
axes[2].plot([-.45,.45],[.45,-.45],'--',color='#999',lw=1,label='Unchanged total: Δidle = −Δactive')
axes[2].set(xlabel='Active-power deviation from group mean (W)',ylabel='Idle-power deviation from group mean (W)',title='Components are dependent, not independent sensors');axes[2].legend(fontsize=8,loc='lower left')
fig.suptitle('Kepler active/idle decomposition — existing eight runs per duration',fontsize=14)
for extension in ['png','svg','pdf']:fig.savefig(ROOT/('active_idle_decomposition.'+extension),dpi=180,bbox_inches='tight')
plt.close(fig)
table='| Duration | Mean active J | Mean idle J | Active CV | Idle CV | Total CV | Correlation active/idle |\n|---|---:|---:|---:|---:|---:|---:|\n'
for _,s in stats.iterrows():table+=f'| {int(s.duration_s)} s | {s.mean_active_j:.1f} | {s.mean_idle_j:.1f} | {s.active_cv_pct:.2f}% | {s.idle_cv_pct:.2f}% | {s.total_cv_pct:.2f}% | {s.active_idle_correlation:+.2f} |\n'
report='''# Active/idle decomposition of the existing pilot

## Purpose and method

No new load was generated. For all 32 original runs, the saved raw Prometheus samples of `kepler_node_cpu_active_joules_total{zone="package"}` and `kepler_node_cpu_idle_joules_total{zone="package"}` were interpolated at exactly the same cutoffs as the original report. Each pair of deltas was checked to reconstruct the reported node package total to within 0.000001 J.

## What the labels mean

Kepler uses CPU utilization to model an active/idle split of hardware-reported package energy. Per sampling interval the conceptual model is:

- active energy = package energy × CPU utilization ratio
- idle energy = package energy − active energy

The split is not two independent hardware measurements. “Idle” during load is not the energy separately measured with the server unloaded, and it is not all energy unrelated to Online Boutique. “Active” is node-wide activity and includes Locust, monitoring and other host processes. Pod attribution applies another CPU-time allocation to active energy.

Source: [Kepler power-attribution documentation](https://sustainable-computing.io/kepler/usage/power-attribution/). The guide's CPU example explicitly splits 40 W at 25% utilization into 10 W active and 30 W idle. This is a utilization-based model, not an empirical unloaded-baseline measurement.

## Observed results

'''+table+'''
![Active/idle results](active_idle_decomposition.png)

Mean active share stays around 61.7–61.9%, consistent with the observed utilization near 62%. Mean modeled idle power is roughly 16.1 W at every duration, while active power is roughly 26.0–26.1 W. Therefore there is no obvious duration-dependent shift in the average active/idle proportion explaining the CV ranking.

Both component CVs are non-monotonic with duration. Merely switching the primary metric from total to modeled active energy does not restore a consistent “longer is more stable” result.

## Why correlation matters

For the energy deltas across repetitions:

`Var(total) = Var(active) + Var(idle) + 2 × Cov(active,idle)`.

At 15 seconds the active/idle correlation is −0.67. Their sample variances are about 3.14 J² and 1.21 J², while twice their covariance is −2.62 J². The resulting total variance is only 1.73 J², giving total SD 1.31 J. Thus the total has lower relative variability than either modeled component. Utilization changes can move estimated energy between the components while total package energy changes little. This observation does not make the physical total artificially wrong; it shows why these component estimates cannot be interpreted as independent measurements.

At 30 seconds correlation is +0.47: both components more often move in the same direction. The 30-second spread is therefore not solely an active-to-idle allocation swap. At 120 seconds the first block has both high active energy and high idle energy, consistent with its higher package total. These are descriptive patterns from eight runs each, not causal diagnoses.

## What this explains and what remains open

This decomposition helps explain the unusually tight total relative to its modeled components at 15 seconds. It also shows that the wider 30-second totals are not exclusively due to idle-attribution variability. It does not identify why the underlying package totals differed. Frequency/power-state changes, instruction mix, thermal conditions, background work and measurement timing remain possible contributors and were not independently isolated.

The plots compare separate run totals, not variation within one time trace. A fixed whole-run power offset is not necessarily averaged away by increasing duration, unlike some short-lived fluctuations. This is a possible mechanism for non-monotonic CV, not a demonstrated cause in this dataset.

## Recommended follow-up

Retain the split as a diagnostic, keep the physical package-total outcome alongside performance/work-count metrics, and choose the primary metric before testing variants. Measure actual no-load baseline windows separately, preferably before and after randomized blocks. Move Locust to another host and record frequency, temperatures, process activity and delivered work. Use actual controlled regression variants and fresh A/A comparisons for detection validation. Subtracting Kepler's modeled idle term alone is not a clean isolation of application energy or a validated noise correction.

All earlier limitations remain: eight repetitions per duration, one session, five-second energy sampling, co-located generator and already-warm deployment. These analyses reuse the same data and do not add independent evidence.
'''
(ROOT/'ACTIVE_IDLE.md').write_text(report)
print(stats.round(4).to_string(index=False))
