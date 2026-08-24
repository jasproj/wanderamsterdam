# s47 — WAMS priceUnit render path + release of the 2 HELD whole-group rows — 2026-08-24 — base origin/main 819cd96 (#90)

## Recon (no writes)
- `git remote -v` → jasproj/wanderamsterdam ✔. Local main == origin/main == 819cd96 (#90); delta 0.
- Served `https://wanderamsterdam.com/tours-data.json` sha256 `5fafd5e9…631d28` == disk at tip ✔ (curl; Chrome extension disconnected).
- Reference: wandernewzealand #108 (833a9b6) `priceUnit()` + card `<small>` + `.tour-price small`, which is itself a verbatim port of keywestsandbartours (KWST not checked out locally; WNZ's header records the provenance). Explicit `_unknownFields.priceUnit` only — **no priceLabel word-inference fallback** (FST's defect variant rejected).
- HELD pair re-derived from served bytes: paynehurdstours pk **662825** (997.11 EUR) and **699480** (524.79 EUR) — the only rows at `priceConfidence: low` whose sole positive tier is `"Group"` / `"Price per group."`. Delta vs task expectation: 0.
- Party-size evidence (#90 `live-readings-2026-08-25-anchor.json`): tier note is exactly "Price per group.", `min_party_size 1`, `high: null` on every reading, and **no** `capacity`/`max_party`/`maximum` key anywhere in the bundle → no cap exists → unit string is **"per group"** (not "whole group · up to N").
- Currency: stored `EUR`; #90 `liveDetails` for both pks = `{"currency":"EUR"}` live → JSON-LD's hard-coded `priceCurrency: "EUR"` is correct for these rows. Asserted in the apply script before release.
- Other rows the new path would affect: rows carrying `_unknownFields.priceUnit` before this pass = **0** (the one existing `_unknownFields` row, pk 442206, carries only `priceSource`). Delta 0.

## Write
- `app.js`: `priceUnit(tour)` (explicit field only) + `unitHtml` `<small>` inside `.tour-price`. `formatPrice()` and `generateTourSchema()` untouched.
- `styles.css`: `.tour-price small` rule; 0 `.tour-price small` matches in tracked HTML, so nothing already shipped is restyled.
- `tours-data.json` via `apply-priceunit.py --execute` (deterministic, asserts against #90 readings: 16/16 date-valid readings agree per row, live currency EUR, int `priceCents` == float `price`×100). Per released row ONLY: `_unknownFields.priceUnit = "per group"`, `priceConfidence low→high`, `priceReleasedBy` stamp naming this pass. `price / priceLabel / priceSource / priceBasis / priceTiers / priceVerifiedAt` from #90 stand (priceBasis still opens with "HELD:" as a historical record; the release stamp says why it's lifted).
- Round-trip `json.dumps(indent=2, ensure_ascii=False)+'\n'` asserted byte-identical before write; all 1,635 other rows asserted unchanged.

## Gates (`render-gate.js`, node vm over app.js `createTourCard` on every row)
| run | visible `From €` | JSON-LD offers |
|---|---|---|
| pre (old app.js, old data) | 842 | 842 ✔ |
| control (new app.js, old data) | 842 | 842 ✔ — **0** rows' rendered HTML differ from pre |
| post (new app.js, new data) | 844 | 844 ✔ — exactly 2 rows differ from pre: 662825, 699480 |

Released rows render `From €997.11<small>per group</small>` / `From €524.79<small>per group</small>` and emit `Offer{price, priceCurrency:"EUR"}`. Rows containing `<small>` in the price badge: exactly 662825, 699480.
