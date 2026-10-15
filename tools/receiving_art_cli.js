// Render one slot's planned receiving drawings with the editor's own code.
//   node tools/receiving_art_cli.js ROM ROYAL SLOT DONOR PLAN.json  -> {palette, poses:[{image:[...144*144], donor:[...], chunks}]}
const fs=require('fs'),path=require('path');global.window=global;
for(const f of ['royal-import-layouts.js','royal-import-core.js','perfect-receiver-layouts.js','raw-tile-directory.js','raw-parts.js','receiving-art.js'])require(path.join(__dirname,'../editor',f));
const [romPath,royalPath,slot,donor,planPath]=process.argv.slice(2);
const rom=new Uint8Array(fs.readFileSync(romPath)),royal=new Uint8Array(fs.readFileSync(royalPath)),R=window.RAW_PERFECT_RECEIVERS,A=window.RAW_RECEIVING_ART;
R.receiving_art=JSON.parse(fs.readFileSync(planPath));
const plan=R.receiving_art.donors[donor];
const poses=A.render(rom,royal,R,Number(slot),{source:'authored',donor:Number(donor)}).map((d,i)=>({image:Array.from(d.image),donor:Array.from(A.donorImage(royal,R,Number(donor),i,plan.colour_map)),chunks:d.chunks}));
console.log(JSON.stringify({palette:window.RAW_PARTS.palette(rom,Number(slot)),poses}));
