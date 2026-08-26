#!/usr/bin/env node
// s51-wams-tiers-backfill — PROBE stage. Adapted from scripts/s49-wams-refresh-probe.mjs, itself
// vendored from wanderengland s48-weng-refresh-b.mjs. Population here is the 233 s47-wams-legacy-enrich
// rows still missing a structured priceTiers array (190 sampled with tiers=None, 43 UNSAMPLED).
// Endpoint matches extract-prices-v7-api.js / s47's own convention exactly: UNDATED price-preview
// per-item v2, include_breakdown=yes (s47 D-606: "undated calls, so each item's availability.start_at
// is the anchor" — no requested-date/start_at mismatch condition can arise). Batching/backoff per v7:
// <=20 pks per request per shortname, 1 req/s, timeout/5xx -> split chunk in half, retry once per half.
import fs from 'node:fs';
const FILE = 'tours-data.json';
const EV = 'scripts/evidence/s51-wams-tiers-backfill';
const BATCH = 20, RATE_MS = 1000, TIMEOUT_MS = 25000;
const UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36';
const sleep = ms => new Promise(r => setTimeout(r, ms));

function parseFhUrl(bookingUrl) {
  if (!bookingUrl || !bookingUrl.includes('fareharbor.com')) return null;
  const m = bookingUrl.match(/fareharbor\.com\/(?:embeds\/book\/)?([^/]+)\/items\/(\d+)/);
  if (!m) return null; const [, shortname, pk] = m;
  if (shortname === 'embeds' || shortname === 'items') return null;
  return { shortname, pk: Number(pk) };
}
const doc = JSON.parse(fs.readFileSync(FILE, 'utf8'));
const popPks = new Set(JSON.parse(fs.readFileSync(`${EV}/population.json`, 'utf8')));
const pop = doc.tours.filter(t => popPks.has(t.pk));
console.error(`population = ${pop.length}`);
if (pop.length !== popPks.size) { console.error('ABORT: population drift', pop.length, popPks.size); process.exit(2); }
for (const t of pop) { const p = parseFhUrl(t.bookingUrl); if (!p || p.pk !== t.pk) { console.error('ABORT: bookingUrl pk mismatch', t.pk); process.exit(2); } }

async function get(url, ms) {
  const ac = new AbortController(); const tm = setTimeout(() => ac.abort(), ms);
  try { const r = await fetch(url, { headers: { 'User-Agent': UA, Accept: 'application/json' }, signal: ac.signal });
    if (r.status !== 200) return { err: 'HTTP ' + r.status }; return { j: await r.json() }; }
  catch (e) { return { err: String(e.name === 'AbortError' ? 'timeout' : e.message) }; } finally { clearTimeout(tm); }
}
const batchUrl = (sn, pks) => `https://fareharbor.com/api/embed/${sn}/price-preview/per-item/v2/?item_pks=${pks.join(',')}&include_breakdown=yes`;

async function probe() {
  const bySn = new Map();
  for (const t of pop) { const { shortname } = parseFhUrl(t.bookingUrl); if (!bySn.has(shortname)) bySn.set(shortname, []); bySn.get(shortname).push(t.pk); }
  let out = { startedAt: new Date().toISOString(), population: pop.length, shortnames: bySn.size, requests: 0, retries: [], perPk: {} };
  if (fs.existsSync(`${EV}/probe.json`)) {
    const prev = JSON.parse(fs.readFileSync(`${EV}/probe.json`, 'utf8'));
    if (prev.population === pop.length) { out = prev; out.resumedAt = (out.resumedAt || []).concat(new Date().toISOString()); delete out.finishedAt; }
  }
  const done = pk => out.perPk[pk] !== undefined;
  async function run(sn, pks, depth) {
    out.requests++;
    const x = await get(batchUrl(sn, pks), TIMEOUT_MS); await sleep(RATE_MS);
    if (x.err && /timeout|HTTP 5/.test(x.err) && pks.length > 1 && depth < 2) {
      out.retries.push({ sn, size: pks.length, err: x.err, split: true });
      const h = Math.ceil(pks.length / 2); await sleep(2000);
      await run(sn, pks.slice(0, h), depth + 1); await run(sn, pks.slice(h), depth + 1); return;
    }
    const items = new Map(((x.j && x.j.items) || []).map(it => [Number(it.id), it]));
    for (const pk of pks) {
      const it = items.get(pk); const p = { error: x.err || null };
      if (!x.err) {
        p.absent = !it;
        p.liveCurrency = x.j.details?.currency ?? null;
        p.includeFees = x.j.details?.prices_include_booking_fees ?? null;
        p.includeTaxes = x.j.details?.prices_include_taxes ?? null;
      }
      if (it) {
        p.start_at = it.availability?.start_at || null;
        const cts = Array.isArray(it.price?.breakdown?.customer_types) ? it.price.breakdown.customer_types : [];
        p.tiers = cts.map(c => ({ id: c.id, singular: c.singular, plural: c.plural, note: c.note, priceCents: c.price, min: c.min_party_size }));
      }
      out.perPk[pk] = p;
    }
  }
  let n = 0;
  for (const [sn, pks] of bySn) {
    const todo = pks.filter(pk => !done(pk));
    if (!todo.length) { n++; continue; }
    for (let i = 0; i < todo.length; i += BATCH) await run(sn, todo.slice(i, i + BATCH), 0);
    n++; if (n % 10 === 0) process.stderr.write(`${n}/${bySn.size} operators, ${out.requests} req\n`);
    fs.writeFileSync(`${EV}/probe.json`, JSON.stringify(out));
  }
  out.finishedAt = new Date().toISOString();
  const bad = pop.map(t => t.pk).filter(pk => out.perPk[pk] === undefined);
  out.reconcile = { population: pop.length, pksWithReading: pop.length - bad.length, missing: bad };
  fs.writeFileSync(`${EV}/probe.json`, JSON.stringify(out));
  console.log(JSON.stringify({ requests: out.requests, retries: out.retries.length, reconcile: out.reconcile }));
}
probe();
