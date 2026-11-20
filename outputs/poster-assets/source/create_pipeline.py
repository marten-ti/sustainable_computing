#!/usr/bin/env python3
"""Vector BPMN artwork and matching, editable BPMN 2.0 XML with layout."""
import os,pathlib,json,xml.etree.ElementTree as ET
os.environ.setdefault('MPLCONFIGDIR','/tmp/energy-study-mpl-0')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch,Circle,Polygon,Ellipse,FancyArrowPatch
from matplotlib.path import Path
ROOT=pathlib.Path(__file__).resolve().parents[1];OUT=ROOT/'pipeline';PRE=ROOT/'previews'
plt.rcParams.update({'font.family':'DejaVu Sans','pdf.fonttype':42,'svg.fonttype':'path'})
NAVY='#132A43';TEAL='#0B756D';GREY='#66788A';RED='#A64141'
fig=plt.figure(figsize=(24,10));ax=fig.add_axes([.025,.07,.95,.86]);ax.set(xlim=(0,64),ylim=(0,26));ax.set_aspect('equal');ax.axis('off')
nodes={};edges=[];texts=[]
def register(id,kind,label,bounds,parent='main',**kw):
 nodes[id]={'id':id,'kind':kind,'label':label,'bounds':bounds,'parent':parent,**kw};return nodes[id]
def task(id,label,x,y,w,h,parent='main',color=NAVY,fill='#F1F5F9'):
 n=register(id,'task',label,(x,y,w,h),parent)
 ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0,rounding_size=.35',lw=1.5,ec=color,fc=fill,zorder=2))
 t=ax.text(x+w/2,y+h/2,label,fontsize=18.5,color=NAVY,ha='center',va='center',linespacing=1.18,zorder=4);texts.append((t,n))
 return n
def event(id,kind,x,y,r,label='',parent='main',color=NAVY):
 n=register(id,kind,label,(x-r,y-r,2*r,2*r),parent)
 ax.add_patch(Circle((x,y),r,ec=color,fc='white',lw=3 if kind=='endEvent' else 1.5,zorder=4))
 if label:ax.text(x,y-r-.36,label,ha='center',va='top',fontsize=16,color=color,zorder=5)
 return n
def gateway(id,x,y,parent='trial'):
 n=register(id,'parallelGateway','',(x-.8,y-.8,1.6,1.6),parent)
 ax.add_patch(Polygon([(x-.8,y),(x,y+.8),(x+.8,y),(x,y-.8)],ec=NAVY,fc='white',lw=1.5,zorder=3))
 ax.plot([x-.34,x+.34],[y,y],color=NAVY,lw=2.3,zorder=4);ax.plot([x,x],[y-.34,y+.34],color=NAVY,lw=2.3,zorder=4)
 return n
def data_object(id,label,x,y,w=1.3,h=1.7,labelpos=None):
 n=register(id,'dataObjectReference',label,(x,y,w,h))
 fold=.4
 ax.add_patch(Polygon([(x,y),(x+w,y),(x+w,y+h-fold),(x+w-fold,y+h),(x,y+h)],closed=True,fc='white',ec=GREY,lw=1.3,zorder=3))
 ax.plot([x+w-fold,x+w-fold,x+w],[y+h,y+h-fold,y+h-fold],color=GREY,lw=1.1,zorder=4)
 if labelpos:
  ax.text(*labelpos,label,fontsize=16,ha='left',va='center',color=GREY,zorder=5);n['labelpos']=labelpos
 return n
def store(id,label,x,y,w,h,labelpos):
 n=register(id,'dataStoreReference',label,(x,y,w,h));n['labelpos']=labelpos
 ax.add_patch(FancyBboxPatch((x,y+.2),w,h-.4,boxstyle='square,pad=0',ec='none',fc='white',zorder=2))
 ax.plot([x,x],[y+.25,y+h-.25],color=GREY,lw=1.3,zorder=3);ax.plot([x+w,x+w],[y+.25,y+h-.25],color=GREY,lw=1.3,zorder=3)
 ax.add_patch(Ellipse((x+w/2,y+.25),w,.5,ec=GREY,fc='white',lw=1.3,zorder=3))
 ax.add_patch(Ellipse((x+w/2,y+h-.25),w,.5,ec=GREY,fc='white',lw=1.3,zorder=4))
 ax.text(*labelpos,label,fontsize=16,ha='left',va='center',color=GREY,zorder=5)
 return n
def flow(id,source,target,points,parent='main',association=False,color=NAVY):
 edges.append({'id':id,'source':source,'target':target,'points':points,'parent':parent,'association':association})
 path=Path(points,[Path.MOVETO]+[Path.LINETO]*(len(points)-1))
 ax.add_patch(FancyArrowPatch(path=path,arrowstyle='->' if association else '-|>',mutation_scale=18,
  lw=1.1 if association else 1.5,linestyle=(0,(1,3)) if association else '-',color=GREY if association else color,
  fill=not association,zorder=1.5))

# Top-level control flow: user dispatch, configuration and reproducible builds.
event('start','startEvent',1.5,21.5,.58,'Manual\ntrigger')
task('configure','Configure experiment\nrecord environment\n+ pipeline start time',4,20,9,3)
task('build','Build revision(s)\nand publish pinned\ncontainer images',16,20,10,3)
data_object('configRef','Durations · repetitions\nusers · seed · variants',7.8,17.1,1.3,1.6,(9.7,17.9))
data_object('sourceRef','Source revision(s)',30.6,20.5,1.3,1.7,(32.5,21.35))
store('registryRef','Versioned local\nimage registry',43,20,3,2,(47,21))
flow('f_start_config','start','configure',[(2.08,21.5),(4,21.5)])
flow('f_config_build','configure','build',[(13,21.5),(16,21.5)])
flow('a_config','configRef','configure',[(8.45,18.7),(8.45,20)],association=True)
flow('a_source','sourceRef','build',[(30.6,21.35),(26,21.35)],association=True)
flow('a_registry','build','registryRef',[(21,23),(21,24.25),(44.5,24.25),(44.5,22)],association=True)

# Expanded sequential multi-instance subprocess: one trial at a time.
register('trial','subProcess','Execute randomized trial plan',(2.5,5.6,56,11))
ax.add_patch(FancyBboxPatch((2.5,5.6),56,11,boxstyle='round,pad=0,rounding_size=.45',lw=1.8,ec='#91A2B3',fc='white',zorder=0))
ax.text(30.5,16.0,'Sequential trial plan: variant × duration × repetition',fontsize=20,fontweight='bold',color=NAVY,ha='center',va='center',zorder=4)
for y in [5.82,6.0,6.18]:ax.plot([30.07,30.93],[y,y],color=NAVY,lw=1.8,zorder=4)
flow('f_build_trial','build','trial',[(21,20),(21,18.85),(30.5,18.85),(30.5,16.6)])
event('trialStart','startEvent',4.2,10.7,.43,parent='trial')
task('deploy','Deploy pinned\nvariant; readiness\n+ smoke checks',6,9.05,7.3,3.3,'trial')
task('preQuiet','Quiet reference\nbefore trial',15,9.05,6.5,3.3,'trial',TEAL,'#ECF6F3')
gateway('fork',23.4,10.7)
task('load','Run seeded Locust\nwarm-up → measure\n→ guard (external)',26,12.2,9,3,'trial','#B57618','#FFF5E4')
task('telemetry','Capture telemetry\nKepler → Prometheus\n+ request timings',26,6.3,9,3,'trial',TEAL,'#ECF6F3')
gateway('join',37.3,10.7)
task('postQuiet','Quiet reference\nafter trial',39.4,9.05,6.5,3.3,'trial',TEAL,'#ECF6F3')
task('validate','Align cutoffs;\nvalidate metrics\nand request results',47.7,9.05,7.2,3.3,'trial')
event('trialEnd','endEvent',56.7,10.7,.45,parent='trial')
for id,s,t,p in [
 ('i_start','trialStart','deploy',[(4.63,10.7),(6,10.7)]),
 ('i_deploy_pre','deploy','preQuiet',[(13.3,10.7),(15,10.7)]),
 ('i_pre_fork','preQuiet','fork',[(21.5,10.7),(22.6,10.7)]),
 ('i_fork_load','fork','load',[(23.4,11.5),(23.4,13.7),(26,13.7)]),
 ('i_fork_monitor','fork','telemetry',[(23.4,9.9),(23.4,7.8),(26,7.8)]),
 ('i_load_join','load','join',[(35,13.7),(37.3,13.7),(37.3,11.5)]),
 ('i_monitor_join','telemetry','join',[(35,7.8),(37.3,7.8),(37.3,9.9)]),
 ('i_join_post','join','postQuiet',[(38.1,10.7),(39.4,10.7)]),
 ('i_post_valid','postQuiet','validate',[(45.9,10.7),(47.7,10.7)]),
 ('i_valid_end','validate','trialEnd',[(54.9,10.7),(56.25,10.7)])]:flow(id,s,t,p,'trial')

# Interrupting boundary error: failed readiness/smoke/metric quality invalidates a job.
register('qualityError','boundaryEvent','Quality gate failed',(5.05,5.15,.9,.9),attachedTo='trial')
ax.add_patch(Circle((5.5,5.6),.45,ec=RED,fc='white',lw=1.5,zorder=5))
ax.add_patch(Circle((5.5,5.6),.35,ec=RED,fc='white',lw=1.0,zorder=6))
ax.add_patch(Polygon([(5.48,5.88),(5.33,5.57),(5.49,5.61),(5.42,5.33),(5.69,5.72),(5.53,5.67)],ec=RED,fc='white',lw=1.1,zorder=7))
ax.text(6.3,4.94,'Quality gate failed',fontsize=15,color=RED,ha='left')
task('failure','Save diagnostics\nand fail the job',8,1.45,12,3.2,color=RED,fill='#FFF1F1')
event('failedEnd','endEvent',22,3.05,.55,'Job failed',color=RED)
flow('f_quality_failure','qualityError','failure',[(5.5,5.15),(5.5,3.05),(8,3.05)],color=RED)
flow('f_failure_end','failure','failedEnd',[(20,3.05),(21.45,3.05)],color=RED)

# Raw data artifact links mirror the supplied reference's data-object association.
data_object('metricsRef','Raw energy +\nrequest metrics',24.4,2.2,1.4,1.8,(26.5,3.1))
flow('a_metrics','telemetry','metricsRef',[(28.2,6.3),(28.2,5.1),(25.1,5.1),(25.1,4.0)],association=True)
task('analyze','Compare A/A + A/B\nCV · detection rate\n· false alarms',35.2,1.45,10.4,3.2)
task('publish','Publish CSV + figures\npipeline timings\nand job status',47.2,1.45,10.4,3.2)
event('finished','endEvent',60.2,3.05,.55,'Finished')
flow('f_trial_analyze','trial','analyze',[(40.4,5.6),(40.4,4.65)])
flow('f_analyze_publish','analyze','publish',[(45.6,3.05),(47.2,3.05)])
flow('f_publish_end','publish','finished',[(57.6,3.05),(59.65,3.05)])
flow('a_metrics_analyze','metricsRef','analyze',[(25.8,3.6),(26.2,3.6),(26.2,4.8),(34,4.8),(34,4.0),(35.2,4.0)],association=True)

fig.suptitle('Planned energy-regression experiment pipeline',fontsize=31,fontweight='bold',color=NAVY,y=.982)
fig.text(.04,.045,'Proposed design · quiet-reference policy is configurable · warm-up and guard are excluded from measured windows.',fontsize=15,color=GREY)
fig.text(.04,.012,'Solid arrows: control flow     Dotted arrows: data associations     +: parallel split / join     Three horizontal bars: sequential repetition',fontsize=15,color=GREY)
# Check task label extents against actual rendered boxes before exporting.
fig.canvas.draw();renderer=fig.canvas.get_renderer();label_checks=[]
for t,n in texts:
 x,y,w,h=n['bounds'];b=ax.transData.transform([[x,y],[x+w,y+h]]);available=b[1]-b[0]
 for _ in range(5):
  size=t.get_window_extent(renderer);ratio=min(.91*available[0]/size.width,.83*available[1]/size.height,1)
  if ratio>=.995:break
  t.set_fontsize(t.get_fontsize()*ratio);fig.canvas.draw();renderer=fig.canvas.get_renderer()
 label_checks.append({'id':n['id'],'font_pt':t.get_fontsize()})
 assert t.get_fontsize()>=15.5,('Label too small',n['id'],t.get_fontsize())
fig.savefig(OUT/'planned_pipeline.pdf')
fig.savefig(OUT/'planned_pipeline.svg')
fig.savefig(OUT/'planned_pipeline.png',dpi=600)
fig.savefig(PRE/'planned_pipeline.png',dpi=100)
plt.close(fig)

# Matching BPMN 2.0 XML and BPMN-DI. This is descriptive, not engine-executable.
NS={'bpmn':'http://www.omg.org/spec/BPMN/20100524/MODEL','bpmndi':'http://www.omg.org/spec/BPMN/20100524/DI',
 'dc':'http://www.omg.org/spec/DD/20100524/DC','di':'http://www.omg.org/spec/DD/20100524/DI','xsi':'http://www.w3.org/2001/XMLSchema-instance'}
for p,u in NS.items():ET.register_namespace(p,u)
def tag(p,n):return '{'+NS[p]+'}'+n
def el(parent,name,attrs=None,text=None,prefix='bpmn'):
 x=ET.SubElement(parent,tag(prefix,name),attrs or {})
 if text is not None:x.text=text
 return x
root=ET.Element(tag('bpmn','definitions'),{'id':'Definitions_EnergyPilot','targetNamespace':'https://example.org/energy-regression-pipeline','exporter':'Poster assets generator','exporterVersion':'1.0'})
el(root,'error',{'id':'InvalidTrialError','name':'Invalid trial','errorCode':'INVALID_TRIAL'})
el(root,'dataStore',{'id':'RegistryStore','name':'Versioned image registry'})
process=el(root,'process',{'id':'EnergyRegressionPipeline','name':'Planned energy-regression experiment pipeline','isExecutable':'false'})
el(process,'documentation',text='Proposed workflow, not an implemented CI/CD pipeline. User configures variants, durations, repetitions, users and seed. Trial instances run sequentially in randomized block order. Quiet references before/after each trial are a conservative proposed policy; duration and cadence must be decided before execution. Readiness, smoke or data validation failures signal INVALID_TRIAL and interrupt the subprocess. Analysis publishes pass/fail/inconclusive status; actual detection must be validated on independent A/A and A/B experiments.')
subprocess_node=el(process,'subProcess',{'id':'trial','name':'Execute randomized trial plan'})
loop=el(subprocess_node,'multiInstanceLoopCharacteristics',{'isSequential':'true'})
el(loop,'loopCardinality',{tag('xsi','type'):'bpmn:tFormalExpression'},'number_of_planned_trials')
parents={'main':process,'trial':subprocess_node}
for id,n in nodes.items():
 if id=='trial':continue
 parent=parents[n['parent']];kind=n['kind'];attrs={'id':id}
 if n['label']:attrs['name']=n['label'].replace('\n',' ')
 if kind=='dataObjectReference':
  data_id=id+'_Data';el(parent,'dataObject',{'id':data_id,'name':attrs.get('name','')});attrs['dataObjectRef']=data_id
 if kind=='dataStoreReference':attrs['dataStoreRef']='RegistryStore'
 if kind=='boundaryEvent':attrs.update({'attachedToRef':'trial','cancelActivity':'true'})
 node=el(parent,kind,attrs)
 if id in ['deploy','validate']:
  el(node,'documentation',text='Signals the INVALID_TRIAL BPMN error if readiness, smoke, sample continuity, cutoff alignment or request quality checks fail.')
 if kind=='boundaryEvent':el(node,'errorEventDefinition',{'id':'CatchInvalidTrial','errorRef':'InvalidTrialError'})
for e in sorted(edges,key=lambda item:item['association']):
 attrs={'id':e['id'],'sourceRef':e['source'],'targetRef':e['target']}
 if e['association']:attrs['associationDirection']='One'
 el(parents[e['parent']],'association' if e['association'] else 'sequenceFlow',attrs)
# Add incoming/outgoing references (optional in XSD but helpful for modelers).
node_elements={x.attrib['id']:x for x in process.iter() if 'id' in x.attrib}
for e in edges:
 if e['association']:continue
 for id,name in [(e['source'],'outgoing'),(e['target'],'incoming')]:
  x=node_elements[id];index=0
  while index<len(x) and x[index].tag in [tag('bpmn','documentation'),tag('bpmn','incoming'),tag('bpmn','outgoing')]:index+=1
  child=ET.Element(tag('bpmn',name));child.text=e['id'];x.insert(index,child)
diagram=el(root,'BPMNDiagram',{'id':'Diagram_EnergyPipeline'},prefix='bpmndi')
plane=el(diagram,'BPMNPlane',{'id':'Plane_EnergyPipeline','bpmnElement':'EnergyRegressionPipeline'},prefix='bpmndi')
S=30;BASE=26
for id,n in nodes.items():
 x,y,w,h=n['bounds'];attrs={'id':'Shape_'+id,'bpmnElement':id}
 if id=='trial':attrs['isExpanded']='true'
 shape=el(plane,'BPMNShape',attrs,prefix='bpmndi')
 el(shape,'Bounds',{'x':str(50+x*S),'y':str(40+(BASE-y-h)*S),'width':str(w*S),'height':str(h*S)},prefix='dc')
 if n.get('labelpos') or (n['label'] and n['kind'] in ['startEvent','endEvent','boundaryEvent']):
  label=el(shape,'BPMNLabel',prefix='bpmndi')
  if n.get('labelpos'):lx,ly=n['labelpos'];bounds={'x':str(50+lx*S),'y':str(40+(BASE-ly)*S-25),'width':'260','height':'60'}
  else:bounds={'x':str(50+(x+w/2)*S-65),'y':str(40+(BASE-y)*S+8),'width':'130','height':'55'}
  el(label,'Bounds',bounds,prefix='dc')
for e in edges:
 edge=el(plane,'BPMNEdge',{'id':'Edge_'+e['id'],'bpmnElement':e['id']},prefix='bpmndi')
 for x,y in e['points']:el(edge,'waypoint',{'x':str(50+x*S),'y':str(40+(BASE-y)*S)},prefix='di')
ET.indent(root,space='  ')
ET.ElementTree(root).write(OUT/'planned_pipeline.bpmn',encoding='utf-8',xml_declaration=True)
(ROOT/'pipeline_manifest.json').write_text(json.dumps({'png_pixels':[14400,6000],'png_dpi':600,'width_mm':609.6,'height_mm':254.0,'bpmn_nodes':len(nodes),'sequence_flows':sum(not e['association'] for e in edges),'data_associations':sum(e['association'] for e in edges),'task_label_checks':label_checks,'is_executable':False},indent=2)+'\n')
print('Generated planned pipeline: vector PDF/SVG, 600-dpi PNG and editable BPMN 2.0 XML.')
