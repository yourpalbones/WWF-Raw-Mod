// Compare editor/raw-parts.js with tools/raw_parts.py on a ROM: node tools/raw_parts_parity.js ROM PY_JSON
const fs=require('fs'),path=require('path');global.window=global;
require(path.join(__dirname,'../editor/raw-tile-directory.js'));require(path.join(__dirname,'../editor/raw-parts.js'));
const rom=new Uint8Array(fs.readFileSync(process.argv[2])),expected=JSON.parse(fs.readFileSync(process.argv[3]));
let checked=0,bad=0;
for(const e of expected){const r=window.RAW_PARTS.resolvePart(rom,e.slot,e.part);const got=r.parts.map(p=>[p.x,p.y,p.size,p.hflip,p.vflip,p.sources.map(s=>s.offset),p.pixels]);checked++;if(JSON.stringify(got)!==JSON.stringify(e.parts)){bad++;if(bad<4)console.error('mismatch',e.slot,e.part.toString(16));}}
console.log(JSON.stringify({checked,mismatches:bad}));process.exit(bad?1:0);
