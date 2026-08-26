#!/usr/bin/env python3
"""s49-wams-refresh — APPLY stage. Port of wanderengland scripts/s48-weng-refresh-b.mjs apply() +
classifyTier() with the s49 refinements from s49-weng-release.mjs / s49-weng-wave2.mjs.

WHY PYTHON (adaptation #1): tours-data.json carries Python float spellings (e.g. "price": 350.0 from
s49-wams-heldrelease-2), so JSON.stringify(doc,null,2) does NOT round-trip it (verified false). The
byte-identity guarantee on the 270 out-of-population rows therefore requires json.dumps(indent=2,
ensure_ascii=False)+'\\n', which round-trips exactly. New integral amounts are spelled as ints (num()),
matching the writer's JSON.stringify parity used since s47.

Population: rows with no priceSource (1,366 on the 2026-05-28 v7 stamp + pk 442206 unstamped).
Evidence: scripts/evidence/s49-wams-refresh/probe.json (4 dated readings per pk, see probe.mjs).

Dispositions (evidence-driven; every population row gets a fresh stamp):
  UNSAMPLED    absent on every dated probe        -> stored figure retained, low, reason stamped
  PROBE_ERROR  every probe errored                -> as UNSAMPLED, status probe_error
  zero_price   majority ladder all-zero           -> price null, low
  D-620        live currency != EUR               -> true currency + amount stamped, low
  D-624        cheapest adult/base per-person tier anchors, high (D-625: cheapest of several base tiers)
  D-614/D-621  no base tier, group tiers present  -> RELEASED here (priceUnit path is live on WAMS, unlike
               WENG s48): rising party-total ladder floor-anchors; falling per-head ladder (s48-R1) anchors on
               the largest band; otherwise floor of group tiers. Unit = tier label verbatim, or description
               "up to N <people>" quoted when the label carries no size/duration (s49 description sanction).
  single-tier  one non-zero tier, never-class, not add-on shaped -> anchors (s49 wave-2 rule)
  HELD         only never-class tiers (multi-tier) -> floor of non-zero tiers stamped, low
Final add-on sweep: a released anchor whose LABEL is add-on shaped or whose NOTE prices it "per additional"
/ "price per item" aborts the run (s49 wave-2 refinement: a note merely advertising extras does not).
Usage: python3 scripts/s49-wams-refresh-apply.py [--execute]
"""
import json, re, sys, hashlib, collections
DATA = 'tours-data.json'; EV = 'scripts/evidence/s49-wams-refresh'; SOURCE = 's49-wams-refresh'; STAMP_DAY = '2026-08-25'
execute = '--execute' in sys.argv
raw = open(DATA, 'rb').read(); doc = json.loads(raw)
assert (json.dumps(doc, indent=2, ensure_ascii=False) + '\n').encode() == raw, 'round-trip not byte-identical; refusing'
ev = json.load(open(f'{EV}/probe.json')); DATES = ev['dates']
assert not ev['reconcile']['incomplete'], 'probe incomplete'
rows = doc['tours']; pop = [t for t in rows if not t.get('priceSource')]
assert ev['population'] == len(pop) == 1367, ('population drift', ev['population'], len(pop))
assert set(map(str, (t['pk'] for t in pop))) == set(ev['perPk']), 'probe/population pk set mismatch'
# date-validity instrument (D-606): at least one start_at must move across dates for some row
assert any(len({p['start_at'] for p in v['probes'] if p.get('start_at')}) > 1 for v in ev['perPk'].values()), 'date parameter ignored'
def num(x): return int(x) if isinstance(x, float) and x.is_integer() else x
def u(c): return num(round(c / 100, 2))

# ---- tier classification (D-624 / D-625 / D-621) — WENG regexes + Dutch/ES/DE additions (adaptation #2) ----
NEVER = re.compile(r"\b(child|childs|child's|children|childrens|children's|kid|kids|kid's|infant|infants|baby|babies|toddler|junior|juniors|youth|youths|teen|teenager|teens|adolescent|adolescents|young adult|student|students|senior|seniors|oap|concession|concessions|pensioner|disabled|wheelchair|carer|companion|blue light|nhs|discount|under\s*\d+s?|\d+\s*(and|&)\s*under|family|families|bundle|package|add[- ]?on|extra(?!\s*(small|large|klein|groot|grote))|extras|additional|supplement|upgrade|gratuity|tip|tips|donation|deposit|voucher|gift card|redemption|per additional|spectator|non[- ]?participant|dog|dogs|pet|pets|kit|merchandise|parking|niño|niños|niña|niñas|nino|ninos|nina|ninas|bebé|bebe|infante|enfant|enfants|bébé|kind|kinder|bambino|bambini|neonato|neonati|ragazzo|ragazzi|ragazza|ragazze"
                   r"|kinderen|kindje|kids?tarief|peuter|peuters|baby's|jeugd|jongeren|studenten|senioren|65\+|korting|toeslag|bijboeking|extra's|optie|opties|fooi|borg|cadeaubon|hond|honden|huisdier|familie|gezin|gezinsticket|pakket|arrangement"
                   r"|joven|jóvenes|jovenes|criança|crianças|niñ[oa]s?|kinderfiets|kids? ?bike|child(?:ren'?s?)? bike|kinderzitje"
                   r"|aggiuntiv[oa]|adicional|adicionales|zusätzlich|zusätzliche|zusatzlich|zusatzliche|supplémentaire|extra persoon|bijboeken|optional|optioneel|upgrade|aanbetaling|voorschot|deposito|caparra|kaution|anzahlung"
                   r"|儿童|孩子|学生|老年|优惠)\b|^add (a|an|the)\b|儿童|孩子|学生|老年|优惠", re.I)
# tiers that are not a price at all (deposits, vouchers, gratuities): never anchor, not even as a sole tier (WAMS adaptation #4)
NOT_A_PRICE = re.compile(r"\b(deposit|deposito|borg|aanbetaling|voorschot|caparra|kaution|anzahlung|voucher|gift card|cadeaubon|donation|gratuity|tip|tips|fooi)\b", re.I)
# hire/rental accessories never anchor unless the product IS the accessory (WENG s49 hire/rental rule)
ACCESSORY = re.compile(r"\b(bag|bags|tas|lock|slot|helmet|helm|child seat|kinderzitje|zitje|seat|basket|mand|poncho|regenjas|raincoat|insurance|verzekering|boots?|gloves?|hoods?|wetsuit|trailer|fietskar|bakfiets ?zitje|kaart|map|extra[- ]person|extra participants?)\b", re.I)
RENTAL_NAME = re.compile(r"\b(hire|rental|rent|huur|verhuur|huren)\b", re.I)
AGE_RANGE = re.compile(r"\b\d{1,2}\s*(-|–|to|t/m|tot)\s*\d{1,2}\s*(yrs|rys|years|year olds|yr olds|y/o|y/old|yo|años|anos|ans|anni|jaar|jr)\b", re.I)
WORDNUM = r"(two|three|four|five|six|seven|eight|nine|ten|twelve|twee|drie|vier|vijf|zes|zeven|acht|negen|tien|twaalf|\d+)"
GROUP = re.compile(r"\b(per group|group|groups|party|parties|private|exclusive|charter|boat|vessel|vehicle|car|van|minibus|coach|table|room|cabin|pod|lane|court|couple|couples|for two|for 2|whole|hire|rental|raft|canoe|kayak|seater|privado|privada|vehículo|vehiculo|grupo|grupos|nights?|berth|capacity|hasta \d+"
                   r"|groep|groepen|privé|prive|priv[ée]-?tour|boot|sloep|bootje|rondvaartboot|huur|verhuur|koppel|stel|gezelschap|hele boot|per boot|personen|persons|pessoas|tafel|kamer|kajak|kano"
                   r"|" + WORDNUM + r"\s*(people|persons|ppl|pax|guests|players|riders|passengers|adults|students|pasajeros|personas|personen|pessoas|gasten|deelnemers|volwassenen)|up to \d+|tot \d+|max(?:imaal|imum)?\.? ?\d+)\b", re.I)
BASE_WORDS = r"adult|adults|person|per person|personen|standard|general|guest|guests|visitor|participant|passenger|rider|player|ticket|seat|single|individual|one person|1 person|per seat|volwassene|volwassenen|volwassen|persoon|per persoon|deelnemer|passagier|bezoeker|adulto|adultos|erwachsene|erwachsener|regular|normaal|normal"
BASE = re.compile(r"\b(" + BASE_WORDS + r")\b", re.I); BASE_HEAD = re.compile(r"^(" + BASE_WORDS + r")\b", re.I)
BASE_AGE = re.compile(r"^\s*(1[0-9]|[2-5][0-9])\s*(years?|yrs?|jaar|y\.?o\.?)?\s*(and (up|over|older)|en ouder|of ouder|\+|plus)\b", re.I)   # minimum-age admission tier (65+ etc. stay senior/never)
# customer-type heads that survive beside a party-size ladder; "Ticket <Museum>" / "<Attraction> Boat Tour" do not
CUSTOMER_HEAD = re.compile(r"^(adult|adults|person|persons|personen|persoon|volwassene|volwassenen|standard|general|guest|guests|visitor|participant|passenger|rider|player|adulto|adultos|erwachsene|regular|normaal|normal|deelnemer|individual|single|seat|\d{1,2}\s*(years?|yrs?|jaar)?\s*(and up|and over|\+|en ouder))\b", re.I)
PER_PERSON = re.compile(r"\b(per (person|player|participant|head|adult|guest|rider|passenger|student|pp|persoon|deelnemer))\b|\beach person\b|\bpp\b|\bp\.p\.|\bprijs per persoon\b|\b(1|one|een|één) (person|student|player|persoon)\b(?!\s*(or|to|-|–|of|tot))", re.I)
ADDON_SELF = re.compile(r"per additional|\bprice per item\b|\bper extra persoon\b|\bprijs per item\b", re.I)   # note wording that prices the tier ITSELF as an add-on (s49 wave-2)
ADDON_LABEL = re.compile(r"\badditional\b|\bextra\b|\badd[- ]?on\b|\bsupplement\b|\btoeslag\b|\bbijboeking\b|^add (a|an|the)\b|\boptional\b|\bupgrade\b|aggiuntiv[oa]|\badicional", re.I)
VOLUME = re.compile(r"^(" + WORDNUM + r"\s*(or more|of meer|\+)?\s*(people|persons|adults|guests|players|passengers|students|personen|gasten|volwassenen)|groups? of|groep(?:en)? van|([2-9]|\d{2,})\s*(-|–|to|\+|tot)\s*\d*\s*(people|persons|adults|guests|players|passengers|students|personen|gasten))\b", re.I)
NAME_GROUP = re.compile(r"\b(hire|rental|charter|private|boat|narrowboat|cruiser|vessel|huur|verhuur|privé|prive|boot|sloep|rondvaart|cruise)\b", re.I)
def classify(t, product_name):
    sing = (t.get('singular') or '').strip(); note = t.get('note') or ''
    if not (t.get('priceCents') or 0) > 0: return 'zero'
    if NEVER.search(sing) or AGE_RANGE.search(sing): return 'never'
    if ADDON_SELF.search(note): return 'never'
    if VOLUME.search(sing): return 'group'
    if BASE_HEAD.search(sing) or BASE_AGE.search(sing): return 'base'   # "14 years and up", "18+" = the general-admission tier
    if BASE.search(sing) and not GROUP.search(sing): return 'base'
    if PER_PERSON.search(note): return 'base' if GROUP.search(sing) else 'unnamed'   # a per-person note prices a party-shaped label per head; on a proper-noun label ("Delft Porcelain Museum") it is an extra
    if GROUP.search(sing) or GROUP.search(note): return 'group'
    if NAME_GROUP.search(product_name or ''): return 'group'
    return 'unnamed'   # resolved by classify_ladder(): base only when the ladder has no explicit base/group tier (WAMS adaptation #5)
def classify_ladder(tiers, product_name):
    """Two-pass: an unnamed variant ("Half Day", "20 Shots") is a per-person base tier under D-625 ONLY when nothing in the
    ladder is explicitly base or group; next to an explicit "Adult" or "Group of 1 to 3" it is an optional extra
    ("Delft Porcelain Museum", "Giethoorn Boat Tour") and is excluded from anchoring."""
    cl = [(x, classify(x, product_name)) for x in tiers]
    # a party-size ladder (≥2 tiers naming a band) makes every band-less group tier an extra ("Electric Boat Selfdrive 8 Seats"
    # beside "Group of 1 to 3 people") — WAMS adaptation #6
    if sum(1 for x, c in cl if c in ('base', 'group') and PARTY_BAND.search(x.get('singular') or '')) >= 2:
        cl = [(x, ('unnamed' if c in ('group', 'base') and not PARTY_BAND.search(x.get('singular') or '') and not CUSTOMER_HEAD.search(x.get('singular') or '') else c)) for x, c in cl]
    explicit = any(c in ('base', 'group') for _, c in cl)
    return [(x, ('base' if c == 'unnamed' and not explicit else c)) for x, c in cl]
PARTY_BAND = re.compile(WORDNUM + r"\s*(or more|of meer|\+)?\s*(people|person|persons|persoon|personen|personas|pessoas|guests|pax|gasten|adults|volwassenen|players|passengers|deelnemers)\b|\b(groups? of|groep(?:en)? van|grupos? de|grupo privado|up to \d|tot \d|max(?:imaal|imum)?\.? ?\d|vanaf \d|from \d)", re.I)

# ---- s49 unit derivation for group anchors ----
WORD2N = dict(two=2, three=3, four=4, five=5, six=6, seven=7, eight=8, nine=9, ten=10, twelve=12, twee=2, drie=3, vier=4, vijf=5, zes=6, zeven=7, acht=8, negen=9, tien=10, twaalf=12)
AGE_PHRASE = re.compile(r"\b\d{1,2}\s*(?:-|–|to|t/m|tot)?\s*\d{0,2}\s*(years?|yrs?|jaar|jr|y\.?o\.?)\b(\s*(and (up|over|older)|en ouder|of ouder|olds?|\+))?|\b\d{1,2}\s*\+(?!\s*(people|persons|personen|guests|pax))|\bages?\s*\d{1,2}(\s*(-|–|to|and|&)\s*(\d{1,2}|under|up|over))?", re.I)
DURATION = re.compile(r"\b\d{1,3}([.,]\d+)?\s*(hours?|hrs?|hr|h|uur|uren|minutes?|mins?|min|days?|dag|dagen|nights?|nachten?|weeks?|weken)\b", re.I)
def band_size(label):
    label = AGE_PHRASE.sub(' ', DURATION.sub(' ', label))   # "Private VIP Charter • 3 Hours" / "14 years and up" carry no party size
    m = re.search(r"\b(\d{1,3})\s*(?:-|–|to|tot)\s*(\d{1,3})\b", label)
    if m: return int(m.group(2))
    m = re.search(r"\b(\d{1,3})\b", label)   # first number wins ("1 person (age 5+)" → 1; "10+ persons" → 10)
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
    if m:   # s49 wave-2: unit from the product name quoted verbatim
        n = m.group(2); noun = (m.group(3)).lower()
        return f"per group, up to {n} {noun}", f'product name quoted: "{m.group(1)}"'
    if RENTAL_NAME.search(name): return anchor_label, 'tier label verbatim'   # a rental's description capacity is not its unit
    m = CAP.search(t.get('description') or '')
    if m:
        noun = 'boat' if re.search(r"boat|boot|sloep|cruise|rondvaart|vaartocht", t.get('name') or '', re.I) else 'group'
        return f"per {noun}, up to {m.group(2)} {m.group(3).lower()}", f'description quoted: "{m.group(1)}"'
    return anchor_label, 'tier label verbatim'

def r1_ladder(base, group):
    """Per-head sliding ladder: every base tier is a 1-person tier, every group tier carries a band size ≥ 2, and the
    per-head price strictly FALLS from the 1-person tier through the bands. Returns (n, anchor tier of the largest band) or None."""
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
    """s48 WAMS ruling (D-614, pks 453211/508139/619538): hybrid ladder — a couple tier plus per-person tiers that exist only
    for large bands. The couple tier is the smallest bookable unit and anchors; the large-group per-person tiers do not."""
    couples = [x for x in group if COUPLE.search(x['singular'])]
    if not couples or not base: return None
    if all((band_size(x['singular']) or 1) >= 3 for x in base): return min(couples, key=lambda x: x['priceCents'])
    return None
def fmt(tiers): return ' / '.join(f"{x['singular']} €{u(x['priceCents'])}" for x in tiers if x['priceCents'] > 0)
def key(p): return json.dumps([[x['singular'], x['priceCents']] for x in p['tiers']])
before = {t['pk']: hashlib.sha256(json.dumps(t, sort_keys=True, ensure_ascii=False).encode()).hexdigest() for t in rows}
pop_set = {t['pk'] for t in pop}
ts = f"{STAMP_DAY}T{__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(timespec='milliseconds')[11:23]}Z"
summary = []; disp = collections.Counter(); sweep_hits = []
for t in pop:
    v = ev['perPk'][str(t['pk'])]; ok = [p for p in v['probes'] if not p['error']]; sampled = [p for p in ok if not p['absent']]
    old = dict(price=t.get('price'), label=t.get('priceLabel'), conf=t.get('priceConfidence'))
    rec = dict(pk=t['pk'], name=t['name'], old=old['price'], oldLabel=old['label'])
    t['priceSource'] = SOURCE; t['priceEnrichmentSource'] = 'extract-prices-v7-api'; t['priceEnrichmentAt'] = ts; t['priceVerifiedAt'] = STAMP_DAY
    if t.get('_unknownFields') and 'priceUnit' in t['_unknownFields']: del t['_unknownFields']['priceUnit']
    if not sampled:
        d = 'UNSAMPLED' if ok else 'PROBE_ERROR'
        t['priceConfidence'] = 'low'; t['priceEnrichmentStatus'] = 'unsampled' if ok else 'probe_error'
        stored = 'null' if old['price'] is None else f"€{old['price']}"
        t['priceBasis'] = f"UNSAMPLED: absent from price-preview items[] on {len(ok)}/{len(DATES)} dated probes ({', '.join(DATES)}){f', {len(DATES)-len(ok)} probe error(s)' if len(ok) < len(DATES) else ''}; stored {stored}{f' ({old['label']})' if old['label'] else ''} retained unpublished pending a live reading"
        t['priceTiers'] = [dict(singular=x.get('singular'), plural=x.get('plural'), note=x.get('note') or '', priceCents=x.get('priceCents'), price=x.get('price'), minPartySize=x.get('minPartySize')) for x in (t.get('priceBreakdown') or [])]
        rec.update(disposition=d, new=t.get('price'), probeErrors=[p['error'] for p in v['probes'] if p['error']]); disp[d] += 1; summary.append(rec); continue
    counts = collections.Counter(key(p) for p in sampled); maj_key = counts.most_common(1)[0][0]; maj = next(p for p in sampled if key(p) == maj_key)
    valid = sum(1 for p in sampled if p.get('dateValid')); evid = f"{len(sampled)}/{len(DATES)} dated readings ({valid} date-valid), {len(counts)} ladder shape(s)"
    cur = maj['liveCurrency']; tiers = maj['tiers']
    t['priceBreakdown'] = [dict(id=c['id'], singular=c['singular'], plural=c['plural'], note=c['note'], priceCents=c['priceCents'], price=u(c['priceCents']), minPartySize=c['min']) for c in tiers]
    t['priceIncludesBookingFees'] = maj['includeFees']; t['priceIncludesTaxes'] = maj['includeTaxes']
    t['priceTiers'] = [dict(singular=c['singular'], plural=c['plural'], note=c['note'] or '', priceCents=c['priceCents'], price=u(c['priceCents']), minPartySize=c['min']) for c in tiers]
    classes = classify_ladder(tiers, t['name']); rec['tiers'] = [dict(singular=x['singular'], note=x.get('note') or '', price=u(x['priceCents']), min=x.get('min'), cls=c) for x, c in classes]
    base = [x for x, c in classes if c == 'base']; group = [x for x, c in classes if c == 'group']; nz = [x for x in tiers if x['priceCents'] > 0]
    never_nz = [x for x, c in classes if c == 'never' and x['priceCents'] > 0]
    cheapest = lambda xs: min(xs, key=lambda x: x['priceCents'])
    skipped = lambda: ', '.join(f"{x['singular']} €{u(x['priceCents'])} [{c}]" for x, c in classes if c != 'base' and x['priceCents'] > 0)
    def release(anchor, unit, rule, basis):
        t['currency'] = 'EUR'; t['price'] = u(anchor['priceCents']); t['priceLabel'] = anchor['singular']; t['priceConfidence'] = 'high'; t['priceEnrichmentStatus'] = 'high'
        t['priceBasis'] = basis
        if unit: t.setdefault('_unknownFields', {})['priceUnit'] = unit
        if ADDON_LABEL.search(anchor['singular']) or ADDON_SELF.search(anchor.get('note') or ''): sweep_hits.append((t['pk'], anchor['singular'], anchor.get('note')))
        changed = old['price'] != t['price']; d = f"{rule}:{'repriced' if changed else 'unchanged'}"
        rec.update(disposition=d, rule=rule, new=t['price'], label=anchor['singular'], unit=unit); disp[d] += 1
    if not nz:
        t['price'] = None; t['priceLabel'] = None; t['priceConfidence'] = 'low'; t['priceEnrichmentStatus'] = 'zero_price'; t['currency'] = 'EUR' if cur == 'EUR' else t.get('currency')
        t['priceBasis'] = f"zero_price: every live tier is €0 on the majority reading ({' / '.join(x['singular'] for x in tiers)}); {evid}; live {cur}"
        rec.update(disposition='zero_price', new=None); disp['zero_price'] += 1
    elif cur != 'EUR':
        anchor = cheapest(base or nz)
        t['currency'] = cur; t['price'] = u(anchor['priceCents']); t['priceLabel'] = anchor['singular']; t['priceConfidence'] = 'low'; t['priceEnrichmentStatus'] = f"non_eur_currency:{cur}"
        t['priceBasis'] = f"HELD (D-620): live details.currency {cur} ≠ site EUR; true amount {cur} {t['price']} ({anchor['singular']}) stamped, unpublished; {evid}"
        rec.update(disposition='D-620', new=t['price'], currency=cur); disp['D-620'] += 1
    elif base and group and hybrid_couple(base, group):
        anchor = hybrid_couple(base, group)
        release(anchor, anchor['singular'], 'D-614', f"D-614 hybrid ladder (s48 WAMS ruling on this shape): couple tier \"{anchor['singular']}\" €{u(anchor['priceCents'])} is the smallest bookable unit and anchors with the tier label verbatim as unit; the large-group per-person tiers ({', '.join(f'{x['singular']} €{u(x['priceCents'])}' for x in base)}) do not anchor; ladder {fmt(tiers)}; {evid}; live EUR")
    elif base and group and r1_ladder(base, group):
        # s48-R1 (WAMS ruling, adaptation #3 vs WENG's s47 closure): per-head sliding ladder — "1 Person" is the
        # dearest per-head figure, not a "From" anchor; the LARGEST band's per-person figure anchors.
        n, anchor = r1_ladder(base, group); unit = f"per person, {anchor['singular']}"
        release(anchor, unit, 's48-R1', f"s48-R1 per-head rate ladder (price per head falls as band grows; 1-person tier €{u(cheapest(base)['priceCents'])} is the dearest, not a From anchor): largest band \"{anchor['singular']}\" €{u(anchor['priceCents'])} per person anchors with unit \"{unit}\" (tier label verbatim, per-person prefix); ladder {fmt(tiers)}; {evid}; live EUR")
    elif base:
        anchor = cheapest(base)
        # a per-person tier restricted to a band ("Besloten groep 50+ personen", per-person note) carries its band as unit (label verbatim)
        bs = band_size(anchor['singular']); unit = f"per person, {anchor['singular']}" if bs and bs >= 2 and PARTY_BAND.search(anchor['singular']) else None
        release(anchor, unit, 'D-624', f"D-624 cheapest adult/base per-person tier {anchor['singular']} €{u(anchor['priceCents'])}{f' of {len(base)} base tiers (D-625)' if len(base) > 1 else ''}{f'; unit \"{unit}\" (tier label verbatim, per-person prefix)' if unit else ''}{f'; not anchoring: {skipped()}' if skipped() else ''}; {evid}; live EUR")
    elif group and RENTAL_NAME.search(t['name']) and not ACCESSORY.search(t['name']) and not [x for x in group if not ACCESSORY.search(x['singular'])]:
        floor = cheapest(nz)
        t['currency'] = 'EUR'; t['priceConfidence'] = 'low'; t['priceEnrichmentStatus'] = 'high'; t['price'] = u(floor['priceCents']); t['priceLabel'] = floor['singular']
        t['priceBasis'] = f"HELD (hire/rental rule): no non-accessory hire tier in ladder {fmt(tiers)}; floor €{t['price']} ({floor['singular']}) stamped unpublished; {evid}; live EUR"
        rec.update(disposition='HELD', new=t['price'], label=floor['singular']); disp['HELD'] += 1
    elif group:
        if RENTAL_NAME.search(t['name']) and not ACCESSORY.search(t['name']): group = [x for x in group if not ACCESSORY.search(x['singular'])]   # accessories never anchor a hire
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
        release(anchor, anchor['singular'], 'single-tier', f"single-tier product (s49 wave-2 rule: the sole tier is the entire audience): tier \"{anchor['singular']}\" €{u(anchor['priceCents'])} anchors with the tier label verbatim as unit; {evid}; live EUR")
    else:
        floor = cheapest(nz)
        t['currency'] = 'EUR'; t['priceConfidence'] = 'low'; t['priceEnrichmentStatus'] = 'high'; t['price'] = u(floor['priceCents']); t['priceLabel'] = floor['singular']
        unnamed = [x for x, c in classes if c == 'unnamed' and x['priceCents'] > 0]
        t['priceBasis'] = f"HELD (no adult/base tier): live ladder {fmt(tiers)} has no anchorable tier ({', '.join(f'{x['singular']} [never]' for x in never_nz)}{'; ' if never_nz and unnamed else ''}{', '.join(f'{x['singular']} [unnamed extra]' for x in unnamed)}); floor €{t['price']} ({floor['singular']}) stamped unpublished pending a ruling; {evid}; live EUR"
        rec.update(disposition='HELD', new=t['price'], label=floor['singular']); disp['HELD'] += 1
    summary.append(rec)
assert not sweep_hits, ('ABORT: add-on-shaped anchor tier(s)', sweep_hits)
after = {t['pk']: hashlib.sha256(json.dumps(t, sort_keys=True, ensure_ascii=False).encode()).hexdigest() for t in rows}
changed = [pk for pk in after if after[pk] != before[pk]]; outside = [pk for pk in changed if pk not in pop_set]
assert not outside and len(rows) == len(before), ('rows outside population changed', outside)
untouched = len(pop) - len(changed); assert untouched == 0, ('population rows without a fresh stamp', untouched)
out = json.dumps(doc, indent=2, ensure_ascii=False) + '\n'
result = dict(stampedAt=ts, population=len(pop), rowsChanged=len(changed), untouchedInPop=untouched, disposition=dict(disp),
              sha256=dict(before=hashlib.sha256(raw).hexdigest(), after=hashlib.sha256(out.encode()).hexdigest()), summary=summary)
print(json.dumps({k: result[k] for k in ('stampedAt', 'population', 'rowsChanged', 'untouchedInPop', 'disposition', 'sha256')}, indent=1), 'EXECUTE' if execute else 'DRY RUN')
if execute:
    open(DATA, 'w', encoding='utf-8').write(out); json.dump(result, open(f'{EV}/apply-summary.json', 'w'), indent=1, ensure_ascii=False); print('WROTE', DATA)
elif __import__('os').environ.get('DRY_OUT'):
    json.dump(result, open(__import__('os').environ['DRY_OUT'], 'w'), indent=1, ensure_ascii=False)
