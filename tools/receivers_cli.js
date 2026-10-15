// Run the browser's receiving-art installer outside the browser (same code as the editor).
//   node tools/receivers_cli.js install BASE.sfc ROYAL.sfc OUT.sfc   -> prints the install report
//   node tools/receivers_cli.js uninstall ROM.sfc OUT.sfc
//   node tools/receivers_cli.js build RAW.sfc ROYAL.sfc OUT.sfc   -> the importer's slot build only (no editor extras)
//   node tools/receivers_cli.js upgrade-poses ROM.sfc ROYAL.sfc OUT.sfc   -> Mr. Perfect's Royal pose upgrade (no receivers)
//   node tools/receivers_cli.js update ROM.sfc ROYAL.sfc OUT.sfc   -> the editor's Update Perfect-Plex on an unedited import
const fs=require('fs'),path=require('path'),crypto=require('crypto');
global.window=global;
const editor=path.join(__dirname,'..','editor');
for(const f of ['royal-import-layouts.js','royal-import-core.js','nwo-gear-patterns.js','perfect-receiver-layouts.js','raw-tile-directory.js','raw-parts.js','receiving-art.js','perfect-receiver-core.js'])
 if(fs.existsSync(path.join(editor,f)))require(path.join(editor,f));
const [command,...args]=process.argv.slice(2);
const read=p=>new Uint8Array(fs.readFileSync(p));
if(command==='install'){
 const [base,royal,out]=args;
 const result=window.RAW_PERFECT_RECEIVER_CORE.install(read(base),read(royal),window.RAW_PERFECT_RECEIVERS);
 fs.writeFileSync(out,result.bytes);
 result.report.sha256=crypto.createHash('sha256').update(result.bytes).digest('hex');
 console.log(JSON.stringify(result.report));
}else if(command==='uninstall'){
 const [rom,out]=args;fs.writeFileSync(out,window.RAW_PERFECT_RECEIVER_CORE.uninstall(read(rom)));
}else if(command==='build'){
 const [raw,royal,out]=args;const result=window.RAW_ROYAL_IMPORT_CORE.build(read(raw),read(royal),window.RAW_ROYAL_IMPORT_MANIFEST);
 fs.writeFileSync(out,result.bytes);console.log(JSON.stringify(result.report));
}else if(command==='upgrade-poses'){
 const [rom,royal,out]=args;
 const result=window.RAW_ROYAL_IMPORT_CORE.upgradePoses(read(rom),read(royal),window.RAW_ROYAL_IMPORT_MANIFEST);
 fs.writeFileSync(out,result.bytes);
 result.report.sha256=crypto.createHash('sha256').update(result.bytes).digest('hex');
 console.log(JSON.stringify(result.report));
}else if(command==='update'){
 // Same steps as the editor's Update Perfect-Plex button (editor/royal-import.js), without the editor's pending edits.
 const [rom,royal,out]=args,RI=window.RAW_ROYAL_IMPORT_CORE,RC=window.RAW_PERFECT_RECEIVER_CORE,source=read(royal);
 let data=RC.uninstall(read(rom));if(!RI.plexCurrent(data))data=RI.updatePlex(data,source,window.RAW_ROYAL_IMPORT_MANIFEST);
 if(!RI.posesCurrent(data))data=RI.upgradePoses(data,source,window.RAW_ROYAL_IMPORT_MANIFEST).bytes;
 data=RC.install(data,source,window.RAW_PERFECT_RECEIVERS).bytes;fs.writeFileSync(out,data);
 console.log(crypto.createHash('sha256').update(data).digest('hex'));
}else{console.error('usage: install BASE ROYAL OUT | uninstall ROM OUT | upgrade-poses ROM ROYAL OUT | update ROM ROYAL OUT');process.exit(2);}
