# s47 — WAMS legacy priced rows: v7 provenance backfill — 2026-08-24 — base origin/main e0b890e (#91; rebased from 819cd96, no conflicts)

## Recon (served bytes, no writes)
- Served `tours-data.json` sha256 `5fafd5e9…631d28` == disk at origin/main 819cd96 (curl; Chrome extension disconnected).
- Legacy unstamped priced rows (price>0, no `priceEnrichmentSource`/`priceSource`/`priceVerifiedAt`): **267** (task said 268, Δ −1);
  of those emitting JSON-LD offers (priceConfidence ≠ low): **142** (task said 143, Δ −1). Stored: all `int` prices, all `currency:"EUR"`.
- Shortname/pk parsed from every `bookingUrl` (writer's own `parseFhUrl`): **267 reachable candidates, 0 malformed/missing**, 56 shortnames, 0 pk↔URL mismatches.
- The one remaining priced row without a top-level stamp is pk 442206, which carries `_unknownFields.priceSource: "v52-dominant-gate"` — stamped by an earlier pass, outside this population.

## Method (WNZ #106 scratch-clone pattern, writer unedited)
- Writer: tracked `scripts/extract-prices-v7-api.js`, sha256 `584e1463…` — identical to WNZ/WPR's vendored copy. **No writer edits.**
- Scoping by data prep: the 267 rows cloned into a scratch file with `price:null` (wrapper preserved); writer run on that file with the
  `fetch-tee.js` preload → `api-responses.ndjson` (every raw response). Results merged back by pk in one write (`apply-legacy-enrich.py`).
- Pass 1 (`--batch 20`, `pass1-run.log`): 267/267 processed, 59 requests, 203 s. 161 high / 52 zero_price / 43 none / **11 error** —
  all 11 = the writer's 15 s timeout, all on ONE operator (pureboats, its entire batch). Timeouts clustered on a single operator, not the
  population → bounded retry, not a shrink.
- Pass 2 (`--batch 4`, the 11 pureboats rows only, `pass2-retry.log`): 11/11 high, 3 requests, 0 errors. Final: 0 error rows; the
  merge script asserts this and aborts otherwise.
- Live `details.currency` recorded per response: **EUR for all 56 operators / 60 responses (all HTTP 200)** → 0 D-620 rows.
- Dead verdicts: **none issued.** Every shortname referenced by a `none` row returned HTTP 200 with live EUR; 15 of the 19 have other
  items priced in this run. Item absent from an undated price-preview = UNSAMPLED (no current availability), not dead.
- D-606: undated calls, so each item's `availability.start_at` is the anchor and is recorded per row in `obs-legacy-enrich.json`
  and in `priceSource`; no requested-date ≠ start_at FALLBACK condition arises for undated calls.
- $0 tiers recorded in `priceBreakdown`, never counted (writer's D-575 rule).

## Ruling stage (post-writer, from the live ladder; `apply-legacy-enrich.py` derives and prints it)
- **R1 child-anchor** (WHAW s45 precedent, as #90 applied): writer's first-positive tier was a child/combo tier on 3 rows →
  635425 re-anchored Child 83.93 → Person 125.90; 594114 re-anchored "Volwassene + Kind in fietszitje" 44.61 → Adult 36.74;
  592154 held (only Child and Private-Group tiers, no adult per-seat tier).
- **R2 whole-group anchor**: anchor tier prices a boat/party/charter/couple ("Boat Lucy 90 Minutes · max 6 people", "Price per group",
  "Prijs per koppel", "Private tour 1-4 persons", …) → #90's HELD class. This base has no priceUnit render path, so held low with the
  true amount + full ladder in `priceBasis`; **release candidates once #91 lands** (several notes carry a cap for the unit string).
- **R3 party-size sliding ladder** ("1 Person 572.40 / 2 People 312.70 / … / 6 People 139.92"): the writer's first tier is the dearest
  seat, not a "From" anchor → held low with the ladder stamped, pending a ruling on the "From" semantic for sliding ladders.
- Per-seat tiers with a headcount minimum ("Adult · Minimum 10 people", "Vanaf 10 personen", Dutch "personen") stay high.

## Disposition (267)
| disposition | rows | effect |
|---|---|---|
| high (writer anchor) | 136 | live float price + label + breakdown + v7 stamp set, priceConfidence high |
| high (re-anchored, R1) | 2 | as above, adult/per-person tier |
| held whole-group / sliding (R2/R3) | 34 | true amount + ladder stamped, priceConfidence **low**, no offer |
| zero_price (live ladder $0-only) | 52 | stored figure retained, contradicted by live preview → **low**, $0 ladder recorded |
| unsampled (`none`) | 43 | stored figure + stamps retained, stamped UNSAMPLED, priceConfidence **low** until sampled (WENG #88: an unverifiable figure never emits an offer; JSON-LD is the highest-exposure surface) |

Confidence moves (stored→post): high→high 85 · low→high 53 · **high→low 19** · **medium→low 38** · low→low 72 · medium→high 0.
(amendment: the 23 unsampled rows that previously kept high/medium now move to low — 8+11 high→low, 26+12 medium→low.)
Of the 138 high rows, stored == live on 9; 129 changed (max |Δ| €313.26, pk 577238 350 → 36.74 "Adult").

## Gates (`render-gate.js`, node vm over `createTourCard` on every row; base e0b890e includes #91's 2 released rows)
| run | visible `From €` | offers |
|---|---|---|
| pre (origin/main e0b890e) | 844 | 844 ✔ |
| post | 840 | 840 ✔ |
Rows whose rendered HTML changed: **187**, **0 outside the population**; #91's rows 662825/699480 byte-identical. Population offers 142 → 138
(the 138 high rows are the only emitters; every held / zero_price / unsampled row is suppressed).

## Integrity
- Round-trip `json.dumps(indent=2, ensure_ascii=False)+'\n'` asserted byte-identical before write; 1,370 other rows asserted unchanged (incl. #91's two).
- Int/float: writer's `centsToDollars` floats spelled as ints when integral (JSON.stringify parity); every `priceCents` is int and
  equals round(price×100) on high rows. Row count 1637 unchanged.
