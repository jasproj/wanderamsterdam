# s46 — WAMS max-tier 3 — 2026-08-24 — base origin/main 6dd0c2c

Served `tours-data.json` == disk before write: sha256 `b39b5556…` (4,909,317 bytes). After: `5fafd5e9…` (4,912,016 bytes).

## Recon (served bytes)
Predicate: leading €0 tier skipped by v7 `list.find(price>0)` **and** stored price == max positive tier
→ exactly {523958, 662825, 699480}; delta 0 vs the s45 list. (631284 also has a leading €0 tier but
already sits at its min tier — excluded, unchanged.)

## Live probe — `probe-maxtier-3.py` → `live-readings-2026-08-25-anchor.json`
Instrument: WHAW s45-probe-18 (17 dates 2026-08-25..09-07 + 30/60/90d, `include_breakdown=yes`, D-606
re-anchor on FALLBACK, zeroOnlyDates, control shortname, per-shortname company probe). Probed 2026-08-24.
Control: impossible shortname → 400 (falsifiable). Errors 0. Re-anchors 0. zeroOnlyDates 0 on every row.
Live `details.currency` = EUR, fees+taxes included, on every reading of all 3 rows.

| pk | shortname | stored | live ladder (every customer type, €0 recorded) | readings | disposition |
|---|---|---|---|---|---|
| 523958 | kinboat | 31.65 Volwassene | Infant **0** ("API") · Volwassene 31.65 "Vanaf 13 jaar" · Kind 15.83 "Vanaf 3 tot 12 jaar"; all min_party 1 | 17 OK | **STAMPS-ONLY** 31.65 / Volwassene / high |
| 662825 | paynehurdstours | 997.11 Group | Child **0** "Ages 0-17 • Price per person" · Group 997.11 **"Price per group."** min_party 1 | 16 OK, 1 FALLBACK | **HOLD** low |
| 699480 | paynehurdstours | 524.79 Group | Child **0** "Ages 0-17 • Price per person" · Group 524.79 **"Price per group."** min_party 1 | 16 OK, 1 FALLBACK | **HOLD** low |

The €0 tiers are the evidence of the v7 defect (`list.find(price>0)` skipped them and took the next
tier). For 523958 that tier was the adult fare, which is the correct "From" anchor — child tiers never anchor (WHAW s45, 57549) — so the fix there is stamps-only.

## Group-unit finding (662825 / 699480)
The sole positive tier's note is "Price per group." — a whole-party fare. Rendering it via
`formatPrice` as `From €997.11` / `From €524.79` publishes a group fare as a per-person price (unit
defect). WAMS `app.js` has no `priceUnit` render path (KWST/WNZ port not present), and the note gives
no party cap to build a `"whole boat · up to N"` string from. Per ruling: **HOLD** — `priceConfidence:
low` (card → "Price on request", JSON-LD offer suppressed), amount left as the true whole-group value,
basis stamped. D-614 ladder logic does not apply (single tier, no ladder).

## Write — `apply-maxtier-3.py --execute` (deterministic, asserts against date-valid readings)
- 4-field stamp on all 3 (flat, WAMS convention): `priceSource="s46-wams-maxtier-3"`, `priceBasis`,
  `priceTiers` (full live ladder incl. €0 tiers, `priceCents` int + `price`), `priceVerifiedAt="2026-08-24"`.
- 523958: STAMPS-ONLY — price €31.65 / Volwassene unchanged (adult anchors "From"; child tier Kind €15.83 never does — WHAW s45 precedent 57549), priceConfidence high, full ladder incl. €0 Infant stamped.
- 662825 / 699480: price + label unchanged, priceConfidence high→low.
- Every other row asserted byte-identical (json.dumps(sort_keys) equality on all 1,634).
- Int/float: 3060→3069 float tokens — 4 new tier amounts + 5 quotations in `priceBasis` text; no
  existing float re-spelled; zero-cent tiers written as int `0`.
- Render gate: visible `From €` 844→842 == JSON-LD offers 844→842 (the two held rows).
