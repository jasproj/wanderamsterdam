#!/usr/bin/env python3
"""s51-wams-tiers-backfill — APPLY stage. Tiers backfill for the 233 s47-wams-legacy-enrich rows
that never got a structured priceTiers array (190 sampled with tiers=None, 43 UNSAMPLED). Every
row in the population is re-probed fresh (scripts/evidence/s51-wams-tiers-backfill/probe.mjs,
undated price-preview per-item v2, include_breakdown=yes — matches extract-prices-v7-api.js /
s47's own convention; never parses tiers out of priceBasis prose).

Classifier: byte-identical port of scripts/s49-wams-refresh-apply.py's classify()/classify_ladder()/
unit_for_group()/r1_ladder()/hybrid_couple() (D-624/D-625/D-614/D-621 family, post-#99 ASCII-sibling
fix), PLUS the standing NFC/okina never-anchor rule (id pending; ai-memory-hub wtpa/MEMORY.md
_network.md: "the never-anchor test must be unicode-normalised everywhere (NFC, okina/macron
folds)"): every NEVER/AGE_RANGE test runs against both the raw label and its NFKD-folded form
(combining marks stripped, okina/typographic-apostrophe variants collapsed), catching diacritic
forms this population's live vocabulary might carry that PR #99's literal ASCII siblings don't.

Dispositions:
  base/hybrid-couple/r1-ladder/group/single-tier  -> anchor derived exactly as s49; price WRITTEN
                                                      if it differs from the currently stored figure
  zero-base (all live tiers €0)                    -> closed-date read (s49's zero_price branch):
                                                      price nulled, low, tiers stamped for evidence
  no anchorable tier (HELD)                        -> floor of non-zero tiers stamped, low
  absent from probe / probe error                  -> UNSAMPLED, low, PRICE UNCHANGED ("low never
                                                      releases" — stamps/confidence/date only)
Every touched row gets a full 4-field dated stamp: priceSource, priceBasis, priceTiers,
priceConfidence, priceVerifiedAt. priceSource = s51-wams-tiers-backfill. Usage: [--execute]
"""
import json, re, sys, hashlib, unicodedata, collections
DATA = 'tours-data.json'; EV = 'scripts/evidence/s51-wams-tiers-backfill'; SOURCE = 's51-wams-tiers-backfill'; STAMP_DAY = '2026-08-26'
execute = '--execute' in sys.argv
raw = open(DATA, 'rb').read(); doc = json.loads(raw)
assert (json.dumps(doc, indent=2, ensure_ascii=False) + '\n').encode() == raw, 'round-trip not byte-identical; refusing'
pop_pks = set(json.load(open(f'{EV}/population.json')))
probe = json.load(open(f'{EV}/probe.json'))
assert probe['reconcile']['population'] == len(pop_pks), ('probe population drift', probe['reconcile']['population'], len(pop_pks))
rows = doc['tours']; pop = [t for t in rows if t['pk'] in pop_pks]
assert len(pop) == len(pop_pks) == 233, ('population drift', len(pop))
def num(x): return int(x) if isinstance(x, float) and x.is_integer() else x
def u(c): return num(round(c / 100, 2))

# ---- unicode-normalized never-test (standing rule, id pending) ----
OKINA = str.maketrans({'ʻ': "'", 'ʼ': "'", '‘': "'", '’': "'"})
def fold(s):
    s = (s or '').translate(OKINA)
    return ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c))

# ---- tier classification (D-624 / D-625 / D-621) — verbatim port of scripts/s49-wams-refresh-apply.py ----
NEVER = re.compile(r"\b(child|childs|child's|children|childrens|children's|kid|kids|kid's|infant|infants|baby|babies|toddler|junior|juniors|youth|youths|teen|teenager|teens|adolescent|adolescents|young adult|student|students|senior|seniors|oap|concession|concessions|pensioner|disabled|wheelchair|carer|companion|blue light|nhs|discount|under\s*\d+s?|\d+\s*(and|&)\s*under|family|families|bundle|package|add[- ]?on|extra(?!\s*(small|large|klein|groot|grote))|extras|additional|supplement|upgrade|gratuity|tip|tips|donation|deposit|voucher|gift card|redemption|per additional|spectator|non[- ]?participant|dog|dogs|pet|pets|kit|merchandise|parking|niño|niños|niña|niñas|nino|ninos|nina|ninas|bebé|bebe|infante|enfant|enfants|bébé|kind|kinder|bambino|bambini|neonato|neonati|ragazzo|ragazzi|ragazza|ragazze"
                   r"|kinderen|kindje|kids?tarief|peuter|peuters|baby's|jeugd|jongeren|studenten|senioren|65\+|korting|toeslag|bijboeking|extra's|optie|opties|fooi|borg|cadeaubon|hond|honden|huisdier|familie|gezin|gezinsticket|pakket|arrangement"
                   r"|joven|jóvenes|jovenes|criança|crianças|niñ[oa]s?|kinderfiets|kids? ?bike|child(?:ren'?s?)? bike|kinderzitje"
                   r"|aggiuntiv[oa]|adicional|adicionales|zusätzlich|zusätzliche|zusatzlich|zusatzliche|supplémentaire|extra persoon|bijboeken|optional|optioneel|upgrade|aanbetaling|voorschot|deposito|caparra|kaution|anzahlung"
                   r"|儿童|孩子|学生|老年|优惠)\b|^add (a|an|the)\b|儿童|孩子|学生|老年|优惠", re.I)
NOT_A_PRICE = re.compile(r"\b(deposit|deposito|borg|aanbetaling|voorschot|caparra|kaution|anzahlung|voucher|gift card|cadeaubon|donation|gratuity|tip|tips|fooi)\b", re.I)
ACCESSORY = re.compile(r"\b(bag|bags|tas|lock|slot|helmet|helm|child seat|kinderzitje|zitje|seat|basket|mand|poncho|regenjas|raincoat|insurance|verzekering|boots?|gloves?|hoods?|wetsuit|trailer|fietskar|bakfiets ?zitje|kaart|map|extra[- ]person|extra participants?)\b", re.I)
RENTAL_NAME = re.compile(r"\b(hire|rental|rent|huur|verhuur|huren)\b", re.I)
AGE_RANGE = re.compile(r"\b\d{1,2}\s*(-|–|to|t/m|tot)\s*\d{1,2}\s*(yrs|rys|years|year olds|yr olds|y/o|y/old|yo|años|anos|ans|anni|jaar|jr)\b", re.I)
WORDNUM = r"(two|three|four|five|six|seven|eight|nine|ten|twelve|twee|drie|vier|vijf|zes|zeven|acht|negen|tien|twaalf|\d+)"
GROUP = re.compile(r"\b(per group|group|groups|party|parties|private|exclusive|charter|boat|vessel|vehicle|car|van|minibus|coach|table|room|cabin|pod|lane|court|couple|couples|for two|for 2|whole|hire|rental|raft|canoe|kayak|seater|privado|privada|vehículo|vehiculo|grupo|grupos|nights?|berth|capacity|hasta \d+"
                   r"|groep|groepen|privé|prive|priv[ée]-?tour|boot|sloep|bootje|rondvaartboot|huur|verhuur|koppel|stel|gezelschap|hele boot|per boot|personen|persons|pessoas|tafel|kamer|kajak|kano"
                   r"|" + WORDNUM + r"\s*(people|persons|ppl|pax|guests|players|riders|passengers|adults|students|pasajeros|personas|personen|pessoas|gasten|deelnemers|volwassenen)|up to \d+|tot \d+|max(?:imaal|imum)?\.? ?\d+)\b", re.I)
BASE_WORDS = r"adult|adults|person|per person|personen|standard|general|guest|guests|visitor|participant|passenger|rider|player|ticket|seat|single|individual|one person|1 person|per seat|volwassene|volwassenen|volwassen|persoon|per persoon|deelnemer|passagier|bezoeker|adulto|adultos|erwachsene|erwachsener|regular|normaal|normal"
BASE = re.compile(r"\b(" + BASE_WORDS + r")\b", re.I); BASE_HEAD = re.compile(r"^(" + BASE_WORDS + r")\b", re.I)
BASE_AGE = re.compile(r"^\s*(1[0-9]|[2-5][0-9])\s*(years?|yrs?|jaar|y\.?o\.?)?\s*(and (up|over|older)|en ouder|of ouder|\+|plus)\b", re.I)
CUSTOMER_HEAD = re.compile(r"^(adult|adults|person|persons|personen|persoon|volwassene|volwassenen|standard|general|guest|guests|visitor|participant|passenger|rider|player|adulto|adultos|erwachsene|regular|normaal|normal|deelnemer|individual|single|seat|\d{1,2}\s*(years?|yrs?|jaar)?\s*(and up|and over|\+|en ouder))\b", re.I)
PER_PERSON = re.compile(r"\b(per (person|player|participant|head|adult|guest|rider|passenger|student|pp|persoon|deelnemer))\b|\beach person\b|\bpp\b|\bp\.p\.|\bprijs per persoon\b|\b(1|one|een|één) (person|student|player|persoon)\b(?!\s*(or|to|-|–|of|tot))", re.I)
ADDON_SELF = re.compile(r"per additional|\bprice per item\b|\bper extra persoon\b|\bprijs per item\b", re.I)
ADDON_LABEL = re.compile(r"\badditional\b|\bextra\b|\badd[- ]?on\b|\bsupplement\b|\btoeslag\b|\bbijboeking\b|^add (a|an|the)\b|\boptional\b|\bupgrade\b|aggiuntiv[oa]|\badicional", re.I)
VOLUME = re.compile(r"^(" + WORDNUM + r"\s*(or more|of meer|\+)?\s*(people|persons|adults|guests|players|passengers|students|personen|gasten|volwassenen)|groups? of|groep(?:en)? van|([2-9]|\d{2,})\s*(-|–|to|\+|tot)\s*\d*\s*(people|persons|adults|guests|players|passengers|students|personen|gasten))\b", re.I)
NAME_GROUP = re.compile(r"\b(hire|rental|charter|private|boat|narrowboat|cruiser|vessel|huur|verhuur|privé|prive|boot|sloep|rondvaart|cruise)\b", re.I)

def classify(t, product_name):
    sing = (t.get('singular') or '').strip(); note = t.get('note') or ''
    sing_f, note_f = fold(sing), fold(note)
    if not (t.get('priceCents') or 0) > 0: return 'zero'
    if NEVER.search(sing) or NEVER.search(sing_f) or AGE_RANGE.search(sing) or AGE_RANGE.search(sing_f): return 'never'
    if ADDON_SELF.search(note) or ADDON_SELF.search(note_f): return 'never'
    if VOLUME.search(sing): return 'group'
    if BASE_HEAD.search(sing) or BASE_AGE.search(sing): return 'base'
    if BASE.search(sing) and not GROUP.search(sing): return 'base'
    if PER_PERSON.search(note): return 'base' if GROUP.search(sing) else 'unnamed'
    if GROUP.search(sing) or GROUP.search(note): return 'group'
    if NAME_GROUP.search(product_name or ''): return 'group'
    return 'unnamed'
def classify_ladder(tiers, product_name):
    cl = [(x, classify(x, product_name)) for x in tiers]
    if sum(1 for x, c in cl if c in ('base', 'group') and PARTY_BAND.search(x.get('singular') or '')) >= 2:
        cl = [(x, ('unnamed' if c in ('group', 'base') and not PARTY_BAND.search(x.get('singular') or '') and not CUSTOMER_HEAD.search(x.get('singular') or '') else c)) for x, c in cl]
    explicit = any(c in ('base', 'group') for _, c in cl)
    return [(x, ('base' if c == 'unnamed' and not explicit else c)) for x, c in cl]
PARTY_BAND = re.compile(WORDNUM + r"\s*(or more|of meer|\+)?\s*(people|person|persons|persoon|personen|personas|pessoas|guests|pax|gasten|adults|volwassenen|players|passengers|deelnemers)\b|\b(groups? of|groep(?:en)? van|grupos? de|grupo privado|up to \d|tot \d|max(?:imaal|imum)?\.? ?\d|vanaf \d|from \d)", re.I)

WORD2N = dict(two=2, three=3, four=4, five=5, six=6, seven=7, eight=8, nine=9, ten=10, twelve=12, twee=2, drie=3, vier=4, vijf=5, zes=6, zeven=7, acht=8, negen=9, tien=10, twaalf=12)
AGE_PHRASE = re.compile(r"\b\d{1,2}\s*(?:-|–|to|t/m|tot)?\s*\d{0,2}\s*(years?|yrs?|jaar|jr|y\.?o\.?)\b(\s*(and (up|over|older)|en ouder|of ouder|olds?|\+))?|\b\d{1,2}\s*\+(?!\s*(people|persons|personen|guests|pax))|\bages?\s*\d{1,2}(\s*(-|–|to|and|&)\s*(\d{1,2}|under|up|over))?", re.I)
DURATION = re.compile(r"\b\d{1,3}([.,]\d+)?\s*(hours?|hrs?|hr|h|uur|uren|minutes?|mins?|min|days?|dag|dagen|nights?|nachten?|weeks?|weken)\b", re.I)
def band_size(label):
    label = AGE_PHRASE.sub(' ', DURATION.sub(' ', label))
    m = re.search(r"\b(\d{1,3})\s*(?:-|–|to|tot)\s*(\d{1,3})\b", label)
    if m: return int(m.group(2))
    m = re.search(r"\b(\d{1,3})\b", label)
    if m: return int(m.group(1))
    m = re.search(r"\b(" + "|".join(WORD2N) + r")\b", label, re.I)
    return WORD2N[m.group(1).lower()] if m else None
CAP = re.compile(r"((?:up to|maximum(?: of)?|max(?:imum|imaal)?\.?|maximaal|tot|voor maximaal|for up to|space for(?: up to)?|accommodates(?: up to)?|seats(?: up to)?|no more than)\s*(\d{1,3})\s*(guests|passengers|people|persons|pax|gasten|passagiers|personen|mensen|deelnemers))", re.I)
SIZE_OR_DUR = re.compile(r"\d|" + "|".join(WORD2N) + r"|\b(hour|hours|uur|minute|minutes|min|day|days|dag|dagen|half)\b", re.I)
NAME_BAND = re.compile(r"((?:\d{1,3})\s*(?:-|–|to|tot)\s*(\d{1,3})\s*(people|persons|personen|guests|pax|pers\.?|passengers|gasten))", re.I)
def unit_for_group(anchor_label, t):
    if SIZE_OR_DUR.search(anchor_label): return anchor_label, 'tier label verbatim'
    name = t.get('name') or ''
    m = NAME_BAND.search(name) or CAP.search(name)
    if m:
        n = m.group(2); noun = (m.group(3)).lower()
        return f"per group, up to {n} {noun}", f'product name quoted: "{m.group(1)}"'
    if RENTAL_NAME.search(name): return anchor_label, 'tier label verbatim'
    m = CAP.search(t.get('description') or '')
    if m:
        noun = 'boat' if re.search(r"boat|boot|sloep|cruise|rondvaart|vaartocht", t.get('name') or '', re.I) else 'group'
        return f"per {noun}, up to {m.group(2)} {m.group(3).lower()}", f'description quoted: "{m.group(1)}"'
    return anchor_label, 'tier label verbatim'
def r1_ladder(base, group):
    if any((band_size(x['singular']) or 1) != 1 for x in base): return None
    sized = [(x, band_size(x['singular'])) for x in group]
    if not sized or any(not n or n < 2 for _, n in sized): return None
    by_n = {}
    for x, n in sized: by_n.setdefault(n, []).append(x)
    seq = [(1, min(x['priceCents'] for x in base))] + [(n, min(x['priceCents'] for x in xs)) for n, xs in sorted(by_n.items())]
    if not all(b[1] < a[1] for a, b in zip(seq, seq[1:])): return None
    n = seq[-1][0]; return n, min(by_n[n], key=lambda x: x['priceCents'])
COUPLE = re.compile(r"\b(koppel|couple|couples|for two|for 2|twee personen|two persons|2 persons|2 people|two people)\b", re.I)
def hybrid_couple(base, group):
    couples = [x for x in group if COUPLE.search(x['singular'])]
    if not couples or not base: return None
    if all((band_size(x['singular']) or 1) >= 3 for x in base): return min(couples, key=lambda x: x['priceCents'])
    return None
def fmt(tiers): return ' / '.join(f"{x['singular']} €{u(x['priceCents'])}" for x in tiers if x['priceCents'] > 0)

# ---- main ----
before = {t['pk']: hashlib.sha256(json.dumps(t, sort_keys=True, ensure_ascii=False).encode()).hexdigest() for t in rows}
pop_set = {t['pk'] for t in pop}
summary = []; disp = collections.Counter(); anchor_changes = []; sweep_hits = []
for t in pop:
    p = probe['perPk'][str(t['pk'])]
    old = dict(price=t.get('price'), label=t.get('priceLabel'), conf=t.get('priceConfidence'))
    rec = dict(pk=t['pk'], name=t['name'], old=old['price'], oldLabel=old['label'])
    t['priceSource'] = SOURCE; t['priceVerifiedAt'] = STAMP_DAY
    if p.get('error') or p.get('absent') or not p.get('tiers'):
        why = f"probe error ({p['error']})" if p.get('error') else "item absent from undated price-preview items[]"
        stored = 'null' if old['price'] is None else f"€{old['price']}"
        t['priceBasis'] = f"UNSAMPLED: {why}; stored {stored}{f' ({old['label']})' if old['label'] else ''} retained, unverified; priceConfidence {old['conf']}->low until sampled (WENG #88: an unverifiable figure never emits an offer)"
        t['priceTiers'] = []; t['priceConfidence'] = 'low'
        rec.update(disposition='UNSAMPLED', new=old['price']); disp['UNSAMPLED'] += 1; summary.append(rec); continue
    tiers = p['tiers']; cur = p.get('liveCurrency')
    t['priceTiers'] = [dict(singular=c.get('singular'), plural=c.get('plural'), note=c.get('note') or '', priceCents=c.get('priceCents'), price=u(c['priceCents']), minPartySize=c.get('min')) for c in tiers]
    evid = f"1/1 live reading (undated, start_at {p.get('start_at')})"
    classes = classify_ladder(tiers, t['name']); rec['tiers'] = [dict(singular=x['singular'], note=x.get('note') or '', price=u(x['priceCents']), min=x.get('min'), cls=c) for x, c in classes]
    base = [x for x, c in classes if c == 'base']; group = [x for x, c in classes if c == 'group']; nz = [x for x in tiers if x['priceCents'] > 0]
    never_nz = [x for x, c in classes if c == 'never' and x['priceCents'] > 0]
    cheapest = lambda xs: min(xs, key=lambda x: x['priceCents'])
    skipped = lambda: ', '.join(f"{x['singular']} €{u(x['priceCents'])} [{c}]" for x, c in classes if c != 'base' and x['priceCents'] > 0)
    def release(anchor, unit, rule, basis):
        t['currency'] = 'EUR'; t['price'] = u(anchor['priceCents']); t['priceLabel'] = anchor['singular']; t['priceConfidence'] = 'high'
        t['priceBasis'] = basis
        if unit: t.setdefault('_unknownFields', {})['priceUnit'] = unit
        if ADDON_LABEL.search(anchor['singular']) or ADDON_SELF.search(anchor.get('note') or ''): sweep_hits.append((t['pk'], anchor['singular'], anchor.get('note')))
        changed = old['price'] != t['price']
        if changed: anchor_changes.append(dict(pk=t['pk'], name=t['name'], old=old['price'], new=t['price'], rule=rule, label=anchor['singular']))
        d = f"{rule}:{'repriced' if changed else 'unchanged'}"
        rec.update(disposition=d, rule=rule, new=t['price'], label=anchor['singular'], unit=unit); disp[d] += 1
    # WPR network ruling (this session): on a course/certification-shaped product, a "student" tier that
    # is the sole way to purchase the item's own named product is sole-audience, not never-anchor;
    # multi-band ladders anchor on the tier buying the item's named product. Two pks tested against it:
    if t['pk'] == 708352:
        # "Plastic Hunting - Secondary Schools & Students": all 3 tiers are student-labeled party-size
        # bands (25-49/50-150/151-200, min party 24 each), price falling 26.24->20.99->15.74 as the band
        # grows — the s48-R1 falling per-head shape. Sole-audience: no non-student tier exists at all, so
        # "student" does not disqualify; largest band's per-head rate anchors (s48-R1 convention).
        anchor = cheapest(tiers); unit = f"per person, {anchor['singular']}"
        release(anchor, unit, 's48-R1', f"s48-R1 per-head rate ladder, sole-audience override (WPR network ruling, this session — a course/certification-shaped product whose only purchasable tiers are student-labeled is sole-audience, not never-anchor): every tier is student-banded ({fmt(tiers)}), price per head falls as the band grows; largest band \"{anchor['singular']}\" €{u(anchor['priceCents'])} per person anchors with unit \"{unit}\"; {evid}; live EUR")
    elif t['pk'] == 669900:
        # "Bachelor Party Package" / "Bachelor Party Package XL": XL's own note is "Upgrade to 90 minutes"
        # (ADDON_LABEL match) — an explicit upgrade of the base package, not a separate base tier. No
        # non-package tier exists at all, so this is the sole-tier shape (package is the only way to
        # purchase the item's own named product), not a true add-on alongside a base tier.
        anchor = next(x for x in tiers if x['singular'] == 'Bachelor Party Package')
        release(anchor, anchor['singular'], 'single-tier', f"single-tier override (WPR network ruling, this session — sole-tier rule: package is the only way to purchase the item's own named product, not a true add-on alongside a separate base tier): \"Bachelor Party Package XL\" is an explicit upgrade of this tier (note: \"Upgrade to 90 minutes\"), not an independent tier; \"{anchor['singular']}\" €{u(anchor['priceCents'])} anchors; ladder {fmt(tiers)}; {evid}; live EUR")
    elif not nz and len(tiers) == 1:
        # Jason's ruling (2026-08-26): a single €0 tier is a price-on-request placeholder (group-size/
        # date-dependent quote), not a closed-date read — the undated per-item preview structurally
        # cannot resolve a figure for this shape. Stored price/label/confidence retained unchanged;
        # render-eligibility check confirmed priceConfidence low does not hide the card (app.js
        # formatPrice/createTourCard have no confidence-based filter), so this is stamps+evidence only.
        t['priceConfidence'] = old['conf']
        stored = 'null' if old['price'] is None else f"€{old['price']}"
        t['priceBasis'] = f"HELD (price-on-request placeholder): sole live tier \"{tiers[0]['singular']}\" ({tiers[0].get('note') or 'no note'}) reads €0 — undated per-item preview cannot quote a group-size/date-dependent product, not a closed-date read; stored {stored}{f' ({old['label']})' if old['label'] else ''} retained unchanged; {evid}; live {cur}"
        rec.update(disposition='HELD-quote', new=old['price']); disp['HELD-quote'] += 1
    elif not nz:
        t['price'] = None; t['priceLabel'] = None; t['priceConfidence'] = 'low'
        t['priceBasis'] = f"zero-base (closed date): every live tier is €0 on the undated reading ({' / '.join(x['singular'] for x in tiers)}) — no bookable availability, not a genuine €0 price; {evid}; live {cur}"
        if old['price'] is not None: anchor_changes.append(dict(pk=t['pk'], name=t['name'], old=old['price'], new=None, rule='zero-base', label=None))
        rec.update(disposition='zero-base', new=None); disp['zero-base'] += 1
    elif cur and cur != 'EUR':
        anchor = cheapest(base or nz)
        t['currency'] = cur; t['price'] = u(anchor['priceCents']); t['priceLabel'] = anchor['singular']; t['priceConfidence'] = 'low'
        t['priceBasis'] = f"HELD (D-620): live details.currency {cur} != site EUR; true amount {cur} {t['price']} ({anchor['singular']}) stamped, unpublished; {evid}"
        rec.update(disposition='D-620', new=t['price'], currency=cur); disp['D-620'] += 1
    elif base and group and hybrid_couple(base, group):
        anchor = hybrid_couple(base, group)
        release(anchor, anchor['singular'], 'D-614', f"D-614 hybrid ladder: couple tier \"{anchor['singular']}\" €{u(anchor['priceCents'])} is the smallest bookable unit and anchors with the tier label verbatim as unit; the large-group per-person tiers ({', '.join(f'{x['singular']} €{u(x['priceCents'])}' for x in base)}) do not anchor; ladder {fmt(tiers)}; {evid}; live EUR")
    elif base and group and r1_ladder(base, group):
        n, anchor = r1_ladder(base, group); unit = f"per person, {anchor['singular']}"
        release(anchor, unit, 's48-R1', f"s48-R1 per-head rate ladder (price per head falls as band grows; 1-person tier €{u(cheapest(base)['priceCents'])} is the dearest, not a From anchor): largest band \"{anchor['singular']}\" €{u(anchor['priceCents'])} per person anchors with unit \"{unit}\" (tier label verbatim, per-person prefix); ladder {fmt(tiers)}; {evid}; live EUR")
    elif base:
        anchor = cheapest(base)
        bs = band_size(anchor['singular']); unit = f"per person, {anchor['singular']}" if bs and bs >= 2 and PARTY_BAND.search(anchor['singular']) else None
        release(anchor, unit, 'D-624', f"D-624 cheapest adult/base per-person tier {anchor['singular']} €{u(anchor['priceCents'])}{f' of {len(base)} base tiers (D-625)' if len(base) > 1 else ''}{f'; unit \"{unit}\" (tier label verbatim, per-person prefix)' if unit else ''}{f'; not anchoring: {skipped()}' if skipped() else ''}; {evid}; live EUR")
    elif group and RENTAL_NAME.search(t['name']) and not ACCESSORY.search(t['name']) and not [x for x in group if not ACCESSORY.search(x['singular'])]:
        floor = cheapest(nz)
        t['currency'] = 'EUR'; t['priceConfidence'] = 'low'; t['price'] = u(floor['priceCents']); t['priceLabel'] = floor['singular']
        t['priceBasis'] = f"HELD (hire/rental rule): no non-accessory hire tier in ladder {fmt(tiers)}; floor €{t['price']} ({floor['singular']}) stamped unpublished; {evid}; live EUR"
        if old['price'] != t['price']: anchor_changes.append(dict(pk=t['pk'], name=t['name'], old=old['price'], new=t['price'], rule='HELD-hire', label=floor['singular']))
        rec.update(disposition='HELD', new=t['price'], label=floor['singular']); disp['HELD'] += 1
    elif group:
        if RENTAL_NAME.search(t['name']) and not ACCESSORY.search(t['name']): group = [x for x in group if not ACCESSORY.search(x['singular'])]
        sized = [(x, band_size(x['singular'])) for x in group]; sized = [(x, n) for x, n in sized if n]
        by_n = {}
        for x, n in sized: by_n.setdefault(n, []).append(x)
        seq = [(n, min(xs, key=lambda x: x['priceCents'])['priceCents']) for n, xs in sorted(by_n.items())]
        if len(seq) >= 2 and all(b[1] < a[1] for a, b in zip(seq, seq[1:])):
            n, _ = seq[-1]; anchor = min(by_n[n], key=lambda x: x['priceCents']); unit = f"per person, {anchor['singular']}"; src = 'tier label verbatim (per-person prefix)'
            rule = 's48-R1'; how = f"s48-R1 per-head rate ladder (price falls as band grows): largest band \"{anchor['singular']}\" €{u(anchor['priceCents'])} per person anchors with unit \"{unit}\" ({src})"
        else:
            anchor = cheapest(group); unit, src = unit_for_group(anchor['singular'], t)
            rising = len(seq) >= 2 and all(b[1] > a[1] for a, b in zip(seq, seq[1:]))
            rule = 'D-614' if (rising or len(group) > 1) else 'D-621'
            how = (f"D-614 party-total ladder (price rises with band; a total is never divided by headcount): floor tier \"{anchor['singular']}\" €{u(anchor['priceCents'])} anchors" if rising else
                   f"{'D-614 party-size ladder floor' if len(group) > 1 else 'D-621 whole-party tier'}: tier \"{anchor['singular']}\" €{u(anchor['priceCents'])} anchors") + f" with unit \"{unit}\" ({src})"
        release(anchor, unit, rule, f"{how}; no standalone adult/base per-person tier{f'; not anchoring: {skipped()}' if skipped() else ''}; ladder {fmt(tiers)}; {evid}; live EUR")
    elif len(nz) == 1 and never_nz and not ADDON_LABEL.search(nz[0]['singular']) and not ADDON_SELF.search(nz[0].get('note') or '') and not NOT_A_PRICE.search(nz[0]['singular']):
        anchor = nz[0]
        release(anchor, anchor['singular'], 'single-tier', f"single-tier product (the sole tier is the entire audience): tier \"{anchor['singular']}\" €{u(anchor['priceCents'])} anchors with the tier label verbatim as unit; {evid}; live EUR")
    else:
        floor = cheapest(nz)
        t['currency'] = 'EUR'; t['priceConfidence'] = 'low'; t['price'] = u(floor['priceCents']); t['priceLabel'] = floor['singular']
        unnamed = [x for x, c in classes if c == 'unnamed' and x['priceCents'] > 0]
        t['priceBasis'] = f"HELD (no adult/base tier): live ladder {fmt(tiers)} has no anchorable tier ({', '.join(f'{x['singular']} [never]' for x in never_nz)}{'; ' if never_nz and unnamed else ''}{', '.join(f'{x['singular']} [unnamed extra]' for x in unnamed)}); floor €{t['price']} ({floor['singular']}) stamped unpublished pending a ruling; {evid}; live EUR"
        if old['price'] != t['price']: anchor_changes.append(dict(pk=t['pk'], name=t['name'], old=old['price'], new=t['price'], rule='HELD', label=floor['singular']))
        rec.update(disposition='HELD', new=t['price'], label=floor['singular']); disp['HELD'] += 1
    summary.append(rec)
assert not sweep_hits, ('ABORT: add-on-shaped anchor tier(s)', sweep_hits)
after = {t['pk']: hashlib.sha256(json.dumps(t, sort_keys=True, ensure_ascii=False).encode()).hexdigest() for t in rows}
changed = [pk for pk in after if after[pk] != before[pk]]; outside = [pk for pk in changed if pk not in pop_set]
assert not outside and len(rows) == len(before), ('rows outside population changed', outside)
untouched = len(pop) - len(changed); assert untouched == 0, ('population rows without a fresh stamp', untouched)
out = json.dumps(doc, indent=2, ensure_ascii=False) + '\n'
result = dict(population=len(pop), rowsChanged=len(changed), untouchedInPop=untouched, disposition=dict(disp),
              probeHitCount=sum(1 for t in pop if probe['perPk'][str(t['pk'])].get('tiers')),
              unsampledCount=disp.get('UNSAMPLED', 0), anchorChanges=anchor_changes,
              sha256=dict(before=hashlib.sha256(raw).hexdigest(), after=hashlib.sha256(out.encode()).hexdigest()), summary=summary)
print(json.dumps({k: result[k] for k in ('population', 'rowsChanged', 'untouchedInPop', 'disposition', 'probeHitCount', 'unsampledCount', 'sha256')}, indent=1), 'EXECUTE' if execute else 'DRY RUN')
print(f"\nanchor changes: {len(anchor_changes)}")
for c in anchor_changes: print(' ', c)
if execute:
    open(DATA, 'w', encoding='utf-8').write(out); json.dump(result, open(f'{EV}/apply-summary.json', 'w'), indent=1, ensure_ascii=False); print('WROTE', DATA)
