#!/usr/bin/env python3
"""s45 WAMS currency verify — apply (D-620 / D-618).
Input: live-currency-observations.json from probe-live-currency.py.
- live currency == EUR  -> stamps-only correction: currency='EUR' + provenance stamps. No price fields touched.
- live currency != EUR  -> priceConfidence='low', stamp true currency + live amount; gate renders 'Price on request'.
- unreachable           -> byte-identical, listed.
Round-trip: json.dumps(indent=2, ensure_ascii=False) — verified byte-identical on unmodified input."""
import json,sys
SRC='tours-data.json'; OBS='scripts-staging/s45-wams-currency-verify/live-currency-observations.json'
SITE='EUR'; STAMP='s45-wams-currency-verify'
o=json.load(open(OBS)); obs=o['observations']; ts=o['probedAt']
raw=open(SRC,'rb').read(); d=json.loads(raw)
assert (json.dumps(d,indent=2,ensure_ascii=False)+'\n').encode()==raw, "round-trip not byte-identical; refusing"
eur=[];foreign=[];unreach=[]
for r in d['tours']:
    if r.get('currency')!='USD': continue
    ob=obs.get(str(r['pk']))
    assert ob, f"no observation for {r['pk']}"
    if not ob.get('reachable') or not ob.get('liveCurrency'): unreach.append(r['pk']); continue
    live=ob['liveCurrency']
    r['currencyVerifiedSource']=STAMP; r['currencyVerifiedAt']=ts; r['currencyVerifiedLive']=live
    if live==SITE:
        r['currency']=SITE; eur.append(r['pk'])
    else:
        r['currency']=live; r['priceConfidence']='low'
        r['liveCurrency']=live; r['liveAmount']=ob.get('liveAmount'); foreign.append(r['pk'])
open(SRC,'w',encoding='utf-8').write(json.dumps(d,indent=2,ensure_ascii=False)+'\n')
json.dump({'stamp':STAMP,'probedAt':ts,'corrected_to_EUR':eur,'demoted_foreign_currency':foreign,'unreachable_left_byte_identical':unreach},
          open('scripts-staging/s45-wams-currency-verify/apply-manifest.json','w'),indent=1)
print(f"corrected->EUR {len(eur)}  demoted(foreign) {len(foreign)} {foreign}  unreachable {len(unreach)} {unreach}")
