#!/usr/bin/env python3
"""Descriptive follow-up on the existing 32 pilot runs; no new load tests."""
import os,pathlib,json
os.environ.setdefault('MPLCONFIGDIR','/tmp/energy-study-mpl-0')
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
ROOT=pathlib.Path(__file__).resolve().parent
SOURCE=ROOT.parents[1]/'results/runs.csv'
df=pd.read_csv(SOURCE)
assert len(df)==32 and all(df.groupby('duration_s').size()==8)
rows=[];allrows=[]
for duration,g in df.groupby('duration_s',sort=True):
 g=g.sort_values('block');e=g.node_package_j.to_numpy();a=g.app_attributed_package_j.to_numpy()
 mean=e.mean();sd=e.std(ddof=1);q1,q3=np.percentile(e,[25,75])
 loo=[np.std(np.delete(e,i),ddof=1)/np.mean(np.delete(e,i))*100 for i in range(8)]
 rows.append({'duration_s':duration,'n':len(e),'mean_j':mean,'median_j':np.median(e),'sd_j':sd,
  'q1_j':q1,'q3_j':q3,'iqr_j':q3-q1,'min_j':e.min(),'max_j':e.max(),'range_j':np.ptp(e),
  'range_pct_of_mean':100*np.ptp(e)/mean,'cv_pct':100*sd/mean,
  'app_cv_pct':100*np.std(a,ddof=1)/a.mean(),'five_percent_shift_j':.05*mean,
  'five_percent_shift_in_sd_units':.05*mean/sd,
  'one_percent_shift_in_sd_units':.01*mean/sd,
  'leave_one_out_cv_min_pct':min(loo),'leave_one_out_cv_max_pct':max(loo)})
 for _,r in g.iterrows():
  allrows.append({'block':int(r.block),'duration_s':int(duration),'node_package_j':r.node_package_j,
   'node_deviation_pct':100*(r.node_package_j/mean-1),
   'app_attributed_package_j':r.app_attributed_package_j,
   'app_deviation_pct':100*(r.app_attributed_package_j/a.mean()-1),
   'mean_node_power_w':r.mean_node_package_w,'j_per_request':r.node_j_per_request,
   'temporal_power_sd_w':r.temporal_power_sd_w})
stats=pd.DataFrame(rows);observations=pd.DataFrame(allrows)
stats.to_csv(ROOT/'distribution_summary.csv',index=False)
observations.to_csv(ROOT/'all_runs.csv',index=False)
pivot=observations.pivot(index='block',columns='duration_s',values='node_package_j')
pivot.columns=[f'{int(x)}s_energy_j' for x in pivot.columns]
pivot.to_csv(ROOT/'all_run_energies_by_block.csv')
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
durations=stats.duration_s.to_numpy();cmap=plt.get_cmap('viridis');norm=plt.Normalize(1,8)
fig,axes=plt.subplots(1,2,figsize=(12,5),layout='constrained',sharey=True)
for ax,col,title in zip(axes,['node_deviation_pct','app_deviation_pct'],['Node CPU package energy','Estimated application energy attribution']):
 data=[observations[observations.duration_s==d].sort_values('block')[col].to_numpy() for d in durations]
 ax.boxplot(data,positions=range(1,5),widths=.48,whis=(0,100),showfliers=False,
  medianprops={'color':'black','linewidth':1.5},boxprops={'color':'#555'},whiskerprops={'color':'#777'})
 for x,d in enumerate(durations,1):
  g=observations[observations.duration_s==d].sort_values('block')
  for jitter,(_,r) in zip(np.linspace(-.16,.16,8),g.iterrows()):
   ax.scatter(x+jitter,r[col],c=[cmap(norm(r.block))],s=48,zorder=3,edgecolor='white',linewidth=.6)
 ax.axhline(0,color='#aaa',linestyle='--',linewidth=1)
 ax.set(xticks=range(1,5),xticklabels=[f'{int(d)} s' for d in durations],xlabel='Run duration',title=title)
 ax.grid(axis='y',alpha=.15)
axes[0].set_ylabel('Deviation from the mean for that duration (%)')
fig.colorbar(plt.cm.ScalarMappable(norm=norm,cmap=cmap),ax=axes,ticks=range(1,9),label='Randomized block',shrink=.8)
fig.suptitle('All eight runs per duration — each dot is one run',fontsize=14)
fig.savefig(ROOT/'all_runs_distributions.png',dpi=180,bbox_inches='tight')
fig.savefig(ROOT/'all_runs_distributions.svg',bbox_inches='tight')
fig2,axes2=plt.subplots(2,2,figsize=(12,8),layout='constrained')
for ax,d in zip(axes2.flat,durations):
 g=observations[observations.duration_s==d].sort_values('block');s=stats[stats.duration_s==d].iloc[0]
 ax.axhspan(s.mean_j-s.sd_j,s.mean_j+s.sd_j,color='#d9e8f6',alpha=.7,label='Mean ± one run SD')
 ax.axhline(s.mean_j,color='#666',linestyle='--',linewidth=1,label='Mean')
 ax.plot(g.block,g.node_package_j,color='#8c9cad',linewidth=1,zorder=2)
 ax.scatter(g.block,g.node_package_j,c=g.block,cmap=cmap,norm=norm,s=55,zorder=3)
 ax.set(xticks=range(1,9),xlabel='Randomized block',ylabel='CPU package energy (J)',title=f'{int(d)} seconds — CV {s.cv_pct:.2f}%')
 ax.ticklabel_format(axis='y',style='plain',useOffset=False);ax.grid(axis='y',alpha=.15)
 for _,r in g.iterrows():ax.annotate(f'{r.node_package_j:.1f}',(r.block,r.node_package_j),xytext=(0,7),textcoords='offset points',ha='center',fontsize=8)
 ax.margins(y=.2)
axes2.flat[0].legend(fontsize=8)
fig2.suptitle('Absolute energy totals in block order — y-axis scales differ by duration',fontsize=14)
fig2.savefig(ROOT/'energy_by_block.png',dpi=180,bbox_inches='tight')
fig2.savefig(ROOT/'energy_by_block.svg',bbox_inches='tight')
with PdfPages(ROOT/'distribution_figures.pdf') as pdf:
 pdf.savefig(fig,bbox_inches='tight');pdf.savefig(fig2,bbox_inches='tight')
plt.close('all')
# A simple table preserves every observed value; no fitted density is implied.
md='| Block | 15 s (J) | 30 s (J) | 60 s (J) | 120 s (J) |\n|---|---:|---:|---:|---:|\n'
for i,r in pivot.iterrows():md+='| '+str(i)+' | '+' | '.join(f'{x:.1f}' for x in r)+' |\n'
summary='| Duration | Mean J | Median J | SD J | Min–max J | CV |\n|---|---:|---:|---:|---|---:|\n'
for _,s in stats.iterrows():summary+=f'| {int(s.duration_s)} s | {s.mean_j:.1f} | {s.median_j:.1f} | {s.sd_j:.2f} | {s.min_j:.1f}–{s.max_j:.1f} | {s.cv_pct:.2f}% |\n'
text='''# Distribution follow-up: existing pilot data

## What “define the regression size” means

A minimum duration is conditional on the smallest energy increase worth detecting. This pilot's observed across-run variation was low compared with the simulated +5% to +30% shifts. The modeled signal was large relative to the noise, so most planned simulation cases were easy. That is why they reached 100% conditional detection and did not distinguish durations. This does not establish 100% detection in new experiments or actual code regressions.

For 15-second runs, mean node energy was 631.4 J and run-to-run sample SD was 1.31 J. A +5% energy shift is about 31.6 J, or 24 single-run SDs. For 30-second runs, mean energy was 1268.3 J and SD 10.89 J; +5% is 63.4 J, about 5.8 SDs. These SD multiples describe scale; they are not detection probabilities. A +1% shift at 30 seconds is only 12.7 J, about 1.16 SDs, and would be a more challenging planning case.

## Distributions across repeated runs

'''+summary+'''
![All observations, normalized for comparison](all_runs_distributions.png)

Every dot is a measured run. Each distribution is centered on its own duration mean so that spread can be compared without longer durations' larger total energy dominating the scale. Boxes show quartiles; whiskers span the observed min/max, not an outlier rejection rule. Color shows randomized block. The two panels show different metrics from the same 32 runs, not 64 independent experiments. Pod energy is an attribution estimate.

- **15 seconds:** all eight node-energy totals lie in a 3.66 J band, only 0.58% of their mean. Removing any one observation changes CV to 0.17–0.22%; its tight spread is not created by a single central point. It still has only three raw energy samples inside each measurement window, so its apparent stability needs independent validation.
- **30 seconds:** the widest relative spread, 1252.8–1284.9 J, or 2.52% of the mean. Blocks 1 and 3 were high; block 6 was low. Removing any one run leaves CV around 0.73–0.92%. Its wider spread is not explained by one observation alone.
- **60 seconds:** 2515.4–2542.0 J, a 1.05% observed range relative to the mean; intermediate variability.
- **120 seconds:** 5023.6–5114.0 J, or 1.79% of the mean. Block 1 was the highest value. Omitting it would reduce CV from 0.55% to about 0.31%, demonstrating sensitivity to one run. It remains included: there is no independent reason to discard it.

“Noise” here means variability across separate run totals at the same duration. It is different from variation within a single run. The existing master CSV also records within-run power SD and native-interval energy variation. A trace can fluctuate within each run yet integrate to similar totals across repetitions.

## Every run total

'''+md+'''
![Run totals in block order](energy_by_block.png)

The first block was high at 30, 60 and 120 seconds, but was not consistently high at 15 seconds. This warrants examining time/order and background activity; it does not identify a cause or justify dropping early runs. Warm-up, temperature, background work, exporter timing and ordinary sampling variation remain possible explanations. The application-attribution metric also has a different CV ranking: 60 seconds is lowest (0.54%), versus 0.74% at 15 seconds.

## What the sample can and cannot show

There are eight observations per duration. That is enough to display the data, describe its range and assess sensitivity to individual points, but not to establish Gaussian shape, tail behavior, bimodality, a stable CV plateau, or a universal minimum duration. For that reason the plots show all points rather than fitted normal curves or smoothed violin densities. CV confidence intervals from the original analysis remain approximate.

The generator was co-located with the SUT, the application stayed warm, and the primary metric covers the CPU package rather than the whole server. These limitations carry over unchanged. This follow-up launches no new load and does not modify or exclude any observations.

Files: `distribution_summary.csv` contains quartiles, ranges, SD and leave-one-out sensitivity; `all_runs.csv` contains both metrics and centered deviations; `all_run_energies_by_block.csv` is the full 8×4 energy table; `distribution_figures.pdf` contains both figures.
'''
(ROOT/'DISTRIBUTIONS.md').write_text(text)
print(stats.round(4).to_string(index=False))
