// Render gate: evaluate app.js in a stub DOM, render every row with createTourCard,
// count visible "From €" vs JSON-LD offers, and dump per-pk rendered HTML for diffing.
const fs=require('fs'), vm=require('vm'), path=require('path');
const [,, appPath, dataPath, outPath]=process.argv;
const src=fs.readFileSync(appPath,'utf8');
const stub={ getElementById:()=>null, addEventListener:()=>{}, querySelector:()=>null, querySelectorAll:()=>[] };
const ctx={ document:stub, window:{}, localStorage:{getItem:()=>null,setItem:()=>{}}, sessionStorage:{getItem:()=>null,setItem:()=>{}}, setTimeout:()=>0, setInterval:()=>0, console, fetch:()=>new Promise(()=>{}), Date, Number, JSON, Math, Intl };
ctx.window=ctx; vm.createContext(ctx);
vm.runInContext(src+'\n;globalThis.__createTourCard=createTourCard;', ctx);
const tours=JSON.parse(fs.readFileSync(dataPath,'utf8')).tours;
let visible=0, offers=0; const out={};
for(const t of tours){
  const html=ctx.__createTourCard(t);
  const priceDiv=(html.match(/<div class="tour-price">([\s\S]*?)<\/div>/)||[])[1]||'';
  if(/^From €/.test(priceDiv)) visible++;
  const ld=JSON.parse(html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1].replace(/<\\\/script/g,'</script'));
  if(ld.offers) offers++;
  out[t.pk]={html, priceDiv, offers: ld.offers||null};
}
fs.writeFileSync(outPath, JSON.stringify(out));
console.log(`rows=${tours.length} visible=${visible} offers=${offers} ${visible===offers?'EQUAL':'MISMATCH'}`);
