import json,collections
d=json.load(open('served-tours-data.json')); rows=d['tours']
def ns(b): return [x['price'] for x in b if isinstance(x,dict) and isinstance(x.get('price'),(int,float))]
bk=[r for r in rows if r.get('priceBreakdown')]
mt=[r for r in bk if ns(r['priceBreakdown']) and r['price']==max(ns(r['priceBreakdown']))!=min(ns(r['priceBreakdown']))]
first=[r for r in mt if r['priceBreakdown'][0].get('price')==r['price']]
notfirst=[r for r in mt if r['priceBreakdown'][0].get('price')!=r['price']]
print("max-tier 180 split: price==breakdown[0] (adult-first):",len(first)," price!=breakdown[0] (true max-tier pick):",len(notfirst))
for r in notfirst[:15]: print("  ",r['pk'],r.get('price'),r.get('priceLabel'),[ (x['singular'],x['price']) for x in r['priceBreakdown']][:5])
# how is price picked overall?
c=collections.Counter()
for r in bk:
    n=ns(r['priceBreakdown'])
    if not n: c['no-nums']+=1; continue
    p=r['price']
    c['==first' if p==r['priceBreakdown'][0].get('price') else ('==min' if p==min(n) else ('==max' if p==max(n) else 'other'))]+=1
print("price-pick policy over 776 breakdown rows:",c)
# min>0 nonzero pick?
minpos=[r for r in bk if ns(r['priceBreakdown']) and r['price']==min([x for x in ns(r['priceBreakdown']) if x>0] or [None])]
print("price==min positive tier:",len(minpos))
# populations
legacy=[r for r in rows if 'id' in r]; hermes=[r for r in rows if r.get('source')=='fareharbor-hermes-extract']
print("legacy(id key):",len(legacy)," hermes:",len(hermes)," overlap:",len([r for r in legacy if r.get('source')]))
print("legacy w/ priceEnrichmentSource:",sum(1 for r in legacy if r.get('priceEnrichmentSource'))," hermes w/:",sum(1 for r in hermes if r.get('priceEnrichmentSource')))
nost=[r for r in rows if not r.get('priceEnrichmentSource')]
print("no-stamp 268: legacy",sum(1 for r in nost if 'id' in r),"hermes",sum(1 for r in nost if r.get('source')))
print("no-stamp priceLabel:",collections.Counter(r.get('priceLabel') for r in nost).most_common(5))
print("no-stamp currency:",collections.Counter(r.get('currency') for r in nost))
print("no-stamp sample:",[(r['pk'],r['price'],r.get('currency'),r.get('priceLabel'),r.get('bookingUrl','')[:50]) for r in nost[:6]])
# status x price
print("status x price>0:",collections.Counter((r.get('priceEnrichmentStatus'), isinstance(r.get('price'),(int,float)) and r['price']>0) for r in rows))
print("currency x source:",collections.Counter((r.get('currency'), 'hermes' if r.get('source') else 'legacy') for r in rows))
print("USD rows w/ breakdown:",sum(1 for r in rows if r.get('currency')=='USD' and r.get('priceBreakdown')))
print("USD sample urls:",[r['bookingUrl'][:60] for r in rows if r.get('currency')=='USD'][:5])
print("zero_price rows price:",collections.Counter(r.get('price') for r in rows if r.get('priceEnrichmentStatus')=='zero_price'))
print("'none' rows price:",collections.Counter(type(r.get('price')).__name__ for r in rows if r.get('priceEnrichmentStatus')=='none'))
uf=[r for r in rows if r.get('_unknownFields')]; print("_unknownFields row:",uf[0]['pk'],uf[0].get('price'),uf[0].get('priceEnrichmentSource'),uf[0]['_unknownFields'])
print("bookingDead:",[(r['pk'],r.get('bookingDead')) for r in rows if r.get('bookingDead')])
print("statuses:",collections.Counter(r.get('status') for r in rows))
print("priceConfidence:",collections.Counter(r.get('priceConfidence') for r in rows))
print("empty-string stamp fields (legacy): ratingSource/enrichmentSource/lastUpdated all '' :",sum(1 for r in legacy if r.get('ratingSource')=='' and r.get('lastUpdated')==''))
print("legacy rating>0:",sum(1 for r in legacy if r.get('rating')), "reviewCount>0:",sum(1 for r in legacy if r.get('reviewCount')))
