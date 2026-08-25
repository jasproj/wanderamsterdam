// s49-wams-refresh render harness — WENG s48 render-harness.mjs adapted: WAMS app.js needs the Proxy
// DOM stub from scripts/evidence/s48-wams-held/verify-render.js (top-level DOM access), same loader
// predicate as app.js:92 (status !== 'inactive' && !bookingDead). Emits per-pk {html, schema,
// priceText, currency, confidence, price, unit} so a pre/post diff can assert non-population rows
// byte-identical and every suppressed row "Price on request" with no offer.
// usage: node render-harness.mjs <app.js> <tours-data.json> <out.json>
import fs from 'fs'; import vm from 'vm';
const [,, appPath, dataPath, outPath] = process.argv;
const stub = () => new Proxy(function () {}, { get: (t, k) => k === Symbol.toPrimitive ? () => '' : stub(), apply: () => stub() });
const ctx = { document: stub(), window: stub(), fetch: () => new Promise(() => {}), console, setTimeout: () => 0, localStorage: stub(), sessionStorage: stub(), addEventListener: () => {}, requestAnimationFrame: () => 0, MutationObserver: stub(), navigator: stub(), location: stub(), IntersectionObserver: stub(), URLSearchParams: stub(), history: stub(), URL, Number, JSON, Math, String, Array, Object };
ctx.window = ctx; vm.createContext(ctx);
vm.runInContext(fs.readFileSync(appPath, 'utf8') + '\n;globalThis.__x={createTourCard,generateTourSchema};', ctx);
const { createTourCard, generateTourSchema } = ctx.__x;
const d = JSON.parse(fs.readFileSync(dataPath, 'utf8'));
const loaded = d.tours.filter(t => t.status !== 'inactive' && !t.bookingDead);
const out = {};
for (const t of loaded) {
  const html = createTourCard(t);
  const m = html.match(/class="tour-price"[^>]*>([^<]*)</);
  out[t.pk] = { currency: t.currency ?? null, confidence: t.priceConfidence ?? null, price: t.price ?? null,
    priceText: m ? m[1] : null, unit: (html.match(/<small>(.*?)<\/small>/) || [])[1] ?? null, html, schema: generateTourSchema(t) };
}
fs.writeFileSync(outPath, JSON.stringify(out));
const rows = Object.values(out); const visible = rows.filter(r => r.priceText && r.priceText.startsWith('From '));
const sym = s => s ? (s.match(/^From (\D+)/) || [])[1] : null;
console.log(JSON.stringify({ loaded: rows.length, visiblePrice: visible.length, jsonLdOffers: rows.filter(r => r.schema.offers).length,
  visibleBySymbol: Object.fromEntries([...new Set(visible.map(r => sym(r.priceText)))].sort().map(c => [c, visible.filter(r => sym(r.priceText) === c).length])),
  offersByPriceCurrency: Object.fromEntries([...new Set(rows.filter(r => r.schema.offers).map(r => r.schema.offers.priceCurrency))].sort().map(c => [c, rows.filter(r => r.schema.offers?.priceCurrency === c).length])),
  visibleNonEur: visible.filter(r => r.currency !== 'EUR').length, withUnit: rows.filter(r => r.unit).length,
  priceTextButNoOffer: rows.filter(r => (r.priceText || '').startsWith('From ') !== !!r.schema.offers).length }));
