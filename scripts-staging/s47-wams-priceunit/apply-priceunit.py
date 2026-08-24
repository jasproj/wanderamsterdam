#!/usr/bin/env python3
"""s47-wams-priceunit — release the 2 HELD whole-group rows (#90) now that app.js has
an explicit-field priceUnit render path (KWST mechanism, via WNZ #108).

Deterministic and asserting. Re-derives the population from the data (paynehurdstours
rows at priceConfidence low with a sole positive "Price per group." tier), asserts each
against #90's tracked live readings (amount, tier ladder, live currency EUR, no party
cap anywhere in the evidence), then writes ONLY:
  _unknownFields.priceUnit = "per group"
  priceConfidence           low -> high
  priceReleasedBy           provenance stamp naming this pass
price / priceLabel / priceSource / priceBasis / priceTiers / priceVerifiedAt from #90 stand.
Round-trip: json.dumps(indent=2, ensure_ascii=False)+'\n' asserted byte-identical before writing.
Usage: apply-priceunit.py [--execute]
"""
import json, re, sys
DATA='tours-data.json'
EV='scripts-staging/s46-wams-maxtier-3/live-readings-2026-08-25-anchor.json'
PASS='s47-wams-priceunit'
UNIT='per group'
execute='--execute' in sys.argv

raw=open(DATA,'rb').read(); doc=json.loads(raw)
assert (json.dumps(doc,indent=2,ensure_ascii=False)+'\n').encode()==raw, 'round-trip not byte-identical; refusing'
ev=json.load(open(EV)); assert ev['control']['falsifiable'] and not ev['errors']
evs=json.dumps(ev)
# No party cap anywhere in the tracked evidence -> unit is "per group", not "up to N".
assert not re.search(r'capacity|max_party|maximum|"high": [1-9]', evs), 'cap evidence exists; unit string must carry it'

rows=doc['tours']; by={r['pk']:r for r in rows}
pop=[r for r in rows if 'paynehurdstours' in r.get('bookingUrl','') and r.get('priceConfidence')=='low'
     and [t for t in r.get('priceTiers',[]) if t['priceCents']>0]==[t for t in r.get('priceTiers',[]) if t.get('note')=='Price per group.']
     and len([t for t in r.get('priceTiers',[]) if t['priceCents']>0])==1]
pks=sorted(r['pk'] for r in pop); print('population', pks)
assert pks==[662825,699480], pks
# Any other row the new path would touch? (rows already carrying a priceUnit)
others=[r['pk'] for r in rows if (r.get('_unknownFields') or {}).get('priceUnit') and r['pk'] not in pks]
print('other rows with priceUnit:', others); assert others==[]

before={pk:json.dumps(by[pk],sort_keys=True) for pk in by if pk not in pks}
for r in pop:
    pk=r['pk']; spk=str(pk)
    assert r['priceSource']=='s46-wams-maxtier-3' and r['priceBasis'].startswith('HELD:')
    assert r['currency']=='EUR'
    live=[json.loads(x) for x in ev['liveDetails'][spk]]; assert live and all(l['currency']=='EUR' for l in live), (pk,live)
    grp=[t for t in r['priceTiers'] if t['priceCents']>0][0]
    assert isinstance(r['price'],float) and r['price']==grp['price']==grp['priceCents']/100 and isinstance(grp['priceCents'],int)
    ok=[o for o in ev['obs'][spk].values() if o['status']=='OK' and o['date_valid']]
    assert len(ok)>=16, (pk,len(ok))
    for o in ok:
        pos=[t for t in o['tiers'] if t['cents']>0]
        assert len(pos)==1 and pos[0]['cents']==grp['priceCents'] and pos[0]['note']=='Price per group.' and pos[0]['min_party_size']==1 and o['high'] is None, (pk,o['requested'])
    print(f"{pk}: {r['price']} EUR per group, {len(ok)} date-valid readings agree, live currency EUR -> release")
    r['priceConfidence']='high'
    r['_unknownFields']={'priceUnit':UNIT}
    r['priceReleasedBy']=(f"{PASS}: HELD condition in priceBasis lifted — explicit-field priceUnit render path landed "
                          f"(KWST mechanism via WNZ #108); unit \"{UNIT}\" because no party cap exists in any #90 evidence; "
                          f"live currency EUR per #90 liveDetails; price/basis/tiers stamps from #90 stand")
for pk in before: assert json.dumps(by[pk],sort_keys=True)==before[pk]
out=json.dumps(doc,indent=2,ensure_ascii=False)+'\n'
if execute:
    open(DATA,'w').write(out); print('WROTE', DATA)
else:
    print('DRY RUN — pass --execute to write')
