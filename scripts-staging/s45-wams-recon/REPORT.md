# s45 WAMS recon — 2026-08-24 — origin/main 82e5fa7 — NOTHING WRITTEN TO GIT (D-604)
Ground truth: served tours-data.json == disk, 4,872,232 bytes, sha256 6b5aa6feb813ad24cacbf3b3207bb3c914dff537248f671a2ba3d2bbb5e0b0a9
Rows 1637 (500 legacy w/ `id`, 1137 hermes). schemaVersion 1.0.8, lastNormalized 2026-05-28T15:23:28Z.
All liveness/render claims: served-bytes substitution (Chrome disconnected).
See census.py / refine.py for reproduction; stdout captured in the session transcript.

## Findings (full write-up in session transcript; reproduce with census.py / refine.py → census-output.txt / refine-output.txt)
- Stamp census: `extract-prices-v7-api` 1,369 rows (UNTRACKED — writer lives in wanderpuertorico/wandernewzealand); `fareharbor-hermes-extract` 1,137 (TRACKED, scripts/merge-hermes-extract.py); `extract-images-v1` 1,137 (UNRECOVERABLE — no writer in any repo); `_unknownFields.priceSource=v52-dominant-gate` 1 (staging writer, demoted by unknown normalizer); bookingDead 7 (no writer). 268 legacy rows with no price stamp, all priced, 143 emitting offers. All stamps dated 2026-05-28.
- Max-tier: `priceLabel=='charter'` 0 (delta 0, but fingerprint is meaningless on multilingual raw labels). `price==max(breakdown)!=min` 180 (177 adult-first, 3 true max-tier picks: pk 523958, 662825, 699480 — v7 "first positive tier" rule).
- Currency (UNVERIFIED-STORED at recon time): EUR 889 / null 518 / USD 230; 118 USD rows published as EUR offers via hard-coded JSON-LD priceCurrency. → Resolved by PR #87 (live-verified: 229 EUR, 1 USD).
- Render gate (served-bytes): visible `From €` 845 == JSON-LD offers 845; "Price on request" 792. Post-#87: 844/844, 0 non-EUR offers.
- Phase 3 for #87: 6/6 at squash 95c58df (see MANIFEST.txt for post-merge served hash).

## Open for s46
1. Vendor extract-prices-v7-api.js into this repo; record extract-images-v1 as unrecoverable.
2. Re-enrich or suppress offers for the 268 unstamped legacy rows.
3. Fix v7 primary-tier rule (min positive per-person tier) → 3 max-tier rows.
4. Re-run enrichment (88 days stale; 593 rows price:null).
5. Replace charter-label fingerprint with the breakdown check; find the `_unknownFields` normalizer.
6. Strip empty Hawaii-template stamps (ratingSource/enrichmentSource/lastUpdated/island) on 500 legacy rows.
