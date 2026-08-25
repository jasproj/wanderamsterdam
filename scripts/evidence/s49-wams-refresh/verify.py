# s49-wams-refresh verify (WENG s48-b verify.py adapted: € symbol, disposition-decomposed delta).
# sha256 in Python only; render before (origin/main bytes) vs after; byte round-trip; 0 out-of-population diffs;
# every suppressed population row renders "Price on request" with no JSON-LD offer; visible == offers after.
import json, hashlib, subprocess, sys, collections
EV = 'scripts/evidence/s49-wams-refresh'
sha = lambda b: hashlib.sha256(b).hexdigest()
base = subprocess.run(['git', 'show', 'origin/main:tours-data.json'], capture_output=True, check=True).stdout
open(f'{EV}/tours-data.before.json', 'wb').write(base)
before = json.loads(base)['tours']; raw = open('tours-data.json', 'rb').read(); after = json.loads(raw)['tours']
summ = json.load(open(f'{EV}/apply-summary.json')); pop = {r['pk'] for r in summ['summary']}
assert len(before) == len(after) == 1637
out_of_pop_diff = [a['pk'] for b, a in zip(before, after) if a['pk'] not in pop and json.dumps(b, sort_keys=True) != json.dumps(a, sort_keys=True)]
rt = (json.dumps(json.loads(raw), indent=2, ensure_ascii=False) + '\n').encode() == raw
for tag, path in (('before', f'{EV}/tours-data.before.json'), ('after', 'tours-data.json')):
    r = subprocess.run(['node', f'{EV}/render-harness.mjs', 'app.js', path, f'{EV}/render-{tag}.json'], capture_output=True, text=True, check=True)
    open(f'{EV}/render-{tag}.summary.json', 'w').write(r.stdout)
rb = json.load(open(f'{EV}/render-before.json')); ra = json.load(open(f'{EV}/render-after.json'))
vis = lambda r: (r['priceText'] or '').startswith('From ')
va = [k for k, r in ra.items() if vis(r)]; oa = [k for k, r in ra.items() if r['schema'].get('offers')]
supp = [k for k, r in ra.items() if int(k) in pop and r['confidence'] == 'low']
bad_supp = [k for k in supp if ra[k]['priceText'] != 'Price on request' or ra[k]['schema'].get('offers')]
nonpop_render_diff = [k for k in ra if int(k) not in pop and (ra[k]['html'] != rb[k]['html'] or ra[k]['schema'] != rb[k]['schema'])]
# delta decomposed by disposition class (rendered rows only; 7 bookingDead rows are not loaded)
delta = collections.Counter()
for rec in summ['summary']:
    k = str(rec['pk'])
    if k not in ra: continue
    delta[rec['disposition']] += int(vis(ra[k])) - int(vis(rb[k]))
res = {'sha256_before_originmain': sha(base), 'sha256_after': sha(raw), 'rows': len(after), 'population': len(pop),
       'outOfPopulationRowsChanged': len(out_of_pop_diff), 'byteRoundTrip': rt,
       'before': {'visible': sum(1 for r in rb.values() if vis(r)), 'offers': sum(1 for r in rb.values() if r['schema'].get('offers'))},
       'after': {'visible': len(va), 'offers': len(oa), 'visibleEqualsOffers': len(va) == len(oa), 'mismatchPks': [k for k in ra if vis(ra[k]) != bool(ra[k]['schema'].get('offers'))]},
       'visibleDeltaByDisposition': dict(delta), 'visibleDeltaTotal': sum(delta.values()),
       'popSuppressed': len(supp), 'suppressedRenderViolations': bad_supp, 'nonPopulationRenderDiff': len(nonpop_render_diff),
       'popVisibleBefore': sum(1 for k in rb if int(k) in pop and vis(rb[k])), 'popVisibleAfter': sum(1 for k in ra if int(k) in pop and vis(ra[k])),
       'withUnitAfter': sum(1 for r in ra.values() if r['unit']), 'disposition': summ['disposition'], 'stampedAt': summ['stampedAt']}
json.dump(res, open(f'{EV}/verify.json', 'w'), indent=1); print(json.dumps(res, indent=1))
ok = res['outOfPopulationRowsChanged'] == 0 and rt and res['after']['visibleEqualsOffers'] and not bad_supp and res['nonPopulationRenderDiff'] == 0 \
     and res['visibleDeltaTotal'] == res['after']['visible'] - res['before']['visible']
print('VERIFY', 'PASS' if ok else 'FAIL'); sys.exit(0 if ok else 1)
