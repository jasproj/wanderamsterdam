// node vm over app.js createTourCard: count visible "From €" vs JSON-LD offers for a tours-data.json path.
const fs=require('fs'),vm=require('vm');
const [,,appPath,dataPath,popPath]=process.argv;
const stub=()=>new Proxy(function(){}, {get:(t,k)=>k===Symbol.toPrimitive?()=>'' :stub(),apply:()=>stub()});
const ctx={document:stub(),window:stub(),fetch:()=>new Promise(()=>{}),console,setTimeout:()=>0,localStorage:stub(),sessionStorage:stub(),addEventListener:()=>{},requestAnimationFrame:()=>0,MutationObserver:stub(),navigator:stub(),location:stub(),IntersectionObserver:stub(),URLSearchParams:stub(),history:stub()};
ctx.window=ctx; vm.createContext(ctx);
vm.runInContext(fs.readFileSync(appPath,'utf8')+'\n;globalThis.__cc=createTourCard;',ctx);
const tours=JSON.parse(fs.readFileSync(dataPath,'utf8')).tours; const pop=new Set(JSON.parse(fs.readFileSync(popPath,'utf8')));
let vis=0,offers=0; const rows={};
for(const t of tours){const h=ctx.__cc(t); const v=/From €/.test(h); const ld=JSON.parse(h.match(/<script type="application\/ld\+json">(.*?)<\/script>/s)[1]); const o=!!ld.offers;
 vis+=v; offers+=o; if(pop.has(t.pk)){const u=(h.match(/<small>(.*?)<\/small>/)||[])[1]||null; rows[t.pk]={visible:v,offer:o,price:ld.offers?ld.offers.price:null,cur:ld.offers?ld.offers.priceCurrency:null,unit:u,text:(h.match(/class="tour-price">(.*?)<\/div>/s)||[])[1]};}}
console.log(JSON.stringify({visiblePrice:vis,jsonLdOffers:offers,rows}));
