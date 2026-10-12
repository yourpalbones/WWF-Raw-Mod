/* Simple workflow shell, pose-image import and local playable-ROM export. */
function showPanel(name){stop();for(const key of ['sprite','profile','export']){$(key+'-panel').hidden=key!==name;$('tab-'+key).setAttribute('aria-selected',String(key===name));}}
for(const name of ['sprite','profile','export'])$('tab-'+name).onclick=()=>showPanel(name);
function refreshApp(){$('scott-reference-card').hidden=!rom||!['5','9','10'].includes(M.id);$('scott-reference-apply').disabled=!rom||hasNativeGear(rom,M.id);for(const id of ['song-import','song-transpose','song-instrument','song-loop','song-preview','song-stop','song-restore'])$(id).disabled=!rom;document.body.classList.toggle('has-rom',Boolean(rom));$('rom-status').textContent=rom?(baseDigest===C.original_sha256?'Original ROM verified':'Edited ROM loaded'):'No ROM loaded';if(!rom)return;
 $('reference-gear-title').textContent=({5:'Scott Hall — fixed Edge gear',9:'Syxx — black/red gear and bandana',10:'Kevin Nash — red gear'})[M.id]||'Reference gear';$('scott-reference-apply').textContent=M.id==='5'?'Apply fixed Scott gear':'Apply '+(M.id==='9'?'Syxx':'Nash')+' reference gear';for(const option of $('wrestler').options)option.textContent=selectionState(option.value).bio.name;
 $('character-title').textContent=selectionState(M.id).bio.name+' · Original slot: '+M.character;
 const tiles=Object.keys(edits).length,colors=Object.values(palettes).reduce((n,p)=>n+Object.keys(p).length,0),profiles=Object.values(selectionEdits).length;
 $('change-summary').textContent=tiles||colors||profiles?`${tiles} tile edits · ${colors} color edits · ${profiles} profile edits`:'No changes yet. Choose an editing tab to begin.';
 $('sprite-import-hint').textContent=`Import a ${canvas.width} × ${canvas.height} PNG for this pose. Keep its transparency and outline. Colors are matched to the current wrestler palette.`;
 $('portrait-thumb').getContext('2d').drawImage($('portrait'),0,0);
}
function importPosePixels(rgba,width,height){
 if(width!==canvas.width||height!==canvas.height)throw Error(`This pose needs a ${canvas.width} × ${canvas.height} PNG. Save the pose image first to get the right size.`);
 const colors=palette(),updates=new Map();
 for(let index=0;index<cells.length;index++){
  const cell=cells[index],alpha=rgba[index*4+3];
  if(!cell){if(alpha!==0)throw Error('The imported image changes the outline. Keep the original transparent pixels.');continue;}
  if(alpha!==255)throw Error('Keep visible pixels fully opaque and preserve the original outline.');
  let best=pixels(cell.key)[cell.index],distance=colors[best].reduce((n,v,c)=>n+(rgba[index*4+c]-v)**2,0);for(let color=1;color<16;color++){let d=0;for(let c=0;c<3;c++)d+=(rgba[index*4+c]-colors[color][c])**2;if(d<distance){distance=d;best=color;}}
  const key=cell.key+':'+cell.index;if(updates.has(key)&&updates.get(key).color!==best)throw Error('Two pixels share the same game tile but have different imported colors. Give those pixels the same color.');
  updates.set(key,{...cell,color:best});
 }
 const next=structuredClone(edits);for(const update of updates.values()){const tile=next[update.key] ||= originals[update.key].slice();tile[update.index]=update.color;}
 for(const key of Object.keys(next))if(next[key].every((v,i)=>v===originals[key][i]))delete next[key];
 // Check storage before applying; imported art must not silently corrupt neighbors.
 for(const key of new Set([...updates.values()].map(u=>u.key))){const source=C.sources[key];if(encode(next[key]||originals[key],source.compressed).length>source.length)throw Error('This image needs more compressed tile space. Simplify its details or adjust the colors before importing.');}
 remember();edits=next;render();
}
$('sprite-import').onchange=async event=>{try{if(!rom)throw Error('Load a ROM first');const file=event.target.files[0];if(!file||file.size>16*1024*1024)throw Error('Choose a PNG smaller than 16 MB.');stop();const id=M.id,pose=$('pose').value,bitmap=await createImageBitmap(file);if(id!==M.id||pose!==$('pose').value){bitmap.close();throw Error('The selected pose changed. Import the image again.');}const temp=document.createElement('canvas');temp.width=bitmap.width;temp.height=bitmap.height;const context=temp.getContext('2d');context.drawImage(bitmap,0,0);bitmap.close();importPosePixels(context.getImageData(0,0,temp.width,temp.height).data,temp.width,temp.height);status('Pose image imported. Preview the other poses to check shared tiles, then save your project.');}catch(e){status(e.message);}event.target.value='';};
function playableROM(){const bytes=patch();let result=rom.slice(),cursor=5;while(String.fromCharCode(...bytes.slice(cursor,cursor+3))!=='EOF'){const offset=bytes[cursor]<<16|bytes[cursor+1]<<8|bytes[cursor+2];let length=bytes[cursor+3]<<8|bytes[cursor+4];cursor+=5;let packet;if(length){packet=bytes.slice(cursor,cursor+length);cursor+=length;}else{length=bytes[cursor]<<8|bytes[cursor+1];packet=new Uint8Array(length).fill(bytes[cursor+2]);cursor+=3;}if(offset+length>result.length){const expanded=new Uint8Array(offset+length);expanded.fill(255);expanded.set(result);result=expanded;}result.set(packet,offset);}return result;}
$('rom-export').onclick=()=>{try{download('WWF-Raw-edited.sfc',playableROM(),'application/octet-stream');status('Playable ROM saved. Open WWF-Raw-edited.sfc in your emulator. Save your project too if you want to keep editing.');}catch(e){status(e.message);}};
