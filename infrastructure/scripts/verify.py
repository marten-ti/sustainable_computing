#!/usr/bin/env python3
"""Read-only rollout/metric checks, plus one synthetic shopping transaction."""
import base64, http.cookiejar, json, os, pathlib, subprocess, time, urllib.parse, urllib.request
K=os.environ.get('KUBECTL','kubectl')
ROOT=pathlib.Path(__file__).resolve().parents[1]
def k(*args): return subprocess.check_output([K,'--request-timeout=20s',*args],text=True)
def query(expr):
 x=json.loads(k('get','--raw','/api/v1/namespaces/monitoring/services/prometheus-kube-prometheus-prometheus:9090/proxy/api/v1/query?'+urllib.parse.urlencode({'query':expr})))
 assert x['status']=='success',x
 return x['data']['result']
def main():
 pods=json.loads(k('get','pods','-n','online-boutique','-o','json'))['items']
 assert len(pods)==11,len(pods)
 for p in pods:
  assert 'loadgenerator' not in p['metadata']['name']
  assert any(c['type']=='Ready' and c['status']=='True' for c in p['status'].get('conditions',[])),p['metadata']['name']
 dashboard=json.loads((ROOT/'monitoring/dashboard.json').read_text())
 results=[]
 for panel in dashboard['panels']:
  for target in panel['targets']:
   data=query(target['expr'].replace('$__range','15m'))
   assert data,panel['title']
   results.append({'panel':panel['title'],'refId':target['refId'],'series':len(data),'samples':data})
 pf=subprocess.Popen([K,'port-forward','-n','online-boutique','svc/frontend','18080:80','--address=127.0.0.1'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 try:
  opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
  for _ in range(30):
   try:
    r=opener.open('http://127.0.0.1:18080/',timeout=5); assert r.status==200; break
   except Exception: time.sleep(1)
  else: raise RuntimeError('Frontend tunnel unavailable')
  def visit(path,form=None):
   data=None if form is None else urllib.parse.urlencode(form).encode()
   with opener.open('http://127.0.0.1:18080'+path,data=data,timeout=30) as r:
    assert r.status==200
    return r.read().decode()
  assert 'Sunglasses' in visit('/product/OLJCESPC7Z')
  visit('/cart',{'product_id':'OLJCESPC7Z','quantity':1})
  assert 'Sunglasses' in visit('/cart')
  visit('/setCurrency',{'currency_code':'EUR'})
  body=visit('/cart/checkout',{'email':'verification@example.com','street_address':'123 Test Street','zip_code':'10115','city':'Berlin','state':'Berlin','country':'Germany','credit_card_number':'4111111111111111','credit_card_expiration_month':'12','credit_card_expiration_year':str(time.gmtime().tm_year+2),'credit_card_cvv':'123'})
  assert 'Your order is complete' in body,body[:200]
 finally:
  pf.terminate(); pf.wait(timeout=10)
 report={'verified_at_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'ready_pods':11,'shopping':['browse','add_to_cart','cart','currency_change','mock_checkout'],'dashboard_queries':results}
 (ROOT/'evidence/verification.json').write_text(json.dumps(report,indent=2)+'\n')
 print('PASS: 11 ready pods; browsing, cart, currency, checkout; all dashboard queries return live data.')
if __name__=='__main__': main()
