#!/usr/bin/env python3
"""s49-wams-heldrelease-2 — release 3 of the 4 s48 HELD rows under Jason's D-?? ruling
(description-derived priceUnit sanctioned when sourced verbatim, with conflicts flagged
in-stamp); 1 stays held pending a template ruling (R1 vs D-614) on its mixed party-size
ladder. No new probe: all four rows' priceTiers/priceBasis stamps are fresh 2026-08-24
from the s48 pass (scripts/evidence/s48-wams-held/probe-2026-08-24.json) and are carried
forward unchanged; only price/priceLabel/priceConfidence/priceSource/priceBasis/
_unknownFields.priceUnit are touched, and only for the 4 in-scope pks. Usage: [--execute]
"""
import json, sys, hashlib, collections

DATA = 'tours-data.json'
E = 'scripts/evidence/s49-wams-heldrelease2'
PASS = 's49-wams-heldrelease-2'
LADDER_DAY = '2026-08-24'   # ladder evidence date — unchanged, carried from s48
WALL_DAY = '2026-08-25'     # today's wall clock, apply-summary only
execute = '--execute' in sys.argv

raw = open(DATA, 'rb').read()
doc = json.loads(raw)
assert (json.dumps(doc, indent=2, ensure_ascii=False) + '\n').encode() == raw, 'round-trip not byte-identical; refusing'
rows = doc['tours']
by = {r['pk']: r for r in rows}

IN_SCOPE = {107307, 244818, 326244, 623293}
before_hash = {pk: hashlib.sha256(json.dumps(by[pk], sort_keys=True).encode()).hexdigest()
               for pk in by if pk not in IN_SCOPE}
before_all_doc_sha256 = hashlib.sha256(raw).hexdigest()

RULING = 'D-?? (pending): description-derived priceUnit sanctioned — source quoted verbatim in priceBasis, conflicts flagged in-stamp'

RELEASE = {
    107307: dict(
        label='1,5 hours boat cruise', price=350.0,
        unit='per boat, up to 12 guests',
        basis=(f"{RULING}: floor tier \"1,5 hours boat cruise\" = 350.0 EUR "
               f"(drops from the s48 HELD anchor 450 EUR on tier \"2 hours boat cruise\" — "
               f"floor is the cheaper of the two live tiers, not the prior s47 anchor); "
               f"priceUnit \"per boat, up to 12 guests\" derived verbatim from description: "
               f"\"The boats are cozy and private, with space for up to 12 guests.\"; "
               f"FLAG: stored capacity field = 10, description says 12 — unit follows the "
               f"description quote, capacity field not reconciled; live ladder "
               f"[('2 hours boat cruise', 45000, ''), ('1,5 hours boat cruise', 35000, '')]; "
               f"prior stamp was HELD (R2, no derivable priceUnit), s47 anchor figure 450 EUR"),
    ),
    244818: dict(
        label='One hour and half  boat rent incl. skipper', price=466.86,
        unit='per boat, up to 85 passengers',
        basis=(f"{RULING}: anchor/floor tier \"One hour and half  boat rent incl. skipper\" = "
               f"466.86 EUR (unchanged from s48); priceUnit \"per boat, up to 85 passengers\" "
               f"derived verbatim from description: \"Capacity / Up to 85 passengers\" (header-"
               f"labeled block); matches stored capacity field 85 — no conflict; live ladder "
               f"[('One hour and half  boat rent incl. skipper', 46686, ''), "
               f"('Two hours boat rent incl. skipper', 62248, ''), "
               f"('Two hours and half  boat rent incl. skipper', 77810, ''), "
               f"('Three hours boat rent incl. skipper', 93372, '')]; "
               f"prior stamp was HELD (R2, no derivable priceUnit)"),
    ),
    326244: dict(
        label='Private Cruise - 1 Hour', price=369.27,
        unit='per boat, up to 12 guests',
        basis=(f"{RULING}: anchor/floor tier \"Private Cruise - 1 Hour\" = 369.27 EUR "
               f"(unchanged from s48); priceUnit \"per boat, up to 12 guests\" derived verbatim "
               f"from description/highlights: \"The cruise is intimate and has no more than 12 "
               f"guests on board.\"; FLAG: stored duration field \"90 Minutes\" mismatches the "
               f"anchor tier \"Private Cruise - 1 Hour\" (90 min pairs with the second tier, "
               f"\"Private Cruise - 1.5 Hours\", 501.15 EUR) — unit and price follow the ruled "
               f"1-Hour anchor, duration field not reconciled; live ladder "
               f"[('Private Cruise - 1 Hour', 36927, ''), ('Private Cruise - 1.5 Hours', 50115, ''), "
               f"('Private Cruise - 2 Hours', 63303, ''), ('Private Cruise - 2.5 Hours', 76491, ''), "
               f"('Private Cruise - 3 Hours', 89679, ''), ('Private Cruise - 3.5 Hours', 102867, ''), "
               f"('Private Cruise - 5.5 Hours', 171445, ''), ('Private Cruise - 7.5 Hours', 234748, '')]; "
               f"prior stamp was HELD (R2, no derivable priceUnit)"),
    ),
}

HOLD_RESTAMP = {
    623293: ("HELD (template ruling pending): whole-group ladder (\"Private tour 1 person\" .. "
             "\"8 persons\") — tier labels carry party-size text but do not fit either established "
             "template cleanly: not a single D-614 whole-group-band tier (cf. pk 690937's lone "
             "\"Private tour 1-4 persons\" tier), and not a clean R1 per-person sliding ladder "
             "(R1 tiers are themselves per-head rates); this ladder's totals increase linearly by "
             "a constant +52.48 EUR/head (366.31, 418.78, 471.26, [523.74 @ n=4], 576.22, 628.70, "
             "681.18, 733.66 = 366.31 + 52.48*(n-1)), i.e. a base-fee-plus-per-head group total, "
             "not a per-attendee rate card; the \"Private tour 1-4 persons\" tier sits exactly where "
             "a clean \"4 persons\" step would (+52.48 over the 3-person tier) and is suspected to be "
             "a mislabeled/merged \"4 persons\" tier rather than a genuine 1-4 range band; queued for "
             "a ruling on which template (R1 sliding-per-person vs D-614 whole-group-band) governs a "
             "mixed incremental/banded party ladder, and on the suspected \"1-4 persons\" mislabel; "
             "no description/title cap language found to derive a unit from independently; live "
             "ladder confirmed 2026-08-24 [('Private tour 1 person', 36631, ''), "
             "('Private tour 2 persons', 41878, ''), ('Private tour 3 persons', 47126, ''), "
             "('Private tour 1-4 persons', 52374, ''), ('Private tour 5 persons', 57622, ''), "
             "('Private tour 6 persons', 62870, ''), ('Private tour 7 persons', 68118, ''), "
             "('Private tour 8 persons', 73366, '')]; stored figure 366.31 EUR (s47 anchor) "
             "retained; live floor 366.31 EUR; not published"),
}

assert set(RELEASE) | set(HOLD_RESTAMP) == IN_SCOPE and not set(RELEASE) & set(HOLD_RESTAMP)
assert len(RELEASE) == 3 and len(HOLD_RESTAMP) == 1

summary = []
for pk, p in RELEASE.items():
    r = by[pk]
    prior_price = r['price']; prior_basis = r['priceBasis']
    tiers = r['priceTiers']  # carried forward unchanged, already stamped 2026-08-24 by s48
    anchor = [t for t in tiers if t['singular'] == p['label']]
    assert len(anchor) == 1, (pk, p['label'])
    assert anchor[0]['price'] == p['price'], (pk, anchor[0]['price'], p['price'])

    r['price'] = p['price']
    r['priceLabel'] = p['label']
    r['priceConfidence'] = 'high'
    r['priceSource'] = (f"{PASS}: FareHarbor price-preview per-item v2 (undated, include_breakdown=yes), "
                         f"live {LADDER_DAY}, details.currency EUR; evidence "
                         f"scripts/evidence/s48-wams-held/probe-2026-08-24.json (carried forward, no reprobe)")
    r['priceBasis'] = p['basis']
    r.setdefault('_unknownFields', {})['priceUnit'] = p['unit']
    r['priceVerifiedAt'] = LADDER_DAY
    # priceTiers untouched — already correct from s48

    summary.append(dict(pk=pk, name=r['name'], disposition='released', ruling='D-??',
                         prior=prior_price, price=r['price'], label=p['label'], priceUnit=p['unit']))

for pk, basis in HOLD_RESTAMP.items():
    r = by[pk]
    prior_basis = r['priceBasis']
    r['priceBasis'] = basis
    # price, priceLabel, priceConfidence, priceSource, priceTiers, priceVerifiedAt: untouched
    summary.append(dict(pk=pk, name=r['name'], disposition='held', ruling='R2 (restamped)',
                         prior=r['price'], price=r['price'], label=r.get('priceLabel'), priceUnit=None))

for pk in before_hash:
    assert hashlib.sha256(json.dumps(by[pk], sort_keys=True).encode()).hexdigest() == before_hash[pk], (pk, 'row outside scope changed!')

c = collections.Counter((s['disposition'], s['ruling']) for s in summary)
print(dict(c))
for s in summary:
    print(f"{s['pk']} {s['disposition']:8} {s['ruling']:16} {s['prior']!s:>8} -> {s['price']!s:>8}  {s['priceUnit'] or '-'}")

out = json.dumps(doc, indent=2, ensure_ascii=False) + '\n'
after_all_doc_sha256 = hashlib.sha256(out.encode()).hexdigest()

if execute:
    open(DATA, 'w').write(out)
    json.dump(dict(
        pass_=PASS, wall_day=WALL_DAY, ladder_day=LADDER_DAY,
        rulings={'D-??': 'description-derived priceUnit sanctioned (source quoted verbatim, conflicts flagged in-stamp); pending id assignment',
                 'R2 (restamped)': 'no derivable priceUnit from either channel; template ruling queued (pk 623293)'},
        sha256=dict(before_tours_data=before_all_doc_sha256, after_tours_data=after_all_doc_sha256),
        rows=summary,
    ), open(E + '/apply-summary.json', 'w'), indent=1, ensure_ascii=False)
    print('WROTE', DATA)
    print('sha256 before:', before_all_doc_sha256)
    print('sha256 after: ', after_all_doc_sha256)
else:
    print('DRY RUN')
