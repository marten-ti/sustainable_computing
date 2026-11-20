"""Deterministic per-user shopping journeys; no artificial think time.

A fixed user population is a closed-loop workload, not a fixed request rate.
The warm-up starts after every user has spawned and is excluded from results.
"""
import csv
import json
import random
import time
from pathlib import Path

import gevent
from locust import FastHttpUser, constant, events, task
from locust.stats import stats_printer

PRODUCTS = ('0PUK6V6EV0','1YMWWN1N4O','2ZYFJ3GM2N','66VCHSJNUP',
            '6E92ZMYYFZ','9SIQT8TOJO','L9ECAV7KIM','LS4PSXUNUM','OLJCESPC7Z')
STATE = {'started':False, 'measuring':False, 'next_user':0, 'bins':{},
         'started_users':0, 'journeys':0, 'first_errors':[], 'request_rows':[]}

@events.init_command_line_parser.add_listener
def arguments(parser):
    parser.add_argument('--measurement-duration',type=float,default=30)
    parser.add_argument('--warmup-seconds',type=float,default=15)
    parser.add_argument('--workload-seed',type=int,default=20261119)
    parser.add_argument('--run-directory',type=str,default='results/manual')

class Shopper(FastHttpUser):
    wait_time = constant(0)
    connection_timeout = 10
    network_timeout = 10

    def on_start(self):
        self.user_id = STATE['next_user']; STATE['next_user'] += 1
        self.rng = random.Random(self.environment.parsed_options.workload_seed+self.user_id)
        STATE['started_users'] += 1

    def checked(self,method,path,name,needle=None,**kwargs):
        with self.client.request(method,path,name=name,catch_response=True,**kwargs) as response:
            if response.status_code != 200:
                response.failure(f'HTTP {response.status_code}')
                return False
            if needle and needle not in response.text:
                response.failure(f'Missing response marker: {needle}')
                return False
        return True

    @task
    def shopping_journey(self):
        product = self.rng.choice(PRODUCTS)
        if not self.checked('GET','/','home',needle='Online Boutique'):return
        if not self.checked('GET','/product/'+product,'product',needle='Add To Cart'):return
        if not self.checked('POST','/cart','add_to_cart',data={'product_id':product,'quantity':1}):return
        if not self.checked('GET','/cart','cart',needle='cart-checkout-form'):return
        if self.checked('POST','/cart/checkout','checkout',needle='Your order is complete',data={
            'email':f'benchmark-{self.user_id}@example.com','street_address':'1 Benchmark Street',
            'zip_code':'10115','city':'Berlin','state':'Berlin','country':'Germany',
            'credit_card_number':'4111111111111111','credit_card_expiration_month':'12',
            'credit_card_expiration_year':'2030','credit_card_cvv':'123'}):
            if STATE['measuring']: STATE['journeys'] += 1

@events.request.add_listener
def request_done(request_type,name,response_time,response_length,exception,**kwargs):
    now = time.time()
    if not STATE['measuring'] or not (STATE['start_epoch'] <= now < STATE['end_epoch_target']):return
    second = int(now-STATE['start_epoch'])
    b=STATE['bins'].setdefault(second,{'requests':0,'failures':0,'latency_sum_ms':0.0,'latencies':[]})
    b['requests']+=1;b['failures']+=int(exception is not None)
    STATE['request_rows'].append((now,name,response_time,int(exception is not None)))
    b['latency_sum_ms']+=response_time;b['latencies'].append(response_time)
    if exception and len(STATE['first_errors'])<10:STATE['first_errors'].append(str(exception))

@events.spawning_complete.add_listener
def ready(user_count,**kwargs):
    if STATE['started']:return
    STATE['started']=True
    env=STATE['environment']
    def control():
        opts=env.parsed_options
        STATE['warmup_start_epoch']=time.time()
        gevent.sleep(opts.warmup_seconds)
        env.stats.reset_all()
        STATE['start_epoch']=time.time()
        STATE['end_epoch_target']=STATE['start_epoch']+opts.measurement_duration
        STATE['start_monotonic']=time.monotonic()
        STATE['measuring']=True
        gevent.sleep(opts.measurement_duration)
        STATE['end_epoch']=time.time()
        STATE['end_monotonic']=time.monotonic()
        STATE['measuring']=False
        # Keep load constant beyond the cutoff so bracketing energy samples do
        # not mix a load-to-idle step into a short measurement window.
        gevent.sleep(11)
        STATE['guard_end_epoch']=time.time()
        env.runner.quit()
    gevent.spawn(control)

@events.init.add_listener
def setup(environment,**kwargs):
    STATE['environment']=environment
    Path(environment.parsed_options.run_directory).mkdir(parents=True,exist_ok=True)

@events.quitting.add_listener
def finish(environment,**kwargs):
    opts=environment.parsed_options; out=Path(opts.run_directory)
    if 'end_epoch' not in STATE:
        (out/'run_error.json').write_text(json.dumps({'error':'Measurement window did not complete','state':{k:v for k,v in STATE.items() if k!='environment'}},default=str,indent=2))
        environment.process_exit_code=2;return
    requests=sum(b['requests'] for b in STATE['bins'].values())
    failures=sum(b['failures'] for b in STATE['bins'].values())
    latencies=sorted(x for b in STATE['bins'].values() for x in b['latencies'])
    p95=latencies[max(0,__import__('math').ceil(.95*len(latencies))-1)] if latencies else None
    total=environment.stats.total
    result={'users':opts.num_users,'seed':opts.workload_seed,'warmup_seconds':opts.warmup_seconds,
            'requested_duration_s':opts.measurement_duration,'start_epoch':STATE['start_epoch'],
            'end_epoch':STATE['end_epoch'],'end_epoch_target':STATE['end_epoch_target'],
            'warmup_start_epoch':STATE['warmup_start_epoch'],
            'actual_duration_s':STATE['end_monotonic']-STATE['start_monotonic'],
            'requests':requests,'failures':failures,'failure_rate':failures/requests if requests else 1,
            'rps':requests/opts.measurement_duration,'p95_latency_ms':p95,
            'mean_latency_ms':sum(latencies)/len(latencies) if latencies else None,
            'completed_journeys':STATE['journeys'],'first_errors':STATE['first_errors'],
            'locust_requests':total.num_requests,'locust_failures':total.num_failures,
            'post_cutoff_loaded_guard_s':11,'guard_end_epoch':STATE['guard_end_epoch'],
            'raw_locust_stats_include_guard':True,
            'window_semantics':'requests completed inside [start,end_target); energy uses exactly the same target boundaries',
            'think_time_s':0,'workload':'home/product/add/cart/checkout, sequential per-user journeys'}
    (out/'run.json').write_text(json.dumps(result,indent=2)+'\n')
    with (out/'requests.csv').open('w',newline='') as f:
        writer=csv.writer(f);writer.writerow(['completed_epoch','operation','response_time_ms','failed']);writer.writerows(STATE['request_rows'])
    # Authoritative measured-window statistics; avoids Locust's asynchronous
    # CSV writer shutdown race and excludes loaded-guard requests.
    with (out/'measured_stats.csv').open('w',newline='') as f:
        writer=csv.writer(f)
        writer.writerow(['operation','requests','failures','mean_latency_ms','p50_latency_ms','p95_latency_ms','rps'])
        for operation in sorted(set(row[1] for row in STATE['request_rows']))+['Aggregated']:
            rows=[row for row in STATE['request_rows'] if operation=='Aggregated' or row[1]==operation]
            vals=sorted(row[2] for row in rows)
            n=len(rows)
            writer.writerow([operation,n,sum(row[3] for row in rows),sum(vals)/n,
                             vals[__import__('math').ceil(.5*n)-1],vals[__import__('math').ceil(.95*n)-1],
                             n/opts.measurement_duration])
    with (out/'requests_per_second.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['second','epoch','requests','failures','mean_latency_ms','p95_latency_ms'])
        writer.writeheader()
        for second,b in sorted(STATE['bins'].items()):
            vals=sorted(b['latencies']);i=__import__('math').ceil(.95*len(vals))-1
            writer.writerow({'second':second,'epoch':STATE['start_epoch']+second,'requests':b['requests'],
                             'failures':b['failures'],'mean_latency_ms':b['latency_sum_ms']/b['requests'],
                             'p95_latency_ms':vals[i]})
    environment.process_exit_code=0 if requests and failures==0 else 1
