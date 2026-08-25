# s49 WAMS delta — 2026-08-25 — main squash 7f504da (PR #95, merged 2026-08-25T16:16:25Z)

Ground truth: served tours-data.json == disk == squash git content, 5,299,888 bytes,
sha256 580368f3d7ffdcab44da46178ea3aaa77d8a2aa37e3494fd10985667795eb421.
All liveness/render claims below: served-bytes substitution (Chrome extension disconnected —
`list_connected_browsers` returned zero devices; substituted a direct HTTPS fetch of
https://wanderamsterdam.com/tours-data.json in its place, labelled here per the s45 precedent).
Reproduce with `scripts/evidence/s49-wams-heldrelease2/verify-render.js` against a re-fetched copy;
apply script and full row-level basis text in `scripts/evidence/s49-wams-heldrelease2/`.

## Ruling: D-?? (pending assembler ID) — description-derived priceUnit sanctioned

Jason, 2026-08-25: a `priceUnit` string may now derive from a row's free-text `description`
(not only from a tier `label`/`note`), **provided**:
1. the source text is quoted **verbatim** in `priceBasis`, and
2. any conflict against another stored field (capacity, duration, etc.) is flagged in the same
   `priceBasis` string, not silently resolved.

This is a new precedent alongside the existing `s48-R1` (sliding-ladder), `D-614` (whole-group
floor band), and `D-621` (child tiers never anchor) rulings — none of which cover a
description-sourced unit. Recorded here as `D-??` pending an assembler-assigned decision id;
do not mint a numeral in this window (see prior WAMS practice: `s48-R1` shipped the same way,
labelled "decision id pending", before an id was assigned).

## The 4 s48 HELD rows — 3 released, 1 re-queued

| pk | name | disposition | price | priceUnit | source (verbatim) |
|---|---|---|---|---|---|
| 107307 | Private Deluxe Boat Cruise | **released** | 450 → **350.00 EUR** (floor tier swap, drops the s47/s48 anchor) | "per boat, up to 12 guests" | description: "The boats are cozy and private, with space for up to 12 guests." — **flag:** stored `capacity` field = 10, conflicts with the description's 12; unit follows the description quote per the ruling, capacity field left unreconciled |
| 244818 | Big Saloon Boat | **released** | 466.86 EUR (unchanged) | "per boat, up to 85 passengers" | description's own "Capacity / Up to 85 passengers" header block — matches stored `capacity` field 85, no conflict |
| 326244 | Private Leemstar V Amsterdam Discovery Cruise | **released** | 369.27 EUR (unchanged) | "per boat, up to 12 guests" | description/highlights: "The cruise is intimate and has no more than 12 guests on board." — **flag:** stored `duration` field "90 Minutes" mismatches the ruled anchor tier "Private Cruise - 1 Hour" (90 min actually pairs with the second tier, "1.5 Hours", 501.15 EUR); price/unit follow the ruled 1-Hour anchor, duration field left unreconciled |
| 623293 | Amsterdam Food Tour De Pijp - Private | **stays held** | 366.31 EUR (unchanged) | none | no description/title cap language exists to derive a unit from; see template-ruling queue below |

No reprobe for any of the 4: all `priceTiers`/`priceBasis` stamps are the s48 pass's live
2026-08-24 evidence, carried forward unchanged.

### 623293 — template-ruling queue (open item, not resolved by D-??)

Whole-group ladder ("Private tour 1 person" .. "8 persons") whose tier labels carry party-size
text but fit neither established template cleanly:
- Not a single **D-614** whole-group-band tier (contrast pk 690937's lone "Private tour 1-4
  persons" tier, which *is* a clean floor-band single-price case).
- Not a clean **R1** per-person sliding ladder either (R1 tiers are themselves per-head rates;
  here the totals are whole-booking group totals).
- The ladder's totals increase **linearly** by a constant **+52.48 EUR/head**: 366.31, 418.78,
  471.26, [523.74 @ n=4], 576.22, 628.70, 681.18, 733.66 — i.e. `total = 366.31 + 52.48*(n-1)`, a
  base-fee-plus-per-head group total, not a per-attendee rate card.
- The "Private tour 1-4 persons" tier sits exactly where a clean "4 persons" step would land
  (+52.48 over the 3-person tier) — **suspected mislabel/merge**, not a genuine 1-4 range band.

**Queued for next ruling:** which template (R1 sliding-per-person vs D-614 whole-group-band)
governs a mixed incremental/banded party ladder, and whether "Private tour 1-4 persons" should
be read/relabeled as "4 persons". `priceBasis` has been restamped with this analysis so the
evidence travels with the row (see PR #95 diff, pk 623293).

## Phase 3 chain — post-merge verify: 6/6 at squash 7f504da

| # | check | result |
|---|---|:---:|
| 1 | PR #95 `MERGED`, squash captured | ✅ `7f504dadc314fac0c2c54f2c5d26d39408902f73` |
| 2 | `tours-data.json` at squash: sha256 matches pre-merge committed content | ✅ `580368f3...` both sides |
| 3 | Live served bytes at `https://wanderamsterdam.com/tours-data.json` match squash git content (labelled substitution — Chrome disconnected) | ✅ `580368f3...`, 5,299,888 bytes, HTTP 200 |
| 4 | Render-gate (served bytes, `app.js` `createTourCard`): visible `From €` count | ✅ 875 (delta **+3** vs pre-merge baseline 872) |
| 5 | Render-gate: JSON-LD `offers` count | ✅ 873 (delta **+3** vs pre-merge baseline 870) |
| 6 | Per-row spot check on served bytes: 3 released rows render `From €<price><small>unit</small>` + offer; 623293 still "Price on request", no offer (no regression on the held row) | ✅ |

Evidence: `scripts-staging/s49-wams-recon/MANIFEST.txt` (served-bytes sha256);
`scripts/evidence/s49-wams-heldrelease2/verify-before.json` / `verify-after.json` (local
pre/post-merge render-gate runs, same figures reproduced live above).

## TASKS (open for next pass)

- [ ] **Islands nav locked-terms fix.** WAMS column-1 term is "Areas" everywhere else on the
  site (footer column-1 on every page already says "Areas"; `privacy.html`/`terms.html` header
  nav already say "Areas" too) — but 2 pages still render the header-nav link text as
  "Islands": `blog.html:107` (nav-desktop) / `blog.html:117` (nav-mobile) / `index.html:126`
  (nav-desktop) / `index.html:137` (nav-mobile). Fix: change the 4 anchor text nodes from
  "Islands" to "Areas" (keep `href="#islands"`/`href="/#islands"` — only the visible label
  changes), matching the `privacy.html`/`terms.html` pattern exactly. Not in scope for PR #95 —
  tracked here per Jason's instruction to keep it a separate task.
