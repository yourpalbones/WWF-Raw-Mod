/* ROM bytes remain local; the published layout contains addresses only. */
'use strict';
const C=window.RAW_EDITOR_MANIFEST, $=id=>document.getElementById(id);
let M=C.characters[0], palettes={};
let rom=null, originals={}, edits={}, paletteEdits={}, history=[], selected=1, cells=[], timer=null, drawing=false;
const canvas=$('sprite'), ctx=canvas.getContext('2d');
function status(message){$('status').textContent=message;}
function decode(data,source){
 let bytes;
 if(source.compressed){bytes=new Uint8Array(32);let cursor=source.offset+4,k=0;
 for(let group=0;group<8;group++){const mask=(data[source.offset+(group>>1)]>>(group%2?0:4))&15;
 for(let bit=8;bit;bit>>=1)bytes[k++]=(mask&bit)?data[cursor++]:0;}
 }else bytes=data.slice(source.offset,source.offset+32);
 const pixels=[];for(let y=0;y<8;y++)for(let x=0;x<8;x++){let c=0;for(let p=0;p<4;p++)c|=((bytes[(p>>1)*16+y*2+(p&1)]>>(7-x))&1)<<p;pixels.push(c);}return pixels;
}
function encode(pixels,packed){const bytes=new Uint8Array(32);pixels.forEach((c,i)=>{for(let p=0;p<4;p++)bytes[(p>>1)*16+(i>>3)*2+(p&1)]|=((c>>p)&1)<<(7-(i&7));});
 if(!packed)return bytes;const masks=new Uint8Array(4),payload=[];for(let i=0;i<32;i++)if(bytes[i]){masks[i>>3]|=(8>>(i%4))<<(i%8<4?4:0);payload.push(bytes[i]);}return new Uint8Array([...masks,...payload]);}
function pixels(key){return edits[key]||originals[key];}
function currentPalette(){paletteEdits=palettes[M.id] ||= {};return paletteEdits;}
function paletteValue(i){return paletteEdits[i] ?? (rom[M.palette_offset+i*2]|rom[M.palette_offset+i*2+1]<<8);}
function palette(){return Array.from({length:16},(_,i)=>{let v=paletteValue(i);return [0,5,10].map(s=>Math.floor(((v>>s)&31)*255/31));});}
function refreshColors(){
 const colors=palette();
 $('colors').replaceChildren(...colors.slice(1).map((c,i)=>{const b=document.createElement('button');b.className='swatch'+(i+1===selected?' selected':'');b.style.background=`rgb(${c.join(',')})`;b.title=`Native color ${i+1}`;b.setAttribute('aria-label',b.title);b.onclick=()=>{selected=i+1;render();};return b;}));
 $('palette-color').value='#'+colors[selected].map(v=>v.toString(16).padStart(2,'0')).join('');
 const count=cells.filter(c=>c && pixels(c.key)[c.index]===selected).length;
 $('palette-usage').textContent=`Color ${selected} is used by ${count} visible pixels in this pose. Changing it recolors every use of this slot, including gear, skin or hair that shares it. Uses outside these captured poses remain unverified.`;
 $('palette-restore').disabled=!Object.hasOwn(paletteEdits,selected);
}
function render(){if(!rom)return;currentPalette();const pose=M.poses[Number($('pose').value)], colors=palette();canvas.width=pose.width;canvas.height=pose.height;canvas.style.width=`${pose.width*Number($('zoom').value)}px`;canvas.style.height=`${pose.height*Number($('zoom').value)}px`;cells=Array(pose.width*pose.height).fill(null);const image=ctx.createImageData(pose.width,pose.height);
 for(const part of [...pose.parts].reverse())for(let y=0;y<part.size;y++)for(let x=0;x<part.size;x++){
 const sx=part.hflip?part.size-1-x:x,sy=part.vflip?part.size-1-y:y,key=part.tiles[(sy>>3)*(part.size>>3)+(sx>>3)];if(key===null)continue;
 const index=(sy%8)*8+sx%8,color=pixels(key)[index];if(!color)continue;const dest=(part.y+y)*pose.width+part.x+x;image.data.set([...colors[color],255],dest*4);cells[dest]={key,index};}
 renderSelection();ctx.putImageData(image,0,0);refreshColors();$('undo').disabled=!history.length;
 const shared=Object.keys(edits).filter(key=>M.sources[key] && C.characters.some(c=>c.id!==M.id && c.sources[key]));
 const users=C.characters.filter(c=>c.id!==M.id && shared.some(key=>c.sources[key])).map(c=>c.character);
 $('shared').textContent=users.length?'Edited tiles in this wrestler are also used by: '+users.join(', ')+'. Changes apply to those shared sources too.':'No edited sources shared with another loaded wrestler are detected. Shared uses outside these captures remain unverified.';
 $('details').textContent=`${Object.keys(edits).length} edited tile sources; ${Object.values(palettes).reduce((n,p)=>n+Object.keys(p).length,0)} changed palette colors across the roster. Edits follow the same source into every loaded pose that uses it. Other animations and shared users remain unverified.`;
}
function remember(){history.push(structuredClone({edits,palettes,selectionEdits}));if(history.length>100)history.shift();}
function paint(event){if(!rom)return;const rect=canvas.getBoundingClientRect(),x=Math.floor((event.clientX-rect.left)*canvas.width/rect.width),y=Math.floor((event.clientY-rect.top)*canvas.height/rect.height);if(x<0||y<0||x>=canvas.width||y>=canvas.height)return;const cell=cells[y*canvas.width+x];if(!cell)return;
 const copy=pixels(cell.key).slice();copy[cell.index]=selected;
 if(copy.every((c,i)=>c===originals[cell.key][i]))delete edits[cell.key];else edits[cell.key]=copy;render();}
function download(name,data,type){const url=URL.createObjectURL(new Blob([data],{type})),link=document.createElement('a');link.href=url;link.download=name;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
function patch(){if(!rom)throw Error('Load a ROM first');const selection=selectionRecords(),result=new Uint8Array(selection.expanded?0x400000:rom.length),records=[];result.fill(255);result.set(rom);for(const [key,p] of Object.entries(edits)){const source=C.sources[key],packet=encode(p,source.compressed);if(packet.length>source.length)throw Error(`Tile at ${source.offset.toString(16)} needs more space. Undo or simplify that edit; relocation is not supported yet.`);result.set(packet,source.offset);records.push([source.offset,packet]);}
 for(const character of C.characters)for(const [index,value] of Object.entries(palettes[character.id]||{})){const offset=character.palette_offset+Number(index)*2,packet=new Uint8Array([value&255,value>>8]);result.set(packet,offset);records.push([offset,packet]);}
 for(const [offset,packet]of selection.records){result.set(packet,offset);records.push([offset,packet]);}
 // 3 MiB HiROM is mirrored to 4 MiB for the native checksum.
 let checksum=0;for(let i=0;i<result.length;i++)checksum=(checksum+result[i]*(result.length===0x300000&&i>=0x200000?2:1))&65535;
 const complement=checksum^65535;records.push([0xffdc,new Uint8Array([complement&255,complement>>8,checksum&255,checksum>>8])]);
 const out=[80,65,84,67,72];if(selection.expanded)for(let address=0x300000;address<0x400000;){const length=Math.min(65535,0x400000-address);out.push(address>>16,address>>8&255,address&255,0,0,length>>8,length&255,255);address+=length;}for(const [offset,packet]of records)out.push(offset>>16,(offset>>8)&255,offset&255,packet.length>>8,packet.length&255,...packet);out.push(69,79,70);return new Uint8Array(out);}
function stop(){clearInterval(timer);timer=null;$('play').textContent='Play poses';}
$('rom').onchange=async event=>{stop();rom=null;try{let bytes=new Uint8Array(await event.target.files[0].arrayBuffer());if(bytes.length%1024===512)bytes=bytes.slice(512);const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),b=>b.toString(16).padStart(2,'0')).join('');if(digest!==M.original_sha256)throw Error('This version requires the original, unmodified WWF Raw USA ROM.');rom=bytes;originals={};edits={};palettes={};selectionEdits={};selectionOriginals={};paletteEdits={};history=[];for(const [key,source]of Object.entries(C.sources))originals[key]=decode(rom,source);
 $('wrestler').replaceChildren(...C.characters.map(c=>new Option(c.character,c.id)));$('wrestler').value=M.id;loadCharacter(M.id);for(const id of ['wrestler','pose','play','reset','save','patch','png','project','palette-color','palette-apply','portrait-import','bio-name','bio-from','bio-weight','bio-height','bio-special','bio-apply','selection-restore'])$(id).disabled=false;status('Original ROM verified. Paint a pose or preview the captured layouts.');render();}catch(e){for(const id of ['wrestler','pose','play','reset','save','patch','png','project','undo','palette-color','palette-apply','palette-restore','portrait-import','bio-name','bio-from','bio-weight','bio-height','bio-special','bio-apply','selection-restore'])$(id).disabled=true;ctx.clearRect(0,0,canvas.width,canvas.height);status(e.message);}};
function loadCharacter(id){stop();M=C.characters.find(c=>c.id===id);$('character-title').textContent=M.character+' · Original WWF Raw sprites · Captured poses';$('pose').replaceChildren(...M.poses.map((p,i)=>new Option(p.label,i)));render();}
$('wrestler').onchange=()=>loadCharacter($('wrestler').value);
$('pose').onchange=()=>{stop();render();};$('zoom').onchange=render;
canvas.onpointerdown=e=>{if(!rom)return;stop();remember();drawing=true;canvas.setPointerCapture(e.pointerId);paint(e);};canvas.onpointermove=e=>{if(drawing)paint(e);};canvas.onpointerup=canvas.onpointercancel=()=>{drawing=false;};
$('undo').onclick=()=>{const previous=history.pop();if(previous){edits=previous.edits;palettes=previous.palettes;selectionEdits=previous.selectionEdits;}render();};$('reset').onclick=()=>{remember();edits={};palettes={};selectionEdits={};render();};
$('palette-apply').onclick=()=>{if(!rom)return;const hex=$('palette-color').value;const rgb=[1,3,5].map(i=>Math.round(parseInt(hex.slice(i,i+2),16)*31/255));const value=rgb[0]|rgb[1]<<5|rgb[2]<<10;if(value===paletteValue(selected))return;remember();const original=rom[M.palette_offset+selected*2]|rom[M.palette_offset+selected*2+1]<<8;if(value===original)delete paletteEdits[selected];else paletteEdits[selected]=value;render();status('Color updated to the nearest SNES color. Preview other poses to check every visible use.');};
$('palette-restore').onclick=()=>{if(!rom)return;remember();delete paletteEdits[selected];render();};
$('play').onclick=()=>{if(timer){stop();return;}$('play').textContent='Stop';timer=setInterval(()=>{$('pose').value=(Number($('pose').value)+1)%M.poses.length;render();},160);};
$('save').onclick=()=>download('raw-gear-project.json',JSON.stringify({version:4,original_sha256:C.original_sha256,edits,palettes,selection_edits:selectionEdits},null,2),'application/json');
$('project').onchange=async event=>{try{
 const project=JSON.parse(await event.target.files[0].text());
 if(![1,2,3,4].includes(project.version)||project.original_sha256!==C.original_sha256||!project.edits||typeof project.edits!=='object'||Array.isArray(project.edits))throw Error('Project does not match this editor.');
 for(const [key,p]of Object.entries(project.edits))if(!Object.hasOwn(C.sources,key)||!Array.isArray(p)||p.length!==64||p.some((v,i)=>!Number.isInteger(v)||v<0||v>15||((originals[key][i]===0)!==(v===0))))throw Error('Project contains invalid tile edits.');
 const colors=project.version>=3?project.palettes:{'1':project.version===1?{}:project.palette_edits};
 if(!colors||typeof colors!=='object'||Array.isArray(colors))throw Error('Project contains invalid palette edits.');
 for(const [id,p]of Object.entries(colors))if(!C.characters.some(c=>c.id===id)||!p||typeof p!=='object'||Array.isArray(p)||Object.entries(p).some(([key,v])=>!/^([1-9]|1[0-5])$/.test(key)||!Number.isInteger(v)||v<0||v>32767))throw Error('Project contains invalid palette edits.');
 const selection=project.version===4?project.selection_edits:{};validateSelection(selection);
 remember();edits=structuredClone(project.edits);palettes=structuredClone(colors);selectionEdits=structuredClone(selection);render();status('Project loaded. Edits still need emulator verification.');
 }catch(e){status(e.message);}event.target.value='';};
$('patch').onclick=()=>{try{download('raw-gear.ips',patch(),'application/octet-stream');status('Patch exported. Apply it to a copy of your original ROM, then test in an emulator.');}catch(e){status(e.message);}};
$('png').onclick=()=>canvas.toBlob(blob=>download(M.character.toLowerCase().replaceAll(' ','-')+'-pose.png',blob,'image/png'));
