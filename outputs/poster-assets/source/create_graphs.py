#!/usr/bin/env python3
"""Poster-sized scientific figures from the measured pilot; no new experiments."""
import os,pathlib,json
os.environ.setdefault('MPLCONFIGDIR','/tmp/energy-study-mpl-0')
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import NullFormatter
ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=ROOT/'graphs';PRE=ROOT/'previews';DPI=600
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':22,'axes.labelsize':25,
 'axes.titlesize':29,'xtick.labelsize':21,'ytick.labelsize':21,'legend.fontsize':18,
 'axes.spines.top':False,'axes.spines.right':False,'axes.linewidth':1.2,
 'pdf.fonttype':42,'ps.fonttype':42,'svg.fonttype':'path','savefig.facecolor':'white'})
NAVY='#132A43';TEAL='#087F8C';ORANGE='#CF8025';GREY='#5F6E7C'
runs=pd.read_csv(ROOT/'data/runs.csv');summary=pd.read_csv(ROOT/'data/duration_summary.csv')
durations=[15,30,60,120];cmap=plt.get_cmap('viridis');norm=plt.Normalize(1,8)
manifest=[]
def save(fig,name,title,description):
 fig.canvas.draw()
 renderer=fig.canvas.get_renderer()
 bounds=fig.bbox
 for t in fig.texts:
  b=t.get_window_extent(renderer)
  assert b.x0>=0 and b.x1<=bounds.width and b.y0>=0 and b.y1<=bounds.height,(name,'Text outside page',t.get_text(),tuple(b.bounds))
 for ax in fig.axes:
  if ax.get_xlabel():
   xb=ax.xaxis.label.get_window_extent(renderer)
   for t in fig.texts:
    if t.get_position()[1]<.1:assert not xb.overlaps(t.get_window_extent(renderer)),(name,'Footer overlaps xlabel')
 fig.savefig(OUT/(name+'.pdf'))
 fig.savefig(OUT/(name+'.svg'))
 fig.savefig(OUT/(name+'.png'),dpi=DPI)
 fig.savefig(PRE/(name+'.png'),dpi=110)
 w,h=fig.get_size_inches()
 manifest.append({'name':name,'title':title,'description':description,'width_in':float(w),'height_in':float(h),
  'width_mm':float(w*25.4),'height_mm':float(h*25.4),'png_dpi':DPI,'png_pixels':[round(w*DPI),round(h*DPI)]})
 plt.close(fig)

def distribution(metric,name,title,estimate=False,clean=False):
 fig,ax=plt.subplots(figsize=(12,8.8))
 fig.subplots_adjust(left=.17 if clean else .16,right=.96 if clean else .84,bottom=.17 if clean else .28,top=.85 if clean else .80)
 groups=[]
 for d in durations:
  g=runs[runs.duration_s==d].sort_values('block');e=g[metric].to_numpy();groups.append(100*(e/e.mean()-1))
 ax.boxplot(groups,positions=range(1,5),widths=.52,whis=(0,100),showfliers=False,
  boxprops={'color':GREY,'linewidth':1.8},medianprops={'color':NAVY,'linewidth':2.5},
  whiskerprops={'color':GREY,'linewidth':1.5},capprops={'color':GREY,'linewidth':1.5})
 for x,d in enumerate(durations,1):
  g=runs[runs.duration_s==d].sort_values('block')
  colors={'color':TEAL} if clean else {'c':g.block,'cmap':cmap,'norm':norm}
  ax.scatter(x+np.linspace(-.17,.17,len(g)),groups[x-1],**colors,
             s=135,edgecolor='white',linewidth=1.1,zorder=3)
 ax.axhline(0,color='#9AA6B2',ls='--',lw=1.2,zorder=0);ax.grid(axis='y',alpha=.18)
 # groups already express percent deviation: their SD is CV in percentage points.
 cvs=[np.std(g,ddof=1) for g in groups]
 ax.set_xticks(range(1,5),[f'{d} s' for d in durations] if clean else [f'{d} s\nCV {v:.2f}%' for d,v in zip(durations,cvs)])
 ax.set_xlabel('Benchmark duration',labelpad=15)
 ax.set_ylabel('Deviation from mean energy (%)' if clean else 'Deviation from duration mean (%)',labelpad=14)
 fig.text(.08,.965,title,ha='left',va='top',fontsize=29,fontweight='bold',color=NAVY)
 if not clean:
  fig.text(.08,.895,'Eight baseline runs per duration · each dot is one run',fontsize=20,color=GREY)
  cax=fig.add_axes([.885,.27,.025,.48]);cb=fig.colorbar(plt.cm.ScalarMappable(norm=norm,cmap=cmap),cax=cax,ticks=range(1,9))
  cb.solids.set_rasterized(False)
  cb.ax.tick_params(labelsize=17);cb.set_label('Randomized block',fontsize=20,labelpad=14)
  footer='CPU-package attribution estimates; not independent hardware measurements.' if estimate else 'Hardware-reported CPU package; generator shared the measured host.'
  fig.text(.08,.075,'Box: quartiles · whiskers: observed range · no fitted distribution',fontsize=15,color=GREY)
  fig.text(.08,.035,footer,fontsize=15,color=GREY)
 save(fig,name,title,'All 32 measured runs centered on the mean at each duration; box quartiles and full min/max whiskers, not normality assumptions.')

distribution('app_attributed_package_j','01_application_energy_distribution','Application energy attribution',True,clean=True)
distribution('node_package_j','02_node_energy_distribution','CPU-package energy distribution')

fig,ax=plt.subplots(figsize=(12,8.8));fig.subplots_adjust(left=.16,right=.95,bottom=.21,top=.80)
x=np.arange(4);jitter=np.linspace(-.14,.14,8)
for k,d in enumerate(durations):
 g=runs[runs.duration_s==d].sort_values('block')
 ax.scatter(k+jitter,g.node_package_j/1000,c=g.block,cmap=cmap,norm=norm,s=115,
            edgecolor='white',linewidth=1,zorder=3)
ax.errorbar(x,summary.mean_energy_j/1000,yerr=summary.sd_energy_j/1000,
            fmt='D-',color=NAVY,lw=2,ms=9,capsize=7,label='Mean ± one run SD',zorder=4)
for k,s in summary.iterrows():ax.annotate(f'{s.mean_energy_j/1000:.2f} kJ',(k,s.mean_energy_j/1000),xytext=(0,22),textcoords='offset points',ha='center',fontsize=21,color=NAVY)
ax.set(xticks=x,xticklabels=[f'{d} s' for d in durations],ylim=(0,5.9),xlabel='Benchmark duration',ylabel='CPU-package energy per run (kJ)')
ax.grid(axis='y',alpha=.18);ax.legend(loc='upper left')
fig.text(.08,.965,'Longer windows increase measured energy',ha='left',va='top',fontsize=29,fontweight='bold',color=NAVY)
fig.text(.08,.895,'Same three-user workload · eight baseline runs per duration',fontsize=20,color=GREY)
fig.text(.08,.085,'120 s consumed 8.01× the measured package energy of 15 s.',fontsize=19,color=NAVY)
fig.text(.08,.035,'Longer windows also complete more work; generator overhead is included.',fontsize=15,color=GREY)
save(fig,'03_energy_cost','Longer windows increase measured energy','Mean energy with sample SD and all eight observed totals at each duration. Total work is not held constant.')

fig,ax=plt.subplots(figsize=(12,8.8));fig.subplots_adjust(left=.16,right=.95,bottom=.20,top=.80)
for col,lo,hi,label,color,marker,shift in [
 ('cv_energy_pct','cv_ci_low_pct','cv_ci_high_pct','Node CPU package',NAVY,'o',-.035),
 ('cv_app_attributed_energy_pct','cv_app_ci_low_pct','cv_app_ci_high_pct','Application attribution estimate',TEAL,'s',.035)]:
 y=summary[col].to_numpy();low=summary[lo].to_numpy();high=summary[hi].to_numpy()
 ax.errorbar(x+shift,y,yerr=np.vstack([y-low,high-y]),fmt=marker+'-',color=color,lw=2,
             markersize=10,capsize=7,label=label)
ax.set(xticks=x,xticklabels=[f'{d} s' for d in durations],xlabel='Benchmark duration',ylabel='Across-run energy CV (%)',ylim=(0,1.65))
ax.grid(axis='y',alpha=.18);ax.legend(loc='upper right',fontsize=18)
fig.text(.08,.965,'Longer was not consistently more stable',ha='left',va='top',fontsize=29,fontweight='bold',color=NAVY)
fig.text(.08,.895,'Pilot result · eight baseline repetitions per duration',fontsize=20,color=GREY)
fig.text(.08,.075,'Bars: approximate bootstrap 95% intervals; small-sample uncertainty remains.',fontsize=15,color=GREY)
fig.text(.08,.035,'Single session · five-second energy sampling · no actual regression variant.',fontsize=15,color=GREY)
save(fig,'04_stability_vs_duration','Longer was not consistently more stable','CV and approximate bootstrap 95% confidence intervals for both energy metrics; not a regression-detection validation.')
(ROOT/'graph_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('Generated',len(manifest),'poster graphs at 600 dpi, plus vector PDFs/SVGs.')
