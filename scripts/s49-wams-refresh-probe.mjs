#!/usr/bin/env node
// s49-wams-refresh — PROBE stage. Vendored from wanderengland scripts/s48-weng-refresh-b.mjs
// (probe() + helpers, byte-for-byte except: population predicate, EV/SOURCE names, no EXCLUDE set).
//   Population: rows with no priceSource — never touched by a WAMS s46–s49 manual pass
//   (1,366 rows on the 2026-05-28 v7 stamp + pk 442206 with no stamp at all). Re-derived at run time.
//   Endpoint/batching/join-by-id per scripts/extract-prices-v7-api.js (D-613 lineage):
//   price-preview/per-item/v2, include_breakdown=yes, ≤20 pks per request per shortname, 1 req/s,
//   dated requests (date-validity instrument, D-606); timeout/5xx → split chunk in half, retry once
//   per half (bounded, depth ≤ 2). Every population pk must end with exactly DATES.length probes.
//   The APPLY stage is scripts/s49-wams-refresh-apply.py (Python — this file's JSON carries
//   Python float spellings, so JSON.stringify cannot round-trip it; see that file's header).
//   usage: node scripts/s49-wams-refresh-probe.mjs
import fs from 'node:fs';
const FILE = 'tours-data.json';
const EV = 'scripts/evidence/s49-wams-refresh';
const DATES = ['2026-08-31', '2026-09-14', '2026-09-28', '2026-10-19'];
const BATCH = 20, RATE_MS = 1000, TIMEOUT_MS = 25000;
const UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36';
const sleep = ms => new Promise(r => setTimeout(r, ms));

function parseFhUrl(bookingUrl) {   // identical to v7
  if (!bookingUrl || !bookingUrl.includes('fareharbor.com')) return null;
  const m = bookingUrl.match(/fareharbor\.com\/(?:embeds\/book\/)?([^/]+)\/items\/(\d+)/);
  if (!m) return null; const [, shortname, pk] = m;
  if (shortname === 'embeds' || shortname === 'items') return null;
  return { shortname, pk: Number(pk) };
}
const doc = JSON.parse(fs.readFileSync(FILE, 'utf8'));
const pop = doc.tours.filter(t => !t.priceSource);
console.error(`population (no priceSource) = ${pop.length}`);
for (const t of pop) { const p = parseFhUrl(t.bookingUrl); if (!p || p.pk !== t.pk) { console.error('ABORT: bookingUrl pk mismatch', t.pk); process.exit(2); } }

async function get(url, ms) {
  const ac = new AbortController(); const tm = setTimeout(() => ac.abort(), ms);
  try { const r = await fetch(url, { headers: { 'User-Agent': UA, Accept: 'application/json' }, signal: ac.signal });
    if (r.status !== 200) return { err: 'HTTP ' + r.status }; return { j: await r.json() }; }
  catch (e) { return { err: String(e.name === 'AbortError' ? 'timeout' : e.message) }; } finally { clearTimeout(tm); }
}
const batchUrl = (sn, pks, date) => `https://fareharbor.com/api/embed/${sn}/price-preview/per-item/v2/?item_pks=${pks.join(',')}&include_breakdown=yes&date=${date}`;

async function probe() {
  const bySn = new Map();
  for (const t of pop) { const { shortname } = parseFhUrl(t.bookingUrl); if (!bySn.has(shortname)) bySn.set(shortname, []); bySn.get(shortname).push(t.pk); }
  // resume (WAMS adaptation): an earlier run flushes probe.json after every shortname; on restart, shortnames whose
  // pks all carry a full probe set are kept verbatim and skipped, counters carry over. Nothing is re-requested.
  let out = { startedAt: new Date().toISOString(), dates: DATES, population: pop.length, shortnames: bySn.size, requests: 0, retries: [], perPk: {} };
  if (fs.existsSync(`${EV}/probe.json`)) { const prev = JSON.parse(fs.readFileSync(`${EV}/probe.json`, 'utf8')); if (prev.population === pop.length && JSON.stringify(prev.dates) === JSON.stringify(DATES)) { out = prev; out.resumedAt = (out.resumedAt || []).concat(new Date().toISOString()); delete out.finishedAt; delete out.reconcile; } }
  for (const t of pop) if (!out.perPk[t.pk]) out.perPk[t.pk] = { probes: [] };
  const complete = pks => pks.every(pk => out.perPk[pk].probes.length === DATES.length);
  // one request per (shortname, chunk, date); on timeout/5xx split the chunk in half and retry once per half (bounded)
  async function run(sn, pks, date, depth) {
    out.requests++;
    const x = await get(batchUrl(sn, pks, date), TIMEOUT_MS); await sleep(RATE_MS);
    if (x.err && /timeout|HTTP 5/.test(x.err) && pks.length > 1 && depth < 2) {
      out.retries.push({ sn, date, size: pks.length, err: x.err, split: true });
      const h = Math.ceil(pks.length / 2); await sleep(2000);
      await run(sn, pks.slice(0, h), date, depth + 1); await run(sn, pks.slice(h), date, depth + 1); return;
    }
    const items = new Map(((x.j && x.j.items) || []).map(it => [Number(it.id), it]));
    for (const pk of pks) {
      const it = items.get(pk); const p = { date, error: x.err || null };
      if (!x.err) { p.absent = !it; p.liveCurrency = x.j.details?.currency ?? null; p.includeFees = x.j.details?.prices_include_booking_fees ?? null; p.includeTaxes = x.j.details?.prices_include_taxes ?? null; }
      if (it) { const sa = it.availability?.start_at || null; p.start_at = sa; p.dateValid = !!sa && sa.slice(0, 10) === date;
        const cts = Array.isArray(it.price?.breakdown?.customer_types) ? it.price.breakdown.customer_types : [];
        p.tiers = cts.map(c => ({ id: c.id, singular: c.singular, plural: c.plural, note: c.note, priceCents: c.price, min: c.min_party_size }));
        p.low = it.price?.low ?? null; p.zeroOnly = !cts.some(c => c.price > 0); }
      out.perPk[pk].probes.push(p);
    }
  }
  let n = 0;
  for (const [sn, pks] of bySn) {
    if (complete(pks)) { n++; continue; }
    for (const pk of pks) out.perPk[pk].probes = [];   // a partially probed shortname is re-run whole (exactly DATES.length probes per pk)
    for (let i = 0; i < pks.length; i += BATCH) for (const date of DATES) await run(sn, pks.slice(i, i + BATCH), date, 0);
    n++; if (n % 10 === 0) process.stderr.write(`${n}/${bySn.size} operators, ${out.requests} req\n`);
    fs.writeFileSync(`${EV}/probe.json`, JSON.stringify(out));
  }
  out.finishedAt = new Date().toISOString();
  // reconcile: every population pk must have exactly DATES.length probe entries
  const bad = Object.entries(out.perPk).filter(([, v]) => v.probes.length !== DATES.length);
  out.reconcile = { population: pop.length, pksWithFullProbeSet: pop.length - bad.length, incomplete: bad.map(([k]) => k) };
  fs.writeFileSync(`${EV}/probe.json`, JSON.stringify(out));
  console.log(JSON.stringify({ requests: out.requests, retries: out.retries.length, reconcile: out.reconcile }));
}
probe();
