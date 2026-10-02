// Export species parameters + habitat-only index at given points from the running app (window.__H test hook).
// Serve index.test.html with a window.__H hook inserted before `function makeP` (see eval/README.md), then: node test/export_hab.js eval/data/eval_points.json eval/data/habitat_at_points.json
const {chromium}=require('playwright');const fs=require('fs');(async()=>{const b=await chromium.launch({args:['--use-gl=swiftshader','--enable-webgl','--ignore-gpu-blocklist']});
const p=await b.newPage({viewport:{width:1000,height:700}});p.on('pageerror',e=>console.log('PE',e.message));
await p.goto('http://localhost:8765/index.html#map=6/45.9/25');await p.waitForFunction(()=>document.getElementById('loading').hidden,null,{timeout:120000});
const pts=JSON.parse(fs.readFileSync(process.argv[2]));
const res=await p.evaluate((pts)=>{const H=window.__H; const P=pts.map(([lon,lat])=>H.makeP(lon,lat));
  const feat=P.map(q=>[Math.round(q.e),q.leaf,+q.f.toFixed(3),q.land?1:0,q.wet===null?null:+q.wet.toFixed(3),q.ph]);
  const sp={}; for(const s of H.LIST){ const hv=new Array(P.length); for(let k=0;k<P.length;k++){ hv[k]=P[k].land? +H.factors(s,P[k],30,true).v.toFixed(4):0; }
    sp[s.latin]={months:s.months,elev:s.elev,t:s.t,lag:s.lag,hosts:s.hosts,frostTol:s.frostTol,hab:s.hab,ed:s.ed,phOpt:s.phOpt,h:hv}; }
  return {feat,sp};},pts);
fs.writeFileSync(process.argv[3],JSON.stringify(res));console.log('points',pts.length,'species',Object.keys(res.sp).length);await b.close();})();
