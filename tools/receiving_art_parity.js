// Check editor/receiving-art.js pack() against the Python packer: re-pack every Royal receiving drawing and
// compare with data/perfect-receivers.json canonical_chunks.  node tools/receiving_art_parity.js ROYAL.sfc
const fs=require('fs'),path=require('path');global.window=global;
for(const f of ['royal-import-layouts.js','royal-import-core.js','perfect-receiver-layouts.js','raw-tile-directory.js','raw-parts.js','receiving-art.js'])require(path.join(__dirname,'../editor',f));
const royal=new Uint8Array(fs.readFileSync(process.argv[2])),R=window.RAW_PERFECT_RECEIVERS,A=window.RAW_RECEIVING_ART;
const identity=Array.from({length:16},(_,i)=>i);let checked=0,bad=0;
R.workers.forEach((w,selector)=>w.poses.forEach((p,i)=>{checked++;const got=A.pack(A.donorImage(royal,R,selector,i,identity));if(JSON.stringify(got)!==JSON.stringify(p.canonical_chunks)){bad++;if(bad<4)console.error('mismatch',selector,i);}}));
console.log(JSON.stringify({checked,mismatches:bad}));process.exit(bad?1:0);
