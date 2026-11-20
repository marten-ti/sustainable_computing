#!/usr/bin/env python3
"""Generate CSVs, figures and a cautious report from the completed pilot."""
import argparse,datetime,html,itertools,json,math,pathlib
from functools import lru_cache
import numpy as np
import pandas as pd
import os,tempfile
os.environ.setdefault('MPLCONFIGDIR',str(pathlib.Path(tempfile.gettempdir())/f'energy-study-mpl-{os.getuid()}'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import NullFormatter
from matplotlib.backends.backend_pdf import PdfPages
from scipy.stats import beta,spearmanr

ROOT=pathlib.Path(__file__).resolve().parents[1]
FIG=ROOT/'figures';DATA=ROOT/'results'
RNG=np.random.default_rng(20261119)

@lru_cache(None)
def permutations(n):
 comb=list(itertools.combinations(range(2*n),n))
 signs=np.full((len(comb),2*n),-1/n,dtype=float)
 for i,c in enumerate(comb):signs[i,list(c)]=1/n
 return signs

def permutation_p(a,b):
 a=np.asarray(a,float);b=np.asarray(b,float);n=len(a)
 assert n==len(b) and n>=1
 v=np.r_[a,b];observed=b.mean()-a.mean()
 null=permutations(n)@v
 return float(np.mean(null>=observed-1e-10))

def cv(a):
 a=np.asarray(a,float)
 return float(np.std(a,ddof=1)/np.mean(a))

def cv_interval(a):
 a=np.asarray(a,float)
 sampled=RNG.choice(a,size=(10000,len(a)),replace=True)
 boots=sampled.std(axis=1,ddof=1)/sampled.mean(axis=1)
 return tuple(np.percentile(boots,[2.5,97.5]))

def simulate(values,n,effect):
 """All disjoint A/B subsets, conditional on this small observed noise pool."""
 values=np.asarray(values,float);indices=range(len(values));results=[]
 for ia in itertools.combinations(indices,n):
  rest=[i for i in indices if i not in ia]
  for ib in itertools.combinations(rest,n):
   a=values[list(ia)];b=values[list(ib)]*(1+effect)
   results.append(permutation_p(a,b)<=.05+1e-12)
 return float(np.mean(results)),len(results)

def savefig(fig,name):
 fig.savefig(FIG/(name+'.png'),dpi=180,bbox_inches='tight')
 fig.savefig(FIG/(name+'.svg'),bbox_inches='tight')
 return fig

def read_runs():
 summaries=[]
 for p in sorted(DATA.glob('block*/summary.json')):
  s=json.loads(p.read_text());summary={k:v for k,v in s.items() if not isinstance(v,(dict,list))}
  summary['temperature_before_max_c']=max(s['host_before']['temperature_c'].values())
  summary['temperature_after_max_c']=max(s['host_after']['temperature_c'].values())
  summary['generator_mean_cpu_cores_including_warmup']=s['generator_cpu_s']/s['wall_time_including_startup_s']
  raw=json.loads((p.parent/'prometheus_raw.json').read_text())['metrics']
  gauge=[float(v) for series in raw['node_power'] for t,v in series['values'] if s['start_epoch']<=float(t)<=s['end_epoch_target']]
  summary['gauge_temporal_power_sd_w']=float(np.std(gauge,ddof=1))
  summary['gauge_mean_power_w']=float(np.mean(gauge))
  usage=[float(v) for series in raw['node_usage'] for t,v in series['values'] if s['start_epoch']<=float(t)<=s['end_epoch_target']]
  summary['peak_node_cpu_fraction']=max(usage)
  intervals=pd.read_csv(p.parent/'energy_intervals.csv')
  full=intervals[(intervals.start_epoch>s['start_epoch']+1e-6)&(intervals.end_epoch<s['end_epoch_target']-1e-6)]
  summary['temporal_normalized_5s_energy_sd_j']=float((full.node_package_w*5).std(ddof=1))
  summary['temporal_interval_energy_samples']=len(full)
  summary['block']=int(s['block']);summary['duration_s']=s['requested_duration_s']
  summaries.append(summary)
 return pd.DataFrame(summaries).sort_values(['start_epoch'])

def summary_table(df):
 rows=[]
 for duration,g in df.groupby('duration_s',sort=True):
  ci=cv_interval(g['node_package_j']);appci=cv_interval(g['app_attributed_package_j'])
  rows.append({'duration_s':duration,'repetitions':len(g),
   'mean_energy_j':g.node_package_j.mean(),'sd_energy_j':g.node_package_j.std(ddof=1),
   'cv_energy_pct':100*cv(g.node_package_j),'cv_ci_low_pct':100*ci[0],'cv_ci_high_pct':100*ci[1],
   'mean_app_attributed_energy_j':g.app_attributed_package_j.mean(),
   'cv_app_attributed_energy_pct':100*cv(g.app_attributed_package_j),
   'cv_app_ci_low_pct':100*appci[0],'cv_app_ci_high_pct':100*appci[1],
   'mean_power_w':g.mean_node_package_w.mean(),'mean_requests':g.requests.mean(),
   'mean_rps':g.rps.mean(),'cv_rps_pct':100*cv(g.rps),
   'requests_total':int(g.requests.sum()),'failures_total':int(g.failures.sum()),
   'failure_rate_pct':100*g.failures.sum()/g.requests.sum(),
   'mean_p95_latency_ms':g.p95_latency_ms.mean(),
   'mean_j_per_request':g.node_j_per_request.mean(),
   'mean_p95_interval_j_per_request':g.p95_interval_j_per_request.mean(),
   'mean_temporal_power_sd_w':g.temporal_power_sd_w.mean(),
   'mean_gauge_temporal_power_sd_w':g.gauge_temporal_power_sd_w.mean(),
   'mean_temporal_normalized_5s_energy_sd_j':g.temporal_normalized_5s_energy_sd_j.mean(),
   'mean_actual_duration_s':g.actual_duration_s.mean(),
   'min_energy_samples':int(g.energy_samples_inside_window.min()),
   'max_energy_samples':int(g.energy_samples_inside_window.max()),
   'mean_wall_time_with_startup_warmup_guard_s':g.wall_time_including_startup_s.mean(),
   'measured_energy_total_j':g.node_package_j.sum()})
 return pd.DataFrame(rows)

def stability_comparisons(df):
 durations=sorted(df.duration_s.unique())
 wide=df.pivot(index='block',columns='duration_s',values='node_package_j').sort_index()
 indexes=np.random.default_rng(20261119).integers(0,len(wide),size=(10000,len(wide)))
 rows=[]
 for shorter,longer in zip(durations[:-1],durations[1:]):
  a=wide[shorter].to_numpy();b=wide[longer].to_numpy()
  acv=a[indexes].std(axis=1,ddof=1)/a[indexes].mean(axis=1)
  bcv=b[indexes].std(axis=1,ddof=1)/b[indexes].mean(axis=1)
  improvement=1-cv(b)/cv(a)
  sampled=1-bcv/np.maximum(acv,1e-12)
  lo,hi=np.percentile(sampled,[2.5,97.5])
  rows.append({'shorter_duration_s':shorter,'longer_duration_s':longer,
   'relative_cv_improvement_pct':100*improvement,'bootstrap_ci_low_pct':100*lo,
   'bootstrap_ci_high_pct':100*hi,'small_change_screen':bool(abs(improvement)<.1),
   'interpretation':'exploratory paired-block bootstrap; not proof of a stable CV plateau'})
 return pd.DataFrame(rows)

def reliability(df):
 rows=[];observed=[];labels=['A','B','B','A','A','B','B','A']
 for duration,g in df.groupby('duration_s',sort=True):
  values=g.sort_values('block').node_package_j.to_numpy()
  for n in [2,3,4]:
   if 2*n>len(values):continue
   for effect in [0,.05,.10,.20,.30]:
    rate,count=simulate(values,n,effect)
    rows.append({'duration_s':duration,'repetitions_per_variant':n,'simulated_energy_increase_pct':effect*100,
                 'conditional_detection_rate_pct':rate*100,'disjoint_subset_assignments':count,
                 'test_alpha':.05,'minimum_attainable_p':1/math.comb(2*n,n),
                 'estimated_measured_window_energy_per_comparison_j':float(n*(2+effect)*g.node_package_j.mean()),
                 'estimated_elapsed_per_comparison_s':float(2*n*(g.wall_time_including_startup_s.mean())),
                 'interpretation':'conditional small-pool simulation; NOT independent empirical detection/false-alarm validation'})
   a=[values[i] for i in range(2*n) if labels[i]=='A'];b=[values[i] for i in range(2*n) if labels[i]=='B']
   p=permutation_p(a,b)
   observed.append({'duration_s':duration,'repetitions_per_variant':n,'p_one_sided':p,
                    'false_alarm':p<=.05+1e-12,'mean_a_j':np.mean(a),'mean_b_j':np.mean(b),
                    'relative_difference_pct':100*(np.mean(b)/np.mean(a)-1),
                    'note':'predefined A/A pseudo labels; comparisons overlap and are not independent trials'})
 return pd.DataFrame(rows),pd.DataFrame(observed)

def timeline(df):
 columns={}
 for rid in df.run_id:
  raw=json.loads((DATA/rid/'prometheus_raw.json').read_text())['metrics']
  for key in ['node_power','dram_power','app_power','node_usage']:
   points={}
   for series in raw[key]:
    for t,v in series['values']:points[float(t)]=points.get(float(t),0)+float(v)
   columns.setdefault(key,{}).update(points)
 rows=[]
 for t in sorted(columns['node_power']):
  row={'epoch':t,'time_utc':datetime.datetime.fromtimestamp(t,datetime.timezone.utc).isoformat()}
  for k,vals in columns.items():row[k]=vals.get(t,np.nan)
  active=df[(df.start_epoch<=t)&(df.end_epoch_target>t)]
  warmup=df[(df.warmup_start_epoch<=t)&(df.start_epoch>t)]
  row['phase']='measurement' if len(active) else ('warmup' if len(warmup) else 'between_runs')
  row['run_id']=active.iloc[0].run_id if len(active) else ''
  rows.append(row)
 return pd.DataFrame(rows)

def plots(df,table,power,reliability_df):
 plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
 durations=table.duration_s.to_numpy();colors=plt.get_cmap('viridis')(np.linspace(.12,.88,len(durations)))
 fig,axes=plt.subplots(2,2,figsize=(12,8),layout='constrained')
 for c,d in zip(colors,durations):
  g=df[df.duration_s==d];jitter=np.linspace(-.08,.08,len(g))
  axes[0,0].scatter(np.log2(d)+jitter,g.node_package_j,color=c,alpha=.75,s=25)
 axes[0,0].errorbar(np.log2(durations),table.mean_energy_j,yerr=table.sd_energy_j,fmt='ko-',capsize=4,label='Mean ± run SD')
 axes[0,0].set(xticks=np.log2(durations),xticklabels=durations,xlabel='Measured duration (s)',ylabel='Node CPU package energy (J)',title='Energy cost grows with duration');axes[0,0].legend()
 axes[0,1].errorbar(durations,table.cv_energy_pct,yerr=np.array([table.cv_energy_pct-table.cv_ci_low_pct,table.cv_ci_high_pct-table.cv_energy_pct]),fmt='o-',capsize=4,label='Node package')
 axes[0,1].errorbar(durations,table.cv_app_attributed_energy_pct,yerr=np.array([table.cv_app_attributed_energy_pct-table.cv_app_ci_low_pct,table.cv_app_ci_high_pct-table.cv_app_attributed_energy_pct]),fmt='s--',capsize=4,label='App attribution estimate')
 axes[0,1].set(xscale='log',xticks=durations,xticklabels=durations,xlabel='Measured duration (s)',ylabel='Energy CV across runs (%)',title='Stability, with bootstrap 95% intervals');axes[0,1].legend()
 for c,d in zip(colors,durations):
  g=df[df.duration_s==d];axes[1,0].scatter(np.repeat(d,len(g)),g.rps,color=c,alpha=.7)
 axes[1,0].plot(durations,table.mean_rps,'k.-')
 axes[1,0].set(xscale='log',xticks=durations,xticklabels=durations,xlabel='Measured duration (s)',ylabel='Completed HTTP requests/s',title='Fixed users; throughput remains an outcome')
 for c,d in zip(colors,durations):
  g=df[df.duration_s==d];axes[1,1].scatter(np.repeat(d,len(g)),g.node_j_per_request,color=c,alpha=.7)
 axes[1,1].plot(durations,table.mean_j_per_request,'k.-')
 axes[1,1].set(xscale='log',xticks=durations,xticklabels=durations,xlabel='Measured duration (s)',ylabel='Node package energy / request (J)',title='Mean energy cost per completed HTTP request')
 for ax in [axes[0,1],axes[1,0],axes[1,1]]:ax.xaxis.set_minor_formatter(NullFormatter())
 fig.suptitle('Preliminary duration study — baseline only; generator shares the host',fontsize=14)
 figs=[savefig(fig,'duration_overview')]
 fig,axes=plt.subplots(2,1,figsize=(12,7),layout='constrained',sharex=True)
 origin=df.warmup_start_epoch.min();x=(power.epoch-origin)/60
 axes[0].plot(x,power.node_power,label='Node CPU package',lw=1)
 axes[0].plot(x,power.app_power,label='App attribution estimate',lw=1)
 for c,d in zip(colors,durations):
  for i,row in df[df.duration_s==d].iterrows():axes[0].axvspan((row.start_epoch-origin)/60,(row.end_epoch_target-origin)/60,color=c,alpha=.1)
 axes[0].set(ylabel='Power (W)',title='Time series: shaded intervals are measured; gaps include warm-up/guard');axes[0].legend()
 axes[1].plot(x,100*power.node_usage,color='#5c3d91',lw=1,label='Kepler node CPU utilization')
 axes[1].set(xlabel='Minutes from campaign warm-up start',ylabel='Node CPU utilization (%)');axes[1].legend()
 figs.append(savefig(fig,'power_timeline'))
 fig,axes=plt.subplots(1,2,figsize=(12,4),layout='constrained')
 for c,d in zip(colors,durations):
  g=df[df.duration_s==d].sort_values('block');axes[0].plot(g.block,g.mean_node_package_w,'o-',color=c,label=f'{int(d)} s');axes[1].plot(g.block,g.temperature_after_max_c,'o-',color=c,label=f'{int(d)} s')
 axes[0].set(xlabel='Randomized block',ylabel='Mean package power (W)',title='Check for between-block drift');axes[0].legend(ncol=2)
 axes[1].set(xlabel='Randomized block',ylabel='Maximum recorded CPU/chip sensor (°C)',title='Temperature snapshot immediately after each run')
 figs.append(savefig(fig,'drift_and_temperature'))
 fig,axes=plt.subplots(1,2,figsize=(12,4),layout='constrained')
 for ax,effect in zip(axes,[10,20]):
  sub=reliability_df[reliability_df.simulated_energy_increase_pct==effect]
  pivot=sub.pivot(index='repetitions_per_variant',columns='duration_s',values='conditional_detection_rate_pct')
  im=ax.imshow(pivot.to_numpy(),vmin=0,vmax=100,cmap='YlGnBu',aspect='auto')
  ax.set(xticks=range(len(pivot.columns)),xticklabels=[int(x) for x in pivot.columns],yticks=range(len(pivot.index)),yticklabels=pivot.index,xlabel='Duration per run (s)',ylabel='Repetitions per variant',title=f'Simulated +{effect}% energy increase')
  for i in range(len(pivot.index)):
   for j in range(len(pivot.columns)):ax.text(j,i,f'{pivot.iloc[i,j]:.0f}%',ha='center',va='center',color='white' if pivot.iloc[i,j]>60 else 'black')
 fig.colorbar(im,ax=axes,label='Conditional simulated detection (%)',shrink=.85)
 fig.suptitle('Planning simulation from 8 baseline runs — no actual regression measured',fontsize=13)
 figs.append(savefig(fig,'conditional_detection'))
 return figs

def markdown_table(frame,columns):
 header='| '+' | '.join(label for col,label,fmt in columns)+' |\n'
 header+='| '+' | '.join('---' for _ in columns)+' |\n'
 for _,row in frame.iterrows():
  vals=[format(row[c],fmt) if fmt else str(row[c]) for c,label,fmt in columns]
  header+='| '+' | '.join(vals)+' |\n'
 return header

def make_report(df,table,rel,aa,figures):
 totalrequests=int(df.requests.sum());failures=int(df.failures.sum());energy=df.node_package_j.sum()
 start=datetime.datetime.fromtimestamp(df.warmup_start_epoch.min(),datetime.timezone.utc)
 end=datetime.datetime.fromtimestamp(df.end_epoch_target.max(),datetime.timezone.utc)
 cvbest=table.loc[table.cv_energy_pct.idxmin()];appbest=table.loc[table.cv_app_attributed_energy_pct.idxmin()];short=table.iloc[0];long=table.iloc[-1]
 monotonic=bool(np.all(np.diff(table.cv_energy_pct)<=0))
 gate=json.loads((DATA/'smoke_gate.json').read_text());users=gate['users_selected']
 # No independent FPR estimate: list real A/A outcomes but do not treat overlapping tests as independent.
 aa4=aa[aa.repetitions_per_variant==4]
 aa_false=int(aa4.false_alarm.sum())
 rho,p=spearmanr(df.start_epoch,df.mean_node_package_w)
 summary={'campaign_runs':len(df),'repetitions_per_duration':int(table.repetitions.min()),'requests':totalrequests,'failures':failures,'measured_package_energy_j':float(energy),'measured_seconds':float(df.duration_s.sum()),'campaign_elapsed_s':float(df.end_epoch_target.max()-df.warmup_start_epoch.min()),'lowest_observed_cv_duration_s':int(cvbest.duration_s),'lowest_observed_cv_pct':float(cvbest.cv_energy_pct),'cv_monotonically_decreases':monotonic,'actual_regression_tested':False,'reliability_certified':False,'n4_predefined_aa_tests':len(aa4),'n4_false_alarms':aa_false,'mean_power_order_spearman_rho':float(rho),'mean_power_order_spearman_p':float(p)}
 (DATA/'findings.json').write_text(json.dumps(summary,indent=2)+'\n')
 tabletext=markdown_table(table,[('duration_s','Duration (s)', '.0f'),('repetitions','Runs','.0f'),('mean_energy_j','Mean package J','.1f'),('sd_energy_j','SD J','.1f'),('cv_energy_pct','CV %','.2f'),('mean_rps','Req/s','.1f'),('mean_j_per_request','J/HTTP request','.4f'),('mean_p95_latency_ms','Mean p95 latency ms','.1f')])
 smoke=pd.DataFrame(gate['candidates'])
 smoketext=markdown_table(smoke,[('users','Users','.0f'),('rps','Req/s','.1f'),('failures','Failures','.0f'),('p95_latency_ms','p95 latency ms','.1f'),('peak_node_cpu_fraction','Peak CPU fraction','.3f')])
 aa_text=markdown_table(aa4,[('duration_s','Duration (s)','.0f'),('p_one_sided','A/A p-value','.4f'),('relative_difference_pct','Pseudo B vs A %','.2f')])
 planning=rel[(rel.simulated_energy_increase_pct.isin([10,20]))&(rel.repetitions_per_variant.isin([3,4]))]
 plantext=markdown_table(planning,[('duration_s','Duration (s)','.0f'),('repetitions_per_variant','n per variant','.0f'),('simulated_energy_increase_pct','Simulated increase %','.0f'),('conditional_detection_rate_pct','Conditional detection %','.1f')])
 report=f'''# Preliminary energy benchmark results

## Main finding

Completed **{len(df)} baseline runs**: eight repetitions at each of 15, 30, 60 and 120 seconds, after smoke testing. There were **{totalrequests:,} measured HTTP requests and {failures} failures**. All runs used {users} concurrent users, no think-time pauses, the same shopping scenario and per-user seed. **These results do not establish a shortest reliable regression-detection duration.** No actual regression variant was run, and eight baseline repetitions per duration cannot validate both 80% detection and a 5% false-alarm ceiling.

The lowest observed node-energy CV was **{cvbest.cv_energy_pct:.2f}% at {int(cvbest.duration_s)} seconds**. CV decreased monotonically with duration: **{monotonic}**. The 120-second runs consumed **{long.mean_energy_j/short.mean_energy_j:.2f}×** the mean measured package energy of 15-second runs. Bootstrap intervals and temporal drift checks below must be considered before treating an apparent CV improvement as stable. The application pod-attribution estimate had its lowest CV at **{int(appbest.duration_s)} seconds ({appbest.cv_app_attributed_energy_pct:.2f}%)**, rather than the node metric's minimum. Attribution is not an independent hardware measurement; choosing a duration from node CV alone would be premature.

Campaign measurement span: {start.isoformat()} to {end.isoformat()} (UTC; add one hour for Berlin). Measured windows total {df.duration_s.sum()/60:.1f} minutes. Wall span including intervening warm-up/guard: {(df.end_epoch_target.max()-df.warmup_start_epoch.min())/60:.1f} minutes. Summed CPU-package energy inside measured windows: {energy/1000:.2f} kJ; this excludes setup, warm-up, the excluded guard and report generation.

## Results by duration

{tabletext}

![Duration, stability, throughput and energy per request](figures/duration_overview.png)

`results/stability_comparisons.csv` quantifies relative CV changes between consecutive duration doublings, with paired-block bootstrap intervals. Small observed changes do not prove a plateau. `results/duration_summary.csv` also contains bootstrap CV confidence intervals, application attribution estimates, energy sample counts, interval energy/request percentiles and temporal power variation. Across-repetition SD is in joules. The CSV field `temporal_normalized_5s_energy_sd_j` separately gives within-run SD of native, fully enclosed energy intervals after normalizing their power × 5 seconds to a common five-second energy increment. Partial boundary intervals are excluded; this is not SD of a rising cumulative counter. Short runs provide very few such intervals. Within-run temporal variation is the SD of the reconstructed power curve in watts, evaluated on a common one-second grid; that grid does not create extra independent measurements. The CSV also reports SD of Kepler's power-gauge samples. Differences between counter-derived and gauge-based variation can reflect unsynchronized exporter/scrape timing and repeated counter snapshots, rather than real power excursions.

## Smoke tests and quality gates

{smoketext}

Selected {users} users using a pre-campaign rule: zero failures, observed peak node CPU ≤75%, p95 HTTP latency <100 ms. The 5-user stage is excluded if it exceeds the CPU headroom rule, even with no errors. Smoke runs are excluded from the duration analysis. All campaign runs must have ≤0.1% request failures, positive node/app energy, no counter resets, complete raw samples bracketing both cutoffs, no scrape gap >10.5 seconds, and measurement timer drift <0.5 seconds. The actual campaign failure count was {failures}. Health and target checks are recorded separately.

## Calibration and cutoff correction

The initial revision stopped load exactly at the cutoff. With five-second energy samples, interpolation across the resulting load-to-idle step can bias short windows. Collection was stopped when this design issue was identified; all revision-1 data are retained in `calibration_v1/` and excluded from the main analysis before the revised campaign. Revision 2 keeps the same loaded guard beyond every cutoff and was re-smoke-tested before the final campaign. No runs were excluded based on their energy/CV results.

## What was changed in the cloned project

The original repo at `/root/sustainable_computing`, revision `1d9ef66`, contained only `pipeline.py`; it did not contain the referenced Locust file. Its metric `kepler_container_joules_total` does not exist in this Kepler version, and its `monitoring` namespace would select the monitoring stack instead of the application. It also redeployed the application, warmed up without load and included Locust startup in the interval.

An isolated Git working copy on `codex/preliminary-energy-study` adds a seeded Locust workload, a guarded local experiment controller and this analysis. It operates against the existing deployment and does not deploy a new application version, introduce an artificial CPU regression, or create a CI/CD pipeline. Original code is preserved in `research/original_pipeline.py`.

## Workload and experiment protocol

Each user continuously repeats home → product → add-to-cart → cart → mock checkout. Product selection uses a separate PRNG seeded by `20261119 + user_id` in every run. HTTP status and response content are checked. There are no think-time sleeps. Every run has a 15-second loaded warm-up after all users spawn, an exact measurement window and an 11-second loaded post-cutoff guard. The load remains active through the guard so boundary interpolation does not mix a post-test transition to idle into the measured interval. Only request completions inside the measurement window enter the reported totals; raw Locust console totals include the guard and are diagnostic rather than the authoritative measured totals. Authoritative per-operation data are in `measured_stats.csv`; asynchronous built-in Locust CSV output is disabled after a shutdown writer race was observed during smoke testing. Eight randomized complete blocks each contain one run of every duration; `results/campaign_plan.json` records the order.

Fixed users define a **closed-loop concurrency workload**, not a constant arrival rate. Throughput is an outcome, and the same seed reproduces each user's product-selection prefix rather than a bit-identical global request schedule. Response-dependent task completion and concurrent scheduling change the total number/interleaving of requests. A complete journey contains five instrumented Locust HTTP operations. Redirect chains are counted as one operation by Locust, so the denominator is not a server-side wire-request count. Static browser assets are not fetched.

## Energy measurement and the requested p95 metric

Primary energy is the change in Kepler's **node CPU-package active + idle accumulated energy counters**, in joules. Secondary energy is the sum of `kepler_pod_cpu_joules_total{{pod_namespace="online-boutique",zone="package",state="running"}}` deltas for all 11 pods. The primary sum reconstructs package energy; its active/idle split and all per-pod allocations are estimates. RAPL is hardware-reported package energy, not whole-server wall-socket energy. Package and core zones are not added together; DRAM power is retained separately.

Prometheus raw range-vector samples are saved for every run. Boundaries use linear interpolation between adjacent raw scrape samples, with the same [start,end) window used for completed-request counts. No missing metric is silently treated as zero, and no Prometheus `increase()` extrapolation is used. The native sampling interval is about five seconds: the 15-second windows contain only about three samples. Boundary interpolation smooths short windows and can influence their apparent CV. This resolution limits how finely a minimum duration can be studied.

**True p95 energy per individual request is unavailable from these aggregate counters.** The CSV field `p95_interval_j_per_request` is explicitly a proxy: for each approximately five-second energy interval, divide package joules by the number of HTTP requests completed in that interval, then take the 95th percentile of those ratios. Partial intervals shorter than four seconds are excluded. This is neither p95 request latency nor p95 independently measured request energy. `node_j_per_request` is the run mean J/completed HTTP request. Temporal overlap and co-located work remain included.

## A/A checks and regression-detection planning

The actual experiment contains only the unchanged baseline. Predefined pseudo labels by randomized block are A,B,B,A,A,B,B,A. For n=4, the exact one-sided permutation tests below compare four A-labelled runs with four B-labelled runs at each duration. They test for an increase in mean package energy:

{aa_text}

There were {aa_false} rejections among these four duration-specific A/A checks. These are few checks under shared host conditions, and smaller-n tests reuse data. They do **not** demonstrate a long-run false-alarm rate ≤5%. Even zero false alarms would require at least 59 independent A/A comparisons for a one-sided 95% binomial upper bound below 5%, assuming independent identically distributed trials.

For planning only, we exhaustively choose disjoint A/B subsets from each duration's eight baseline runs and multiply B energies by a known 5%, 10%, 20% or 30%. The test is an exact one-sided permutation test at α=0.05. Effect sizes refer to node CPU-package energy increases, not code slowdown or isolated application energy increases; background and generator energy affect that relationship. The following rates are conditional simulated sensitivity under multiplicative energy shifts with unchanged sampled noise, not measurements of actual code regressions. The CSV also includes nominal comparison time (2 × n runs including warm-up/guard/startup) and estimated measured-window energy cost. It excludes unmeasured warm-up/guard energy and all CI/CD deployment overhead:

{plantext}

![Conditional detection planning](figures/conditional_detection.png)

With n=2 per variant, the smallest attainable exact p-value is 1/6, so this test cannot reject at 5%. With n=3 it is 1/20=0.05, and with n=4 it is 1/70. Reusing the same eight baseline observations makes simulated percentages optimistic or unstable as general forecasts. Enumerated A/A rejection rates reflect the permutation test's conditional calibration; they are not independent validation of the real deployment's false-alarm rate. In particular, no duration is certified as meeting the RQ's reliability target.

## Drift and environmental limitations

![Measured power through the campaign](figures/power_timeline.png)

![Block drift and temperature](figures/drift_and_temperature.png)

Spearman correlation between run order and mean package power was {rho:.3f} (exploratory p={p:.4g}; no causal interpretation). Randomized blocks reduce systematic order effects but do not remove temporal autocorrelation or background activity.

- **Load generator and SUT share the same physical host/kernel.** The node metric includes Locust, Kubernetes, Prometheus, Grafana, SSH and other host work. Application attribution is useful context, not a clean subtraction or independent hardware measurement. Generator CPU time is recorded as a diagnostic; it includes startup, warm-up and report writing.
- Security updates completed before the study. The running kernel was held unchanged; a newer installed kernel awaits a separate planned reboot. Daily maintenance timers were inspected and did not overlap the planned campaign. No firewall, SSH, exporter, scrape interval, resource requests, service replica count or CPU-governor changes were made for these tests.
- Kepler retains existing process exports and debug logging. Monitoring overhead and the effect of UI queries are not isolated. This is a single machine, single application revision, single workload level and one session.
- A fixed closed-loop user count does not guarantee identical completed work. A slower future variant may complete fewer operations within the same duration; assess total energy together with throughput, failures and J/operation.
- Multiple duration/effect/n comparisons are exploratory; selecting a favorable candidate on these data requires independent confirmation, with appropriate control of the final decision rule.
- Eight observations per duration give imprecise CV confidence intervals and weak independent evidence about detection/false alarms. The CV plateau screen (less than 10% relative improvement per duration doubling) is exploratory and does not establish a stable asymptote.
- The application was not redeployed or restarted between repetitions. These runs characterize an already-warm, long-lived deployment; they do not include fresh-deployment, container-startup or cold-cache variance.
- This pilot is not a CI/CD-overhead experiment. Per-run wall time is saved, but reporting and environment setup energy are excluded from measured benchmark energy. A later experiment must measure end-to-end pipeline cost separately.

## Practical next experiment

The planned +5% to +30% models saturate at 100% conditional detection for n≥3 at every duration in this small sample. They therefore do not discriminate duration choices here. Smaller effects and independent actual-regression tests are needed; a minimum duration is always conditional on a defined effect size.

Use an external load generator, freeze and record the environment after any planned reboot, and keep the same workload/cutoff rule. Collect a fresh randomized/block-balanced baseline, then run actual controlled regression variants at explicitly defined effect sizes. Predefine the comparison test, α, practical effect size and n. Validate detection and false alarms on **independent** A/B and A/A comparison batches, not resampling of the selection data. Use the present CV and conditional power plots to choose a smaller candidate grid; retain a longer reference duration to check whether the apparent stability improvement persists.

For an illustrative precision target, 59 independent A/A comparisons with zero false alarms are needed for a one-sided 95% upper confidence bound below 5%; hundreds may be needed to estimate detection rates near the 80% boundary precisely. Duration and repetition count must be chosen together and assessed against benchmark energy plus pipeline overhead.

## Files and rerunning

- `results/runs.csv`: one row per measured run, with workload, energy, latency, timing and quality fields.
- `results/duration_summary.csv`: means, SD, CV and bootstrap intervals by duration.
- `results/stability_comparisons.csv`: paired-block bootstrap comparisons of CV improvement.
- `results/conditional_detection.csv`: conditional resampling estimates for effect size × duration × n.
- `results/aa_comparisons.csv`: predefined actual baseline-versus-baseline comparisons.
- `results/power_timeline.csv`: raw scrape-derived power/CPU timeline.
- `results/block*/`: raw Prometheus samples, per-request completions, interval energy CSV, measured operation CSV, Locust console output and run metadata.
- `research/protocol.json`: analysis and experiment design recorded before the campaign.
- `figures/`: PNG/SVG figures and `report.pdf` containing summary and charts.

Install the pinned dependencies in a Python environment, then use `python pipeline.py --mode smoke`, followed by `python pipeline.py --mode campaign --users {users} --repetitions 8`, and `python pipeline.py --mode analyze`. The controller refuses to overwrite existing run directories; archive/move the existing `results/` before a fresh campaign. Host and Prometheus URLs can be overridden. No application deployment is performed by this entry point.

Sources: [Locust workload behavior](https://docs.locust.io/en/stable/writing-a-locustfile.html), [Kepler energy attribution](https://sustainable-computing.io/kepler/usage/power-attribution/), [Prometheus query functions](https://prometheus.io/docs/prometheus/latest/querying/functions/). Most reported facts are direct observations from the saved raw data.
'''
 (ROOT/'REPORT.md').write_text(report)
 # A standalone HTML index uses local figure files and CSV links; no network dependencies.
 display=table[['duration_s','repetitions','mean_energy_j','cv_energy_pct','mean_rps','mean_j_per_request']].to_html(index=False,float_format=lambda x:f'{x:.3f}')
 body=f'''<!doctype html><meta charset="utf-8"><title>Preliminary energy results</title><style>body{{font:17px system-ui;max-width:1150px;margin:40px auto;padding:0 20px;color:#17212b}}img{{width:100%;height:auto}}table{{border-collapse:collapse;width:100%}}td,th{{padding:9px;border-bottom:1px solid #ddd;text-align:right}}.note{{background:#fff1cc;padding:16px;border-radius:8px}}</style><h1>Preliminary energy benchmark results</h1><p>{len(df)} runs, {totalrequests:,} HTTP requests, {failures} failures; {users} users without think-time pauses.</p><p class="note">Baseline-only pilot. Locust shares the measured host. No minimum reliable duration is certified; detection charts are simulations, not actual regression tests.</p>{display}<p>Lowest observed CV: {cvbest.cv_energy_pct:.2f}% at {int(cvbest.duration_s)} seconds; uncertainty is shown below.</p>'''
 for title,name in [('Duration and stability','duration_overview'),('Power timeline','power_timeline'),('Drift and temperature','drift_and_temperature'),('Conditional planning simulation','conditional_detection')]:body+=f'<h2>{title}</h2><img src="figures/{name}.png" alt="{title}">'
 body+='<h2>Data and method</h2><p><a href="REPORT.md">Full report and limitations</a> · <a href="results/runs.csv">Per-run CSV</a> · <a href="results/duration_summary.csv">Duration summary CSV</a> · <a href="figures/report.pdf">PDF charts</a></p>'
 (ROOT/'report.html').write_text(body)
 with PdfPages(FIG/'report.pdf') as pdf:
  intro=plt.figure(figsize=(11.7,8.3));intro.text(.06,.92,'Preliminary Online Boutique energy study',fontsize=20,weight='bold')
  intro.text(.06,.83,f'{len(df)} baseline runs · {totalrequests:,} HTTP requests · {failures} failures\n{users} fixed users, no think-time pauses · durations 15/30/60/120 s',fontsize=13)
  lines=['No shortest reliable duration has been established.','Baseline-only data; conditional sensitivity is not actual regression detection.','Generator shares the measured node: package energy includes its overhead.',f'Lowest observed CV: {cvbest.cv_energy_pct:.2f}% at {int(cvbest.duration_s)} seconds.','See REPORT.md for confidence intervals, definitions and limitations.']
  intro.text(.06,.66,'\n\n'.join(lines),fontsize=12,va='top')
  intro.text(.06,.22,'Primary measure: Kepler node CPU package energy (J).\nSecondary measure: estimated application pod attribution.\nNative sampling: about 5 seconds; interval boundaries are interpolated.\nNo deployment, actual regression or CI/CD pipeline was introduced.',fontsize=11)
  pdf.savefig(intro);plt.close(intro)
  for fig in figures:pdf.savefig(fig,bbox_inches='tight')
 for fig in figures:plt.close(fig)
 return summary

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--allow-incomplete',action='store_true');args=parser.parse_args()
 if not args.allow_incomplete:assert (DATA/'campaign_complete.json').exists(),'Campaign incomplete'
 FIG.mkdir(exist_ok=True)
 df=read_runs();assert len(df)>0
 if not args.allow_incomplete:assert len(df)==32 and all(df.groupby('duration_s').size()==8),'Unexpected campaign shape'
 assert df.measurement_valid.all() and df.failures.sum()==0,'Quality failure'
 df.to_csv(DATA/'runs.csv',index=False)
 table=summary_table(df);table.to_csv(DATA/'duration_summary.csv',index=False)
 if min(table.repetitions)>=8:stability_comparisons(df).to_csv(DATA/'stability_comparisons.csv',index=False)
 if min(table.repetitions)<8:
  print('Intermediate overview only; not enough data for the prespecified analysis.');return
 rel,aa=reliability(df);rel.to_csv(DATA/'conditional_detection.csv',index=False);aa.to_csv(DATA/'aa_comparisons.csv',index=False)
 power=timeline(df);power.to_csv(DATA/'power_timeline.csv',index=False)
 figures=plots(df,table,power,rel)
 summary=make_report(df,table,rel,aa,figures)
 print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
