import pandas as pd
from pathlib import Path

left = pd.read_csv('outputs/ccp_registry_enriched.csv', dtype=str).fillna('')
right = pd.read_csv('outputs/adjudications.csv', dtype=str).fillna('')

on = ['review_id','section','claim_id']
lk = left[on].astype(str)
rk = right[on].astype(str)

lk['_key'] = lk.apply(lambda r: '|'.join([r[c] for c in on]), axis=1)
rk['_key'] = rk.apply(lambda r: '|'.join([r[c] for c in on]), axis=1)

left_only = set(lk['_key']) - set(rk['_key'])
right_only = set(rk['_key']) - set(lk['_key'])

print('left rows:', len(left))
print('right rows:', len(right))
print('shared keys:', len(set(lk['_key']) & set(rk['_key'])))
print('left-only keys:', len(left_only))
print('right-only keys:', len(right_only))

print('Example left-only (first 5):')
for k in list(left_only)[:5]:
    print('  ', k)

print('Example right-only (first 5):')
for k in list(right_only)[:5]:
    print('  ', k)

