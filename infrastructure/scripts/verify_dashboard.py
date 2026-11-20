#!/usr/bin/env python3
"""Verify the provisioned dashboard and all queries via authenticated Grafana."""
import base64,json,os,pathlib,subprocess,time,urllib.error,urllib.parse,urllib.request
ROOT=pathlib.Path(__file__).resolve().parents[1]
K=os.environ.get('KUBECTL','kubectl')
def k(*args):return subprocess.check_output([K,'--request-timeout=20s',*args],text=True)
def main():
 local=json.loads((ROOT/'monitoring/dashboard.json').read_text())
 # Validate all PromQL before checking Grafana provisioning; emulate a 15-minute selection.
 for panel in local['panels']:
  for t in panel['targets']:
   path='/api/v1/namespaces/monitoring/services/prometheus-kube-prometheus-prometheus:9090/proxy/api/v1/query?'+urllib.parse.urlencode({'query':t['expr'].replace('$__range','15m')})
   q=json.loads(k('get','--raw',path));assert q['status']=='success' and q['data']['result'],panel['title']
 pf=subprocess.Popen([K,'port-forward','-n','monitoring','svc/prometheus-grafana','13000:80','--address=127.0.0.1'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 try:
  secret=json.loads(k('get','secret','prometheus-grafana','-n','monitoring','-o','json'))['data']
  cred=base64.b64decode(secret['admin-user'])+b':'+base64.b64decode(secret['admin-password'])
  auth='Basic '+base64.b64encode(cred).decode()
  def get(path):
   req=urllib.request.Request('http://127.0.0.1:13000'+path,headers={'Authorization':auth})
   with urllib.request.urlopen(req,timeout=30) as r:return json.load(r)
  for _ in range(40):
   try:
    live=get('/api/dashboards/uid/boutique-energy')['dashboard']
    if len(live['panels'])==len(local['panels']):break
   except (OSError,urllib.error.URLError):pass
   time.sleep(1)
  else:raise RuntimeError('Dashboard provisioning did not converge')
  results=[]
  for p in local['panels']:
   remote=next(x for x in live['panels'] if x['id']==p['id'])
   assert remote['targets']==p['targets'] and remote['type']==p['type'],p['title']
   for t in remote['targets']:
    q=get('/api/datasources/proxy/uid/prometheus/api/v1/query?'+urllib.parse.urlencode({'query':t['expr'].replace('$__range','15m')}))
    assert q['status']=='success' and q['data']['result'],p['title']
    results.append({'title':p['title'],'refId':t['refId'],'series':len(q['data']['result'])})
  try:
   urllib.request.urlopen('http://127.0.0.1:13000/api/dashboards/uid/boutique-energy',timeout=10)
   raise RuntimeError('Anonymous dashboard access unexpectedly allowed')
  except urllib.error.HTTPError as e:assert e.code==401,e.code
  report={'verified_at_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'health':get('/api/health'),'dashboard_uid':live['uid'],'panel_count':len(live['panels']),'anonymous_dashboard_status':401,'queries_via_grafana':results}
  (ROOT/'evidence/grafana-verification.json').write_text(json.dumps(report,indent=2)+'\n')
  print('PASS:',len(live['panels']),'provisioned panels;',len(results),'live queries through authenticated Grafana; anonymous API denied.')
 finally:
  pf.terminate();pf.wait(timeout=10)
if __name__=='__main__':main()
