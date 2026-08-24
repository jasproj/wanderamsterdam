// Preload: tee every fetch response body to an evidence NDJSON (date-validity instrument). Script under test untouched.
const fs=require('fs');const out=process.env.FETCH_TEE;const orig=globalThis.fetch;
globalThis.fetch=async function(url,opts){const r=await orig(url,opts);const c=r.clone();let body=null;try{body=await c.text();}catch(e){body=null}
fs.appendFileSync(out,JSON.stringify({at:new Date().toISOString(),url:String(url),status:r.status,body:(()=>{try{return JSON.parse(body)}catch(e){return body}})()})+"\n");return r;};
