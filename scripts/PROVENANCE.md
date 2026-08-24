# Price-provenance writers vendored from sibling repos

Vendored 2026-08-24 (s46) to close WAMS's unversioned-writer gap under the
D-613 adoption gate. Files are byte-identical copies of tracked sources — no
edits, no reformatting, no run. Verified by sha256 before and after copy.

Recon population: `tours-data.json` → `priceEnrichmentSource`, 1,637 rows
total, 1,369 stamped `extract-prices-v7-api`, 268 unstamped. Rows whose
writer was not in the tracked tree before this PR: 1,369 (claimed 1,369,
delta 0). Row counts re-derived from tours-data.json at origin/main fe1a9e7.

| stamp | rows | tracked writer | status |
|---|---|---|---|
| extract-prices-v7-api | 1,369 | scripts/extract-prices-v7-api.js | **vendored** (this PR) |
| (none) | 268 | — | unstamped; out of scope |

## extract-prices-v7-api.js

- sha256: `584e1463c2b25ae14dfd8626b77d906059d54c94a87433d4f7e23415bc95a41f`
- size: 12229 bytes
- immediate source: wandernewzealand `scripts/extract-prices-v7-api.js`
  (github.com/jasproj/wandernewzealand, tracked at commit 952e0b0, #105)
- origin: wanderpuertorico commit 53c0dc56 (2026-05-28), file at repo root
  `extract-prices-v7-api.js` — same sha256, so WNZ's copy and this copy are
  both verbatim from the WPR original.
- writes stamp: `extract-prices-v7-api` (hard-coded, lines 155/172/179)
- fields minted: `priceEnrichmentSource`, `priceEnrichmentAt`,
  `priceEnrichmentStatus` (`high` | `zero_price` | `none` | `error`),
  `priceEnrichmentError` (error only), `priceIncludesBookingFees`,
  `priceIncludesTaxes`, `currency`, `price`, `priceConfidence`, `priceLabel`,
  `priceBreakdown[]` items `{id, singular, plural, note, priceCents, price,
  minPartySize}`.
- rows accounted for: 1,369 — all `priceEnrichmentAt` stamps dated
  2026-05-28 (same day as the WPR origin commit); shipped in WAMS commit
  40a3cbb (2026-05-28), which touched only data, no script. Status mix:
  702 high, 593 none, 74 zero_price, 0 error. Field-set comparison against
  those rows: no diff — 776 rows (702 high + 74 zero_price) carry
  `priceBreakdown` with exactly the seven item keys above plus both fee
  flags; 593 `none` rows carry only source/at/status; no
  `priceEnrichmentError` present, consistent with 0 error rows.
- adoption date basis: this PR (s46-wams-vendor-v7). Not run in WAMS since
  the 2026-05-28 backfill; `tours-data.json` asserted byte-identical
  (sha256 b39b55566c09ee9abf0e9b487d40fe8ebb04d76876ff5c07c36305ef8689fdc2)
  before and after vendoring.
- copied with `cp -p`, `cmp` byte-identical, sha256 re-verified post-copy.
