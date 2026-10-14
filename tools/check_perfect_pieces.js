// Compare every Mr. Perfect piece (slot 12, primary 0-997 + 1000-1011, secondary 0-721) between two ROMs.
//   node tools/check_perfect_pieces.js BEFORE.sfc AFTER.sfc [--expect-replaced]
// Prints counts of identical and changed pieces; with a manifest, changed pieces must be rows with 'replaces'
// whose new pixels equal the manifest row rendered from Royal (checked by the caller via the report).
const fs=require('fs'),path=require('path');
global.window=global;
const editor=path.join(__dirname,'..','editor');
for(const f of ['royal-import-layouts.js','royal-import-core.js','raw-tile-directory.js','raw-parts.js'])require(path.join(editor,f));
const P=window.RAW_PARTS,RI=window.RAW_ROYAL_IMPORT_CORE,M=window.RAW_ROYAL_IMPORT_MANIFEST;
const [a,b]=process.argv.slice(2).map(p=>new Uint8Array(fs.readFileSync(p)));
const rows=new Map(M.frames.map(f=>[f.kind+':'+f.index,f]));
const out={same:0,changed:0,changed_replaceable:0,changed_other:[]};
for(const [kind,list]of [['primary',[...Array(998).keys(),...Array.from({length:12},(_,i)=>1000+i)]],['secondary',[...Array(722).keys()]]])for(const i of list){
 const x=RI.pieceHash(P.raster(P.resolveIndex(a,12,kind,i).parts)),y=RI.pieceHash(P.raster(P.resolveIndex(b,12,kind,i).parts));
 if(x===y){out.same++;continue;}out.changed++;
 const row=rows.get(kind+':'+i);if(row&&(row.replaces===x||row.replaces_hair===x))out.changed_replaceable++;else out.changed_other.push(kind+'/'+i);
}
console.log(JSON.stringify(out));
