import json,collections,re
d=json.load(open('served-tours-data.json'))
rows=d['tours'] if isinstance(d,dict) and 'tours' in d else d
if isinstance(d,dict): print("top-level keys:",list(d.keys())[:20], {k:(v if not isinstance(v,(list,dict)) else f'<{type(v).__name__} {len(v)}>') for k,v in d.items()})
print("rows:",len(rows))
allkeys=collections.Counter()
for r in rows: allkeys.update(r.keys())
print("KEYS:",dict(allkeys))
stampish=[k for k in allkeys if re.search(r'source|stamp|enrich|version|provenance|updated|checked|fetched|_unknown|origin|label',k,re.I)]
print("STAMP-SHAPED KEYS:",stampish)
for k in stampish:
    vals=collections.Counter()
    for r in rows:
        v=r.get(k)
        if isinstance(v,dict):
            for kk,vv in v.items(): vals[f"{k}.{kk}={json.dumps(vv)[:80]}"]+=1
        elif v is not None: vals[json.dumps(v)[:80]]+=1
    print(f"\n== {k} (present in {sum(1 for r in rows if r.get(k) is not None)} rows)")
    for v,c in vals.most_common(40): print(f"  {c:5d}  {v}")
nostamp=[r for r in rows if not r.get('priceSource') and not r.get('priceEnrichmentSource')]
print("\nrows with NO priceSource/priceEnrichmentSource:",len(nostamp))
print(" of which price>0:",sum(1 for r in nostamp if isinstance(r.get('price'),(int,float)) and r['price']>0))
dates=[]
for r in rows:
    for k,v in r.items():
        if isinstance(v,str) and re.match(r'20\d\d-\d\d-\d\d',v): dates.append((k,v[:10]))
dc=collections.Counter(k for k,_ in dates); print("date fields:",dc)
for k in dc:
    vs=sorted(v for kk,v in dates if kk==k); print(f"  {k}: oldest {vs[0]} newest {vs[-1]}")
print("\npriceLabel:",collections.Counter(r.get('priceLabel') for r in rows))
charter=sum(1 for r in rows if r.get('priceLabel')=='charter'); print("priceLabel=='charter':",charter,"delta vs claimed 0:",charter)
bk=[r for r in rows if r.get('priceBreakdown')]
print("rows with priceBreakdown:",len(bk))
def nums(b):
    if isinstance(b,dict): return [x for x in b.values() if isinstance(x,(int,float))] or [x.get('price') for x in b.values() if isinstance(x,dict) and isinstance(x.get('price'),(int,float))]
    if isinstance(b,list): return [x.get('price') if isinstance(x,dict) else x for x in b if isinstance(x,(int,float)) or (isinstance(x,dict) and isinstance(x.get('price'),(int,float)))]
    return []
if bk:
    print(" sample:",json.dumps(bk[0]['priceBreakdown'])[:300])
    mt=[r for r in bk if nums(r['priceBreakdown']) and r.get('price')==max(nums(r['priceBreakdown']))!=min(nums(r['priceBreakdown']))]
    print(" price==max(breakdown)!=min:",len(mt),"delta vs 0:",len(mt))
    for r in mt[:10]: print("   ",r.get('id') or r.get('slug'),r.get('price'),r['priceBreakdown'])
tier=[k for k in allkeys if re.search(r'tier|option|variant|rate|prices|pricing|unit|breakdown',k,re.I)]
print(" tier-like keys:",tier)
for k in tier:
    c=collections.Counter(json.dumps(r.get(k))[:70] for r in rows if r.get(k) is not None); print("  ",k,"distinct",len(c),c.most_common(6))
print("\ncurrency (UNVERIFIED-STORED):",collections.Counter(r.get('currency') for r in rows))
print("price>0:",sum(1 for r in rows if isinstance(r.get('price'),(int,float)) and r['price']>0),"price types:",collections.Counter(type(r.get('price')).__name__ for r in rows))
print("price==0:",sum(1 for r in rows if r.get('price')==0))
