#!/usr/bin/env python3
"""s45 WAMS currency verify — probe. Reads tours-data.json, selects rows with stored
currency=='USD', parses shortname/pk from bookingUrl, fetches live FareHarbor
price-preview per shortname (batched), records details.currency + primary positive
tier amount per row. Writes live-currency-observations.json + probe-run.log.
Read-only: never touches tours-data.json."""
import json,re,sys,time,urllib.request,urllib.error,collections,datetime
SRC='tours-data.json'; OUT='scripts-staging/s45-wams-currency-verify/live-currency-observations.json'
LOG='scripts-staging/s45-wams-currency-verify/probe-run.log'
UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
RETRIES=3; TIMEOUT=15; BATCH=20
log=open(LOG,'w')
def L(s): print(s); log.write(s+'\n'); log.flush()
L(f"start {datetime.datetime.now(datetime.timezone.utc).isoformat()}")
rows=json.load(open(SRC))['tours']
usd=[r for r in rows if r.get('currency')=='USD']
L(f"stored-USD population: {len(usd)}")
def parse(url):
    m=re.search(r'fareharbor\.com/embeds/book/([^/?#]+)/items/(\d+)',url or '')
    return (m.group(1),int(m.group(2))) if m else (None,None)
by=collections.defaultdict(list); unparsed=[]
for r in usd:
    s,pk=parse(r.get('bookingUrl'))
    if s is None: unparsed.append(r['pk']); continue
    by[s].append((r['pk'],pk))
L(f"shortnames: {len(by)}  unparsed bookingUrl rows: {unparsed}")
def get(url):
    last=None
    for i in range(RETRIES):
        try:
            req=urllib.request.Request(url,headers={'User-Agent':UA,'Accept':'application/json'})
            with urllib.request.urlopen(req,timeout=TIMEOUT) as resp: return resp.status,json.loads(resp.read())
        except urllib.error.HTTPError as e: last=f"HTTP {e.code}"; 
        except Exception as e: last=f"{type(e).__name__}: {e}"
        time.sleep(1.5*(i+1))
    return None,last
obs={}
for s,pairs in sorted(by.items()):
    for i in range(0,len(pairs),BATCH):
        chunk=pairs[i:i+BATCH]; pks=[p for _,p in chunk]
        url=f"https://fareharbor.com/api/embed/{s}/price-preview/per-item/v2/?item_pks={','.join(map(str,pks))}&include_breakdown=yes"
        st,j=get(url)
        if st!=200:
            L(f"  {s} batch {i//BATCH}: FAILED after {RETRIES} tries: {j}")
            for rpk,ipk in chunk: obs[str(rpk)]={'pk':rpk,'shortname':s,'itemPk':ipk,'reachable':False,'error':str(j)}
            continue
        cur=(j.get('details') or {}).get('currency'); items={int(it['id']):it for it in j.get('items',[])}
        for rpk,ipk in chunk:
            it=items.get(ipk); amt=None; label=None; found=it is not None
            if it:
                cts=((it.get('price') or {}).get('breakdown') or {}).get('customer_types') or []
                prim=next((c for c in cts if isinstance(c.get('price'),(int,float)) and c['price']>0),None)
                if prim: amt=prim['price']/100; label=prim.get('singular')
                elif (it.get('price') or {}).get('low',0)>0: amt=it['price']['low']/100
            obs[str(rpk)]={'pk':rpk,'shortname':s,'itemPk':ipk,'reachable':True,'itemInResponse':found,'liveCurrency':cur,'liveAmount':amt,'liveLabel':label,'httpStatus':st}
        L(f"  {s} batch {i//BATCH}: 200 currency={cur} items={len(items)}/{len(pks)}")
        time.sleep(0.4)
for pk in unparsed: obs[str(pk)]={'pk':pk,'reachable':False,'error':'unparsable bookingUrl'}
json.dump({'probedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'population':len(usd),'observations':obs},open(OUT,'w'),indent=1,sort_keys=True)
reach=[o for o in obs.values() if o.get('reachable')]
L(f"population {len(usd)} observed {len(obs)} reachable {len(reach)} unreachable {len(obs)-len(reach)} item-missing {sum(1 for o in reach if not o.get('itemInResponse'))}")
L("live currency dist: "+str(collections.Counter(o.get('liveCurrency') for o in reach)))
if len(obs)!=len(usd): L("ABORT: observation count != population"); sys.exit(2)
