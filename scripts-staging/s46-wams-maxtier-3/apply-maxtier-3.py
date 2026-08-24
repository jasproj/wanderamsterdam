#!/usr/bin/env python3
"""s46 — apply the 3 max-tier rulings to tours-data.json. DETERMINISTIC, no network.
Reads the frozen live evidence live-readings-2026-08-25-anchor.json and asserts every
written value against date-valid readings before any byte changes.

Dispositions:
  523958 STAMPS-ONLY  adult per-person tier Volwassene 31.65 stays (child tiers never anchor "From";
                WHAW s45 precedent 57549); priceConfidence high; full ladder incl. €0 Infant + €15.83 Kind stamped.
  662825 HOLD   single positive tier "Group" / note "Price per group." = whole-group fare;
  699480 HOLD   WAMS has no unit render path -> priceConfidence low, true basis stamped,
                amount left as the true whole-group value (render + JSON-LD suppressed).
4-field stamp on all three (flat, WAMS style): priceSource, priceBasis, priceTiers, priceVerifiedAt.
Round-trip: json.dumps(indent=2, ensure_ascii=False)+'\n' asserted byte-identical before writing.
"""
import json, sys, re
from pathlib import Path
REPO=Path(__file__).resolve().parents[2]
TOURS=REPO/'tours-data.json'; EV=Path(__file__).resolve().parent/'live-readings-2026-08-25-anchor.json'
SRC='s46-wams-maxtier-3'
ev=json.load(open(EV)); assert ev['control']['falsifiable'] and not ev['errors']
raw=TOURS.read_bytes(); doc=json.loads(raw)
assert (json.dumps(doc,indent=2,ensure_ascii=False)+'\n').encode()==raw, 'round-trip not byte-identical; refusing'
by={t['pk']:t for t in doc['tours']}
POP={523958,662825,699480}; assert set(map(int,ev['obs']))==POP
def money(cents): v=round(cents/100,2); return int(v) if float(v).is_integer() else v
def ladder(pk):
    """Stable ladder across all date-valid readings (positive + zero tiers), asserted identical on every date."""
    sigs=set(); lad=None
    for day,v in sorted(ev['obs'][str(pk)].items()):
        if not v.get('date_valid'): continue
        l=[{'id':t['tier_id'],'singular':t['singular'],'plural':t['plural'],'note':t['note'],'priceCents':int(t['cents']),'price':money(t['cents']),'minPartySize':t['min_party_size']} for t in v['tiers']+v['zero_tiers']]
        sigs.add(json.dumps(l,sort_keys=True)); lad=l
    assert len(sigs)==1, ('unstable ladder',pk,len(sigs))
    return lad
VERIFIED_AT='2026-08-24'  # probe date (probe-run.log); the readings file carries the 17-date window
before={pk:json.dumps(by[pk],sort_keys=True) for pk in by if pk not in POP}
def stamp(row,basis):
    row['priceSource']=SRC; row['priceBasis']=basis; row['priceTiers']=ladder(row['pk']); row['priceVerifiedAt']=VERIFIED_AT
# 523958 STAMPS-ONLY (adult anchors "From"; child tiers never do — WHAW s45 precedent 57549)
r=by[523958]; lad=ladder(523958)
pos=[t for t in lad if t['priceCents']>0]; adult=next(t for t in pos if t['singular']=='Volwassene')
assert adult['priceCents']==3165 and all(t['minPartySize']==1 for t in pos), lad
assert {t['singular']:t['priceCents'] for t in lad}=={'Infant':0,'Volwassene':3165,'Kind':1583}, lad
assert 'per group' not in ' '.join((t['note'] or '') for t in pos).lower()
assert r['price']==31.65 and r['priceLabel']=='Volwassene'  # price + label unchanged
r['priceConfidence']='high'
stamp(r,'Volwassene: adult per-person tier of live ladder (Infant 0 / Volwassene 31.65 / Kind 15.83), 17/17 date-valid; adult anchors "From", child tier Kind 15.83 does not (WHAW s45 precedent 57549)')
# 662825 / 699480 HOLD
for pk,cents in ((662825,99711),(699480,52479)):
    r=by[pk]; lad=ladder(pk); pos=[t for t in lad if t['priceCents']>0]
    assert len(pos)==1 and pos[0]['singular']=='Group' and pos[0]['priceCents']==cents and 'per group' in pos[0]['note'].lower(), lad
    assert r['price']==money(cents) and r['priceLabel']=='Group'
    r['priceConfidence']='low'
    stamp(r,f'HELD: sole positive tier "Group" note "{pos[0]["note"]}" is a whole-group fare ({money(cents)} EUR per group, min_party_size 1, no party cap); Child 0 EUR per person. WAMS has no priceUnit render path; not published as a per-person "From" price')
for pk in before: assert json.dumps(by[pk],sort_keys=True)==before[pk]
out=json.dumps(doc,indent=2,ensure_ascii=False)+'\n'
if '--execute' in sys.argv: TOURS.write_text(out,encoding='utf-8'); print('WROTE',len(raw),'->',len(out.encode()))
else: print('DRY RUN ok; would write',len(out.encode()),'bytes (was',len(raw),')')
