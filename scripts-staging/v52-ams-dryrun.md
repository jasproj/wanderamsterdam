# wanderamsterdam v5.2 Dry-Run Report (EUR) — null-price tour re-extraction

**Generated:** 2026-05-03T21:45:21.568Z
**Branch:** `feat/ams-v52-price-extraction`
**Mode:** `--dry-run-only` (no writes to tours-data.json)

## 1. Inputs

- wanderamsterdam total tours: 500
- Tours with `price: null` evaluated: **233**
- Extractor: v5.4 baseline + v5.2 dominant-price gate (ported verbatim from wanderusvi)
- Currency: **EUR**
- Page fetch: Playwright (chromium headless), 1.5 s settle wait

## 2. Result distribution

| Outcome | Count | Disposition |
|---|---:|---|
| **high** (v5.4 Method 1/2 — adult/per-person anchor) | 0 | "From $X" if applied |
| **medium** (v5.4 native — Method 3/4/6) | 0 | "From $X" if applied |
| **medium** (v5.2 dominant-price gate) | 1 | "From $X" if applied |
| **low** (Method 5 unanchored, gate FAILed) | 1 | stays "Check availability" |
| **no-price** (extractor returned null) | 231 | stays "Check availability" |
| **error** (fetch/parse) | 0 | stays "Check availability" |
| **Total** | 233 | |

**Net effect if applied --live:** 1 tours flip from "Check availability" → "From $X" (0.4% of the 233). 232 stay hidden.

## 3. Cat-E candidate sanity check

**0 Cat-E candidates** detected among gate PASSes. Disqualifier blocklist (`additional, extra, option, optional, rental, nitrox, upgrade, supplement, add-on, addon, surcharge` + `+$` literal) appears to be holding.

## 4. Sample 10 promoted tours

### 442206 — Open Boot Rondvaart vertrek vanaf Central Station

- company: KINboat
- extracted price: **$20** (medium, unknown)
- priceSource: `v52-dominant-gate`
- gate distinct $-values: [10,20]
- gate matched token: `€ 20,95`
- gate ±40 char window:

  ```
  am CS, perfect bereikbaar voor iedereen € 20,95 Volwassenen Vanaf 13 jaar € 10,40 Kinde
  ```

## 5. Sample 5 stays-hidden tours

### 523958 — Open Boot Rondvaart met Onbeperkte Drankjes vertrekt vanaf Centraal Station

- outcome: low
- gate criterion failed: 2
- distinct $-values: [0,15,31]

### 83660 — Combo: Rijksmuseum + Van Gogh Museum Guided Tour - Semi-Private (ENGLISH)

- outcome: no-price

### 83640 — Rijksmuseum Guided Museum Tour - Private (ENGLISH)

- outcome: no-price

### 83697 — Combo: Rijksmuseum + Amsterdam History - City Center Guided Tour - Private (ENGLISH)

- outcome: no-price

### 83634 — Rijksmuseum Guided Tour - Semi-Private (ENGLISH)

- outcome: no-price

## 6. Out of scope for this run

- No edits to `tours-data.json`.
- No commits, no push, no deploy.
- `--live` mode not implemented yet — adopt USVI's `apply-v52-live.js` pattern when ready.
