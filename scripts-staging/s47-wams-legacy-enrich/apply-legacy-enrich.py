#!/usr/bin/env python3
"""s47-wams-legacy-enrich — merge the v7 probe results (obs-legacy-enrich.json, built from the
verbatim writer's scratch-clone runs: pass1 --batch 20, pass2 --batch 4 on the 11 pureboats
timeouts) back into tours-data.json for exactly the 267 legacy unstamped priced rows.

Dispositions (evidence-driven, no row leaves the population):
  high       item returned with a positive tier   -> v7 stamp set + live price/label/breakdown, priceConfidence high
  zero_price item returned, ladder is $0-only      -> stored figure retained, priceConfidence low (no offer),
                                                    $0 ladder recorded not counted, HELD basis
  none       operator HTTP 200 / EUR, item absent  -> stored figure retained, stamped UNSAMPLED, priceConfidence low
                                                    until sampled (WENG #88: unverifiable figure never emits an offer)
Live currency asserted EUR on every row (D-620: any non-EUR would be held low).
Round-trip json.dumps(indent=2, ensure_ascii=False)+'\n' asserted byte-identical before writing;
integral floats from the writer are spelled as ints (JSON.stringify parity). Usage: [--execute]
"""
import json, sys, collections
DATA='tours-data.json'; E='scripts-staging/s47-wams-legacy-enrich'; PASS='s47-wams-legacy-enrich'; DAY='2026-08-24'
execute='--execute' in sys.argv
raw=open(DATA,'rb').read(); doc=json.loads(raw)
assert (json.dumps(doc,indent=2,ensure_ascii=False)+'\n').encode()==raw, 'round-trip not byte-identical; refusing'
ev=json.load(open(E+'/obs-legacy-enrich.json')); obs={int(k):v for k,v in ev['obs'].items()}
rows=doc['tours']; by={r['pk']:r for r in rows}
def stamped(r): return bool(r.get('priceEnrichmentSource') or r.get('priceSource') or r.get('priceVerifiedAt') or (r.get('_unknownFields') or {}).get('priceSource'))
pop=sorted(r['pk'] for r in rows if isinstance(r.get('price'),(int,float)) and r['price']>0 and not stamped(r))
assert pop==sorted(obs), ('population drift', len(pop), len(obs))
assert all(o['status'] in ('high','zero_price','none') for o in obs.values()), 'unresolved error rows; abort'
assert all(len(o['currency'])==1 and o['currency']==['EUR'] for o in ev['operators'].values()), 'non-EUR operator'
def num(x): return int(x) if isinstance(x,float) and x.is_integer() else x
# ---- Ruling stage (post-writer, evidence from the live ladder itself; no writer edit) ----
# R1 child-anchor: the writer's first-positive-tier rule may land on a child tier. WHAW s45 precedent
#    (applied by #90 on 523958): child tiers never anchor "From". Re-anchor to the first positive tier
#    whose label is adult/per-person; if the ladder has none, HOLD.
# R2 whole-group anchor: an anchor tier whose label/note prices a party/boat/charter rather than a seat
#    is #90's HELD class. This branch (off origin/main) has no priceUnit render path, so HOLD low with
#    the true amount + basis stamped; release candidates once the priceUnit path (#91) lands.
import re
CHILD=re.compile(r'\b(child|children|kind|kids?|infant|junior|youth|baby|teen)\b',re.I)
ADULT=re.compile(r'\b(adult|volwassene|person|persoon|adulto)\b',re.I)
PERPERSON=re.compile(r'per person|price pp|prijs per persoon|per persoon|\bpp\b|minimum \d+ people|vanaf \d+ personen|select the number of passengers|^personen\b',re.I)
GROUP=re.compile(r'private|group|grupos|boat|charter|\brent\b|koppel|hire|persons\b|personen|people|pessoas|^one hour$|hours? boat',re.I)
# Party-size sliding ladder ("1 Person 572.40 / 2 People 312.70 / ..."): the seat price depends on party
# size, so the writer's first tier is the dearest, not a "From" anchor. Held until a ruling on that semantic.
SLIDING=re.compile(r'^\d+ (person|people|persons|personen)\b',re.I)
rulings={}
for pk,o in obs.items():
    if o['status']!='high': continue
    tiers=o['live']['tiers']; anchor=[t for t in tiers if t['cents']==round(o['writer']['price']*100)][0]
    lab=anchor['singular'] or ''; note=anchor.get('note') or ''
    if CHILD.search(lab) and not ADULT.search(lab):
        alt=[t for t in tiers if ADULT.search(t['singular'] or '') and not CHILD.search(t['singular'] or '') and not GROUP.search(t['singular'] or '')]
        rulings[pk]=('reanchor',alt[0]) if alt else ('hold','child-only ladder, no adult per-person tier')
    elif CHILD.search(lab) and ADULT.search(lab):  # combo tier e.g. "Volwassene + Kind in fietszitje"
        alt=[t for t in tiers if ADULT.search(t['singular'] or '') and not CHILD.search(t['singular'] or '')]
        if alt: rulings[pk]=('reanchor',alt[0])
    elif SLIDING.search(lab):
        rulings[pk]=('hold',f'anchor tier "{lab}" heads a party-size sliding ladder ({len(tiers)} tiers); per-seat price depends on party size, not a clean "From" anchor')
    elif GROUP.search(lab+' '+note) and not PERPERSON.search(lab+' '+note):
        rulings[pk]=('hold',f'anchor tier "{lab}" ({note or "no note"}) prices a party/boat, not a seat')
before={pk:json.dumps(by[pk],sort_keys=True) for pk in by if pk not in obs}
split=collections.Counter(); moved=collections.Counter(); deltas=[]
for pk,o in obs.items():
    r=by[pk]; w=o['writer']; st=o['status']; live=o['live']; stored=r['price']
    r['priceEnrichmentSource']='extract-prices-v7-api'; r['priceEnrichmentAt']=w['priceEnrichmentAt']; r['priceEnrichmentStatus']=st
    r.pop('priceEnrichmentError',None)
    if st in ('high','zero_price'):
        assert live and live['currency']=='EUR', pk
        r['currency']='EUR'; r['priceIncludesBookingFees']=w['priceIncludesBookingFees']; r['priceIncludesTaxes']=w['priceIncludesTaxes']
        if w['priceBreakdown']: r['priceBreakdown']=[{k:num(v) for k,v in t.items()} for t in w['priceBreakdown']]
    if st=='high' and pk in rulings and rulings[pk][0]=='reanchor':
        t=rulings[pk][1]; split['high:reanchored']+=1
        r['price']=num(t['cents']/100); r['priceLabel']=t['singular']; r['priceConfidence']='high'
        r['priceSource']=f"{PASS}: FareHarbor price-preview per-item v2 (undated, include_breakdown=yes), anchor start_at {live['start_at']}; evidence {E}/obs-legacy-enrich.json"
        r['priceBasis']=f"{t['singular']}: adult/per-person tier of live ladder {[(x['singular'],x['cents']) for x in live['tiers']]}; writer's first-positive tier \"{w['priceLabel']}\" is a child/combo tier and does not anchor (WHAW s45 precedent, #90); zero tiers {live['zero_tiers']}; stored legacy figure was {stored}"
        deltas.append((pk,stored,r['price'])); r['priceVerifiedAt']=DAY; continue
    if st=='high' and pk in rulings and rulings[pk][0]=='hold':
        split['high:held-whole-group']+=1; moved[(r.get('priceConfidence'),'low')]+=1
        r['price']=num(w['price']); r['priceLabel']=w['priceLabel']; r['priceConfidence']='low'
        r['priceSource']=f"{PASS}: FareHarbor price-preview per-item v2 (undated, include_breakdown=yes), anchor start_at {live['start_at']}; evidence {E}/obs-legacy-enrich.json"
        r['priceBasis']=f"HELD: {rulings[pk][1]}; live ladder {[(x['singular'],x['cents'],x.get('note') or '')  for x in live['tiers']]}; true amount {num(w['price'])} EUR stamped; WAMS has no priceUnit render path on this base — release candidate once #91 lands; stored legacy figure was {stored}"
        r['priceVerifiedAt']=DAY; continue
    if st=='high':
        assert isinstance(w['price'],(int,float)) and w['price']>0
        cents=[t for t in r['priceBreakdown'] if t['priceCents']>0][0]; assert isinstance(cents['priceCents'],int) and cents['priceCents']==round(w['price']*100)
        deltas.append((pk,stored,w['price']))
        r['price']=num(w['price']); r['priceLabel']=w['priceLabel']; r['priceConfidence']='high'
        r['priceSource']=f"{PASS}: FareHarbor price-preview per-item v2 (undated, include_breakdown=yes), anchor start_at {live['start_at']}; evidence {E}/obs-legacy-enrich.json"
        r['priceBasis']=f"{w['priceLabel']}: first positive tier of live ladder {[(t['singular'],t['cents']) for t in live['tiers']]}; zero tiers recorded not counted {live['zero_tiers']}; stored legacy figure was {stored}"
    elif st=='zero_price':
        moved[(r.get('priceConfidence'),'low')]+=1
        r['priceConfidence']='low'
        r['priceSource']=f"{PASS}: FareHarbor price-preview per-item v2 (undated), anchor start_at {live['start_at']}; evidence {E}/obs-legacy-enrich.json"
        r['priceBasis']=f"HELD: live ladder is $0-only {live['zero_tiers']} (charter/vehicle preview, D-575); stored legacy figure {stored} EUR retained but unverified and contradicted by the live preview; not published"
    else:
        # Ruling (WENG #88 precedent): an unverifiable figure never emits an offer — JSON-LD is the
        # highest-exposure surface. Figure and stamps stay; only confidence moves, low until sampled.
        moved[(r.get('priceConfidence'),'low')]+=1
        r['priceSource']=f"{PASS}: UNSAMPLED — operator {o['shortname']} reachable (HTTP 200, live currency EUR) but item absent from undated price-preview; stored legacy figure {stored} EUR retained, unverified; priceConfidence {r.get('priceConfidence')}->low until sampled (WENG #88: an unverifiable figure never emits an offer); evidence {E}/obs-legacy-enrich.json"
        r['priceConfidence']='low'
    r['priceVerifiedAt']=DAY
    split[st]+=1
for pk in before: assert json.dumps(by[pk],sort_keys=True)==before[pk]
print('disposition',dict(split)); print('rulings:'); [print(' ',pk,v[0],v[1] if v[0]=='hold' else v[1]['singular']+' '+str(v[1]['cents'])) for pk,v in sorted(rulings.items())]; print('zero_price confidence moves',dict(moved))
same=sum(1 for _,a,b in deltas if a==b); print(f'high: stored==live {same}, changed {len(deltas)-same}; max |delta| {max(abs(b-a) for _,a,b in deltas):.2f}')
out=json.dumps(doc,indent=2,ensure_ascii=False)+'\n'
if execute: open(DATA,'w').write(out); print('WROTE',DATA)
else: print('DRY RUN')
