#!/usr/bin/env python3
"""s46 — live price-preview probe of the 3 WAMS max-tier picks. READ-ONLY.
Instrument: WHAW s45-probe-18.py (D-606 re-anchor on FALLBACK, zeroOnlyDates, 17 dates,
control shortname, per-shortname company currency). $0 tiers are recorded, not discarded."""
import json, sys, time, re, collections, urllib.request, urllib.error
from datetime import date, timedelta
API=("https://fareharbor.com/api/embed/{sn}/price-preview/per-item/v2/?item_pks={pks}&include_breakdown=yes&date={d}")
COMPANY="https://fareharbor.com/api/v1/companies/{sn}/"
UA="WanderRenderMonitor/1.0 (+internal-qa)"
GRAT=re.compile(r"\b(gratuit|tip|service charge|fuel surcharge|deposit)",re.I)
RETRIES=3
ANCHOR=sys.argv[1]; OUT=sys.argv[2]; SERVED=sys.argv[3]
rows={r['pk']:r for r in json.load(open(SERVED))['tours']}
targets={}
for pk in (523958,662825,699480):
    r=rows[pk]; sn=re.search(r"fareharbor\.com/embeds/book/([^/]+)/items/",r['bookingUrl']).group(1)
    targets[pk]={'sn':sn,'name':r['name'],'price':r['price'],'label':r.get('priceLabel'),'currency':r.get('currency')}
def dates(a):
    d0=date.fromisoformat(a); return [(d0+timedelta(days=i)).isoformat() for i in range(14)]+[(d0+timedelta(days=n)).isoformat() for n in (30,60,90)]
def get(url,sn):
    last=None
    for attempt in range(RETRIES):
        req=urllib.request.Request(url,headers={"User-Agent":UA,"Accept":"application/json","Referer":f"https://fareharbor.com/embeds/book/{sn}/"})
        try:
            with urllib.request.urlopen(req,timeout=30) as r: return r.status,r.read().decode('utf-8','replace'),None
        except urllib.error.HTTPError as e: return e.code,None,f"HTTP {e.code}"
        except Exception as e: last=str(e)[:120]; time.sleep(1.5*(attempt+1))
    return None,None,"RETRIES_EXHAUSTED: "+str(last)
def tiers_of(it):
    br=((it.get('price') or {}).get('breakdown') or {}); out,zeros,grat=[],[],[]
    for c in br.get('customer_types') or []:
        cents=c.get('price')
        if not isinstance(cents,(int,float)): continue
        rec={"tier_id":c.get('id'),"singular":c.get('singular'),"plural":c.get('plural'),"note":c.get('note'),"min_party_size":c.get('min_party_size'),"cents":cents,"amount":cents/100.0}
        if cents==0: zeros.append(rec)
        elif GRAT.search(f"{c.get('singular') or ''} {c.get('note') or ''}"): grat.append(rec)
        else: out.append(rec)
    return out,zeros,grat
code,_,err=get(API.format(sn="definitely-not-a-real-fh-shortname-zzz",pks="1",d=ANCHOR),"x")
print("[control] impossible shortname ->",code,err,file=sys.stderr)
if code==200: sys.exit("FATAL not falsifiable")
bysn=collections.defaultdict(list)
for pk,v in targets.items(): bysn[v['sn']].append(pk)
company={sn:dict(zip(("code","body_head","err"),(lambda r:(r[0],(r[1] or '')[:120],r[2]))(get(COMPANY.format(sn=sn),sn)))) for sn in bysn}
obs=collections.defaultdict(dict); errors=[]; details_seen=collections.defaultdict(set)
def sweep(sn,pks,days,tag):
    for day in days:
        st,body,ferr=get(API.format(sn=sn,pks=",".join(map(str,pks)),d=day),sn)
        if ferr or not body or not body.lstrip().startswith('{'):
            for pk in pks: obs[pk][day]={"status":"ERROR","err":ferr or "non-JSON","window":tag}
            errors.append((sn,day,ferr)); time.sleep(0.3); continue
        data=json.loads(body); seen={int(it.get('id',-1)):it for it in (data.get('items') or [])}
        det=data.get('details') or {}
        for pk in pks:
            details_seen[pk].add(json.dumps({"currency":det.get('currency'),"fees":det.get('prices_include_booking_fees'),"taxes":det.get('prices_include_taxes')},sort_keys=True))
            it=seen.get(pk)
            if it is None: obs[pk][day]={"status":"UNSAMPLED","window":tag}; continue
            sa=(it.get('availability') or {}).get('start_at'); t,z,g=tiers_of(it); valid=bool(sa) and sa[:10]==day
            obs[pk][day]={"status":"OK" if valid else "FALLBACK","start_at":sa,"requested":day,"date_valid":valid,"tiers":t,"zero_tiers":z,"gratuity_tiers":g,"zeroOnly":valid and not t and bool(z),"low":(it.get('price') or {}).get('low'),"high":(it.get('price') or {}).get('high'),"window":tag}
        time.sleep(0.3)
D=dates(ANCHOR)
for sn,pks in sorted(bysn.items()):
    sweep(sn,sorted(pks),D,"anchor:"+ANCHOR); print(" swept",sn,pks,file=sys.stderr)
reanchored={}
for pk in targets:
    days=obs[pk]; ok=sum(1 for v in days.values() if v['status']=='OK')
    fb=sorted(v['start_at'][:10] for v in days.values() if v['status']=='FALLBACK' and v.get('start_at'))
    if ok==0 and fb:
        a2=fb[0]; reanchored[pk]=a2; sweep(targets[pk]['sn'],[pk],dates(a2),"reanchor:"+a2); print(" re-anchored",pk,a2,file=sys.stderr)
missing=[pk for pk in targets if len(obs[pk])<17]
errpk=[pk for pk in targets if all(v['status']=='ERROR' for v in obs[pk].values())]
json.dump({"anchor":ANCHOR,"dates":D,"population":sorted(targets),"control":{"code":code,"falsifiable":code!=200},"companies":company,"liveDetails":{str(k):sorted(v) for k,v in details_seen.items()},"reanchored":reanchored,"errors":errors,"obs":{str(k):v for k,v in obs.items()},"meta":{str(k):v for k,v in targets.items()}},open(OUT,'w'),indent=1,sort_keys=True)
if missing or errpk: sys.exit(f"ABORT PARTIAL POPULATION missing={missing} all-error={errpk} errors={len(errors)}")
print("WROTE",OUT,"errors",len(errors),file=sys.stderr)
