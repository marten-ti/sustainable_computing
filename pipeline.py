#!/usr/bin/env python3
"""Manual local research entry point. Does not deploy an app or create CI/CD."""
import argparse,pathlib,shutil,sys
ROOT=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'research'))

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--mode',choices=['smoke','campaign','single','analyze'],default='smoke')
 p.add_argument('--variant',default='baseline',help='Only the unchanged baseline is supported by this pilot')
 p.add_argument('--workload',action='store_true',help='Compatibility flag; workload is always enabled in workload modes')
 p.add_argument('--duration',type=int,default=60)
 p.add_argument('--warmup',type=int,default=15)
 p.add_argument('--users',type=int,default=3)
 p.add_argument('--repetitions',type=int,default=8)
 p.add_argument('--durations',type=int,nargs='+',default=[15,30,60,120])
 p.add_argument('--host',default='http://10.152.183.142')
 p.add_argument('--prometheus',default='http://10.152.183.218:9090')
 p.add_argument('--seed',type=int,default=20261119)
 p.add_argument('--locust',default=shutil.which('locust') or str(pathlib.Path(sys.executable).parent/'locust'))
 args=p.parse_args()
 if args.variant!='baseline':p.error('This pilot does not deploy or implement regression variants.')
 if args.mode=='analyze':
  import analyze
  sys.argv=[sys.argv[0]];analyze.main();return
 import experiment
 if args.mode=='single':
  import datetime
  rid='manual-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
  experiment.one_run(args,rid,'manual',args.duration,args.users);return
 forwarded=['--mode',args.mode,'--users',str(args.users),'--warmup',str(args.warmup),
            '--repetitions',str(args.repetitions),'--host',args.host,'--prometheus',args.prometheus,
            '--seed',str(args.seed),'--locust',args.locust,'--durations',*[str(d) for d in args.durations]]
 sys.argv=[sys.argv[0],*forwarded];experiment.main()
if __name__=='__main__':main()
