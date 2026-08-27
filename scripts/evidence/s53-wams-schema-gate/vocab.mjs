// s53-wams-schema-gate: dump the unit-evidence vocabulary of the EMITTING
// population (the loadTours() draw pool, app.js:92, further gated by
// generateTourSchema's own emitPrice predicate) so the three-state classifier
// is built from this repo's own data, not from a guessed word list.
// usage: node vocab.mjs <app.js> <tours-data.json>
import fs from 'fs';
import vm from 'vm';

const [appPath, dataPath] = process.argv.slice(2);
const src = fs.readFileSync(appPath, 'utf8');
const d = JSON.parse(fs.readFileSync(dataPath, 'utf8'));
const rows = Array.isArray(d) ? d : d.tours;

const ctx = vm.createContext({ console, window: undefined, document: undefined });
vm.runInContext(
  src.slice(0, src.indexOf('// Fisher-Yates shuffle')) +
    '\n;globalThis.__x={priceUnit};',
  ctx
);
const { priceUnit } = ctx.__x;

// The loadTours() draw-pool filter, verbatim (app.js:92).
const drawPool = rows.filter((t) => t.status !== 'inactive' && !t.bookingDead);
// generateTourSchema's own emitPrice gate (app.js:160) -- the rows that emit
// a bare Offer.price TODAY, and therefore the population this gate concerns.
const pool = drawPool.filter((t) => Number.isFinite(t.price) && t.priceConfidence !== 'low');
console.log(`draw pool: ${drawPool.length} of ${rows.length} rows`);
console.log(`emitting population (draw pool + emitPrice): ${pool.length} of ${rows.length} rows`);

function anchorTier(t) {
  const pb = Array.isArray(t.priceBreakdown) ? t.priceBreakdown : [];
  return pb.find((p) => p.price === t.price) || null;
}

function tally(label, values) {
  const m = new Map();
  for (const v of values) m.set(v, (m.get(v) || 0) + 1);
  console.log(`\n== ${label} (${m.size} distinct) ==`);
  [...m.entries()]
    .sort((a, b) => b[1] - a[1])
    .forEach(([k, n]) => console.log(`${String(n).padStart(5)}  ${k}`));
}

tally('priceUnit (_unknownFields.priceUnit via priceUnit())', pool.map((t) => priceUnit(t) || '<empty>'));
tally('priceLabel', pool.map((t) => (t.priceLabel || '<null>').trim() || '<empty>'));
tally('anchor tier singular', pool.map((t) => {
  const a = anchorTier(t);
  return a ? (a.singular || '<no-singular>').trim() : '<no-anchor-tier>';
}));
