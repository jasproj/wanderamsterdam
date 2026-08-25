#!/usr/bin/env python3
"""s49-wams-navfix — release pk 623293 under the D-614 "party-total ladder" rule
(WENG s49 C rule): a party-total ladder rising with band is D-614; the floor TOTAL
anchors, with the tier label used VERBATIM as priceUnit (not a paraphrased "per
group, N" string, unlike the other D-614 rows in this population). No new probe:
priceTiers/priceBasis stamp is the s48 pass's live 2026-08-24 evidence, carried
forward unchanged; only price/priceLabel/priceConfidence/priceSource/priceBasis are
touched, and only for this one pk. Usage: [--execute]
"""
import json, sys, hashlib

DATA = 'tours-data.json'
E = 'scripts/evidence/s49-wams-navfix'
PASS = 's49-wams-navfix'
LADDER_DAY = '2026-08-24'   # ladder evidence date — unchanged, carried from s48
execute = '--execute' in sys.argv

raw = open(DATA, 'rb').read()
doc = json.loads(raw)
assert (json.dumps(doc, indent=2, ensure_ascii=False) + '\n').encode() == raw, 'round-trip not byte-identical; refusing'
rows = doc['tours']
by = {r['pk']: r for r in rows}

PK = 623293
before_hash = {pk: hashlib.sha256(json.dumps(by[pk], sort_keys=True).encode()).hexdigest()
               for pk in by if pk != PK}
before_all_doc_sha256 = hashlib.sha256(raw).hexdigest()

r = by[PK]
prior_price = r['price']; prior_basis = r['priceBasis']
tiers = r['priceTiers']  # carried forward unchanged, already stamped 2026-08-24 by s48
LABEL = 'Private tour 1 person'
anchor = [t for t in tiers if t['singular'] == LABEL]
assert len(anchor) == 1, ('anchor tier not found', LABEL)
assert anchor[0]['price'] == 366.31, anchor[0]['price']

BASIS = (
    "D-614 (per WENG s49 C rule: a party-total ladder rising with band is D-614; "
    "the floor TOTAL anchors, tier label used verbatim as priceUnit): floor tier "
    "\"Private tour 1 person\" = 366.31 EUR (unchanged); priceUnit \"Private tour 1 "
    "person\" is the anchor tier's own label, verbatim, per the C rule's unit "
    "convention for this ladder shape; carried forward from the prior template-ruling "
    "note: this ladder's totals rise linearly by a constant +52.48 EUR/head (366.31, "
    "418.78, 471.26, [523.74 @ n=4], 576.22, 628.70, 681.18, 733.66 = 366.31 + "
    "52.48*(n-1)), and the \"Private tour 1-4 persons\" tier sits exactly where a "
    "clean \"4 persons\" step would land (+52.48 over the 3-person tier) — still "
    "suspected to be a mislabeled/merged \"4 persons\" tier, not a genuine 1-4 range "
    "band; that mislabel note is informational only and does not block release under "
    "the C rule, since the ruling anchors the named floor tier regardless; live ladder "
    "confirmed 2026-08-24 [('Private tour 1 person', 36631, ''), "
    "('Private tour 2 persons', 41878, ''), ('Private tour 3 persons', 47126, ''), "
    "('Private tour 1-4 persons', 52374, ''), ('Private tour 5 persons', 57622, ''), "
    "('Private tour 6 persons', 62870, ''), ('Private tour 7 persons', 68118, ''), "
    "('Private tour 8 persons', 73366, '')]; prior stamp was HELD (template ruling "
    "pending), s48/s47 anchor figure 366.31 EUR unchanged"
)

r['price'] = 366.31
r['priceLabel'] = LABEL
r['priceConfidence'] = 'high'
r['priceSource'] = (f"{PASS}: FareHarbor price-preview per-item v2 (undated, include_breakdown=yes), "
                     f"live {LADDER_DAY}, details.currency EUR; evidence "
                     f"scripts/evidence/s48-wams-held/probe-2026-08-24.json (carried forward, no reprobe)")
r['priceBasis'] = BASIS
r.setdefault('_unknownFields', {})['priceUnit'] = LABEL
r['priceVerifiedAt'] = LADDER_DAY
# priceTiers untouched — already correct from s48

for pk in before_hash:
    assert hashlib.sha256(json.dumps(by[pk], sort_keys=True).encode()).hexdigest() == before_hash[pk], (pk, 'row outside scope changed!')

print(f"{PK} released D-614(C-rule) {prior_price!s:>8} -> {r['price']!s:>8}  {LABEL!r}")

out = json.dumps(doc, indent=2, ensure_ascii=False) + '\n'
after_all_doc_sha256 = hashlib.sha256(out.encode()).hexdigest()

if execute:
    open(DATA, 'w').write(out)
    json.dump(dict(
        pass_=PASS, ladder_day=LADDER_DAY,
        ruling='D-614 (WENG s49 C rule: party-total ladder rising with band; floor TOTAL anchors, tier label verbatim as unit)',
        sha256=dict(before_tours_data=before_all_doc_sha256, after_tours_data=after_all_doc_sha256),
        rows=[dict(pk=PK, name=r['name'], disposition='released', ruling='D-614 (C rule)',
                    prior=prior_price, price=r['price'], label=LABEL, priceUnit=LABEL)],
    ), open(E + '/apply-summary.json', 'w'), indent=1, ensure_ascii=False)
    print('WROTE', DATA)
    print('sha256 before:', before_all_doc_sha256)
    print('sha256 after: ', after_all_doc_sha256)
else:
    print('DRY RUN')
