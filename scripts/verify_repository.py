#!/usr/bin/env python3
"""Offline checks for poster evidence consistency and repository documentation."""
from pathlib import Path
import csv, hashlib, json, re
ROOT=Path(__file__).resolve().parents[1]
def rows(p):
 with p.open() as f: return list(csv.DictReader(f))
a=rows(ROOT/'results/runs.csv'); b=rows(ROOT/'outputs/poster-assets/data/runs.csv')
assert a==b, 'Poster observations differ from final campaign'
assert rows(ROOT/'results/duration_summary.csv')==rows(ROOT/'outputs/poster-assets/data/duration_summary.csv')
assert len(a)==32 and all(sum(float(x['duration_s'])==d for x in a)==8 for d in (15,30,60,120))
assert sum(int(x['requests']) for x in a)==562888
assert all(int(x['failures'])==0 for x in a)
for p in [ROOT/'README.md', *ROOT.glob('docs/*.md'), ROOT/'infrastructure/README.md', ROOT/'outputs/poster-assets/README.md']:
 for target in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',p.read_text()):
  if '://' in target or target.startswith('#'): continue
  target=target.split('#')[0]
  assert (p.parent/target).exists(), (p,target)
for p in ROOT.rglob('SHA256SUMS'):
 for line in p.read_text().splitlines():
  expected,rel=line.split('  ',1)
  assert hashlib.sha256((p.parent/rel).read_bytes()).hexdigest()==expected,(p,rel)
print('PASS: 32 campaign observations, poster CSV agreement, 562888 operations, zero failures, documentation links and checksums.')
