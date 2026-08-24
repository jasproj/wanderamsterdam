#!/usr/bin/env python3
"""s48-wams-heldrelease — release 30 of the 34 s47 HELD rows under Jason's rulings; 4 stay held.

Rulings applied (2026-08-24):
  s48-R1 sliding-ladder ruling (largest-band per-person floor anchors; decision id pending) (R1, new): per-person sliding ladder -> the LARGEST-BAND per-person figure anchors "From"
        (floor of the ladder = cheapest non-concession fare; usually FareHarbor price.low — 524008 differs, recorded in priceBasis).
  D-614: whole-group ladder banded by party size -> the floor band publishes.
  D-621: child tiers are concessions and never anchor; re-anchor to the first non-concession tier.
  R2:    a row releases only if a priceUnit string is derivable VERBATIM from a tier label/note;
         rows with no derivable unit stay held.
All amounts are read from the live probe JSON (scripts/evidence/s48-wams-held/probe-2026-08-24.json,
FareHarbor price-preview per-item v2, include_breakdown=yes, all 34 sampled, details.currency EUR);
nothing is written from stored data. Rows outside the 34 asserted byte-identical.  Usage: [--execute]
"""
import json, sys, re, collections
DATA = 'tours-data.json'; E = 'scripts/evidence/s48-wams-held'; PASS = 's48-wams-heldrelease'; DAY = '2026-08-24'
execute = '--execute' in sys.argv
raw = open(DATA, 'rb').read(); doc = json.loads(raw)
assert (json.dumps(doc, indent=2, ensure_ascii=False) + '\n').encode() == raw, 'round-trip not byte-identical; refusing'
probe = json.load(open(E + '/probe-2026-08-24.json')); items = {int(k): v for k, v in probe['items'].items()}
rows = doc['tours']; by = {r['pk']: r for r in rows}
STAMP = 's47-wams-legacy-enrich: FareHarbor price-preview per-item v2 (undated, include_breakdown=yes)'
def held(r):
    ps = r.get('priceSource') or ''; pb = r.get('priceBasis') or ''
    return ps.startswith(STAMP) and pb.startswith('HELD:') and r.get('priceVerifiedAt') == '2026-08-24' and '$0-only' not in pb
pop = sorted(r['pk'] for r in rows if held(r))
assert len(pop) == 34 and pop == sorted(items), ('population drift', len(pop), len(items))

# pk -> (ruling, anchor tier label, priceUnit, extra basis note). Unit strings are derived from the quoted label/note only.
def rel(ruling, label, unit, note=''): return dict(ruling=ruling, label=label, unit=unit, note=note)
PDTA = rel('s48-R1 sliding-ladder ruling (largest-band per-person floor anchors; decision id pending)', '6 People', 'per person, group of 6', 'per-person sliding ladder; 1 Person tier is the dearest, not a "From" anchor')
PLAN = {
    117571: PDTA, 177428: PDTA, 190046: PDTA, 190121: PDTA, 190128: PDTA, 190132: PDTA, 190099: PDTA,
    384741: rel('s48-R1 sliding-ladder ruling (largest-band per-person floor anchors; decision id pending)', '10+ persons', 'per person, group of 10+',
                'quirk: 1 person 207.82 = 2 x 103.91 = 3 x 69.27 ~= 4 x 51.95 -- the 1-4 tiers divide a fixed ~207.82 group fare; per-head only from the 10+ band'),
    524008: rel('s48-R1 sliding-ladder ruling (largest-band per-person floor anchors; decision id pending)', 'Group of 10 ( age 5+ / price pp)', 'per person, group of 10', 'per-person sliding ladder (price pp)'),
    148032: rel('D-614', 'Private Cruise', 'per group, up to 12 people', 'single whole-group tier; note "Up to 12 People"'),
    672906: rel('D-614', 'Private group of 1 to 15 people', 'per group, 1 to 15 people', 'single whole-group tier'),
    234991: rel('D-614', 'Group of 1 to 3 people', 'per group, 1 to 3 people', 'note "Price per group"; floor band'),
    353963: rel('D-614', 'Extra Small Group - 1 to 6 persons', 'per group, 1 to 6 persons', 'floor band'),
    354014: rel('D-614', 'Extra Small Group - 1 to 6 persons', 'per group, 1 to 6 persons', 'floor band'),
    396248: rel('D-614', 'Grupos de 1-5 Pessoas', 'per group, 1-5 pessoas', 'floor band'),
    396252: rel('D-614', 'Grupos de 1-5 Pessoas', 'per group, 1-5 pessoas', 'floor band'),
    690937: rel('D-614', 'Private tour 1-4 persons', 'per group, 1-4 persons', 'floor band'),
    314373: rel('D-614', 'Boat "Lucy" 90 Minutes', 'per boat, max 6 people', 'whole-boat duration ladder; shortest duration; note "Classic Boat • max 6 people"'),
    415027: rel('D-614', 'Boat "Lucy" 90 Minutes', 'per boat, max 6 people', 'whole-boat duration ladder; shortest duration; note "Classic Boat • max 6 people"'),
    314378: rel('D-614', 'Boat "Geertje" - 90 min', 'per boat, max 10 people', 'whole-boat duration ladder; note "Small open boat • max 10 people"'),
    314383: rel('D-614', 'Boat "Geertje" - 90 min', 'per boat, max 10 people', 'whole-boat duration ladder; note "Small open boat • max 10 people"'),
    314385: rel('D-614', 'Boat "Schollevaar" - 90 min', 'per boat, max 10 people', 'whole-boat duration ladder; note "Classic Boat • max 10 people"'),
    314386: rel('D-614', 'Boat "Pure Spirit" - 90 min', 'per boat, max 20 people', 'whole-boat duration ladder; note "The Flagship • max 20 people"'),
    576273: rel('D-614', 'Boat "Stan Huygens" - 90 Minutes', 'per boat, max 36 people', 'whole-boat duration ladder; note "Classic Boat • max 36 people"'),
    635956: rel('D-614', 'Anderhalf uur Privé Tour', 'per boat, maximaal 6 personen', 'whole-boat duration ladder; note "Maximaal 6 personen"'),
    540184: rel('D-614', 'Private Charter - Boat Hedir', 'per boat, 11 seater', 'vessel-banded; note "Private Hire of our 11 seater boat Hedir, with storyteller and captain."'),
    453211: rel('D-614', 'Koppel / Twee personen', 'per couple', 'hybrid ladder; couple tier is the smallest bookable unit; note "Prijs per koppel"; NOT the large-group per-person tiers'),
    619538: rel('D-614', 'Koppel / Twee personen', 'per couple', 'hybrid ladder; couple tier is the smallest bookable unit; note "Prijs per koppel"; NOT the large-group per-person tiers'),
    508139: rel('D-614', 'Koppel / Twee personen', 'per couple', 'hybrid ladder; couple tier is the smallest bookable unit; note "Prijs per koppel"; NOT the large-group per-person tiers'),
    592154: rel('D-621', 'Private Group - 1 Hour Cruise', 'per boat, 1 hour', 'child tiers ("Child | No Drinks" 18.84, "Child | Including Drinks" 25.17) are concessions and never anchor; prior s47 figure 18.84 was child-anchored'),
}
HOLD = {107307: 'anchor "2 hours boat cruise" prices a boat but no tier label/note carries cap or party language',
        244818: 'anchor "One hour and half  boat rent incl. skipper" prices a boat but no tier label/note carries cap or party language',
        326244: 'anchor "Private Cruise - 1 Hour" prices a boat but no tier label/note carries cap or party language',
        623293: 'whole-group ladder ("Private tour 1 person" .. "8 persons") but no tier label/note carries a unit-bearing cap or per-group note'}
assert set(PLAN) | set(HOLD) == set(pop) and not set(PLAN) & set(HOLD) and len(PLAN) == 30 and len(HOLD) == 4
def num(x): return int(x) if isinstance(x, float) and x.is_integer() else x
def tiers_of(pk):
    it = items[pk]['item']; cts = it['price']['breakdown']['customer_types']
    return [dict(singular=c['singular'], plural=c.get('plural'), note=c.get('note') or '', priceCents=c['price'], price=num(c['price'] / 100), minPartySize=c.get('min_party_size')) for c in cts], it['price'].get('low')
before = {pk: json.dumps(by[pk], sort_keys=True) for pk in by if pk not in items}
summary = []
for pk in pop:
    r = by[pk]; tiers, low = tiers_of(pk); cur = items[pk]['currency']; assert cur == 'EUR', (pk, cur)
    prior = r['price']
    if pk in PLAN:
        p = PLAN[pk]; anchor = [t for t in tiers if t['singular'] == p['label']]; assert len(anchor) == 1, (pk, p['label'])
        a = anchor[0]; assert a['priceCents'] > 0
        lowNote = f"FH price.low {low}" + ('' if a['priceCents'] == low else f' (not the ruled anchor {a["priceCents"]}: FH low is the cheapest tier of any kind; the ruling anchors the named tier)')
        r['price'] = num(a['priceCents'] / 100); r['priceLabel'] = a['singular']; r['priceConfidence'] = 'high'; r['currency'] = 'EUR'
        r.setdefault('_unknownFields', {})['priceUnit'] = p['unit']
        r['priceSource'] = f"{PASS}: FareHarbor price-preview per-item v2 (undated, include_breakdown=yes), live {DAY}, details.currency EUR; evidence {E}/probe-2026-08-24.json"
        r['priceBasis'] = f"{p['ruling']}: anchor tier \"{a['singular']}\"{(' (' + a['note'] + ')') if a['note'] else ''} = {r['price']} EUR; priceUnit \"{p['unit']}\" derived verbatim from that label/note; {p['note']}; {lowNote}; live ladder {[(t['singular'], t['priceCents']) for t in tiers]}; prior s47 HELD figure was {prior}"
        r['priceTiers'] = tiers; r['priceVerifiedAt'] = DAY
        summary.append(dict(pk=pk, name=r['name'], disposition='released', ruling=p['ruling'], prior=prior, price=r['price'], label=a['singular'], priceUnit=p['unit']))
    else:
        r['priceConfidence'] = 'low'
        r['priceSource'] = f"{PASS}: FareHarbor price-preview per-item v2 (undated, include_breakdown=yes), live {DAY}, details.currency EUR; evidence {E}/probe-2026-08-24.json"
        r['priceBasis'] = f"HELD (R2, no derivable priceUnit): {HOLD[pk]}; live ladder confirmed {DAY} {[(t['singular'], t['priceCents'], t['note']) for t in tiers]}; stored figure {prior} EUR (s47 anchor) retained; live floor {num(min(t['priceCents'] for t in tiers if t['priceCents'] > 0) / 100)} EUR; not published"
        r['priceTiers'] = tiers; r['priceVerifiedAt'] = DAY
        summary.append(dict(pk=pk, name=r['name'], disposition='held', ruling='R2', prior=prior, price=r['price'], label=r.get('priceLabel'), priceUnit=None))
for pk in before: assert json.dumps(by[pk], sort_keys=True) == before[pk], pk
c = collections.Counter((s['disposition'], s['ruling']) for s in summary); print(dict(c))
for s in summary: print(f"{s['pk']} {s['disposition']:8} {s['ruling']:6} {s['prior']!s:>7} -> {s['price']!s:>7}  {s['priceUnit'] or '-'}")
out = json.dumps(doc, indent=2, ensure_ascii=False) + '\n'
if execute:
    open(DATA, 'w').write(out); json.dump(dict(pass_=PASS, day=DAY, rulings={'s48-R1 sliding-ladder ruling (largest-band per-person floor anchors; decision id pending)': 'largest-band per-person figure anchors From (R1)', 'D-614': 'whole-group floor band publishes', 'D-621': 'child tiers never anchor', 'R2': 'no derivable priceUnit -> stays held'}, rows=summary), open(E + '/apply-summary.json', 'w'), indent=1, ensure_ascii=False); print('WROTE', DATA)
else: print('DRY RUN')
