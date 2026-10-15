// Print the editor preview's composite for one Perfect-Plex step as [[x, y, r, g, b, actor, index], ...]
// (screen coordinates of the preview canvas), or with STEP 'plan' the steps' labels.
// node tools/preview_points.js ROM RECEIVER_SLOT STEP|plan left|right
const fs=require('fs'),path=require('path');global.window=global;
for(const f of ['raw-tile-directory.js','raw-parts.js','animation-preview.js'])require(path.join(__dirname,'../editor',f));
const [romPath,receiver,step,facing]=process.argv.slice(2),rom=new Uint8Array(fs.readFileSync(romPath));
const A=window.RAW_ANIMATION_PREVIEW,P=window.RAW_PARTS,plan=A.plexSteps(rom,Number(receiver));
if(step==='plan'){console.log(JSON.stringify(plan.steps.map(s=>s.label)));process.exit(0);}
const c=A.compose(rom,Number(receiver),plan.steps[Number(step)],facing==='left');
const rgb=v=>[0,5,10].map(s=>Math.floor((v>>s&31)*255/31)),out=[];
// The receiver is drawn first; attacker pixels overwrite it.
for(const [actor,slot,points]of [['receiver',Number(receiver),c.receiver],['attacker',12,c.attacker]]){const pal=P.palette(rom,slot).map(rgb);for(const [k,v]of points){const [x,y]=k.split(',').map(Number);out.push([x,y,...pal[v],actor,v]);}}
console.log(JSON.stringify(out));
