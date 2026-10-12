/* Resolve Scott's isolated ExHiROM assets without bundling game pixels. */
const SCOTT=window.RAW_SCOTT_MANIFEST;
const baseRosterSources=structuredClone(C.sources),baseScottCharacter=structuredClone(C.characters.find(c=>c.id==='5'));
function hasScottGear(data){return data.length===0x600000&&String.fromCharCode(...data.slice(SCOTT.signature_offset,SCOTT.signature_offset+SCOTT.signature.length))===SCOTT.signature;}
function activateScottSources(data){
 const active=hasScottGear(data),character=structuredClone(baseScottCharacter),mapping={},read24=p=>data[p]|data[p+1]<<8|data[p+2]<<16;
 C.sources=structuredClone(baseRosterSources);character.sources={};
 for(const [key,meta]of Object.entries(SCOTT.sources)){
  let source={offset:meta.offset,compressed:meta.compressed,length:meta.length};
  if(meta.private_packet_offset){source=active?{offset:meta.private_packet_offset,compressed:true,length:36}:{offset:meta.original_offset,compressed:meta.original_compressed,length:meta.original_length};}
  else if(active&&meta.frame_kind){const table=meta.frame_kind==='primary'?SCOTT.primary_table:SCOTT.secondary_table,low=data[table+meta.frame_index*3]|data[table+meta.frame_index*3+1]<<8;if(low){const descriptor=data[table+meta.frame_index*3+2]*65536+low,field=descriptor+meta.field_relative,id=data[field]|data[field+1]<<8;if(id>=SCOTT.private_tag){source={offset:read24(SCOTT.pointer_table+(id&SCOTT.private_mask)*3),compressed:true,length:36};}}}
  if(source.offset+source.length>data.length||source.offset<0)throw Error('Scott sprite data points outside the loaded ROM.');
  const canonical=String(source.offset);mapping[key]=canonical;
  if(C.sources[canonical]&&(C.sources[canonical].offset!==source.offset||C.sources[canonical].compressed!==source.compressed))throw Error('Conflicting Scott sprite source.');
  C.sources[canonical]=source;character.sources[canonical]=source;
 }
 character.poses=SCOTT.poses.map(p=>({...structuredClone(p),parts:p.parts.map(part=>({...part,tiles:part.tiles.map(key=>key===null?null:mapping[key])}))}));character.scope=SCOTT.coverage;
 C.characters[C.characters.findIndex(c=>c.id==='5')]=character;
}
async function applyScottReferenceGear(base){
 const recipe=window.RAW_SCOTT_GEAR_PATTERNS;
 if(hasScottGear(base))throw Error('Scott reference gear is already in this ROM. Use the sprite tools to edit it.');
 if(![0x300000,0x400000].includes(base.length))throw Error('Load a supported original or edited WWF Raw ROM first.');
 for(const p of recipe.programs)if(p.expected.some((value,i)=>base[p.hook+i]!==value))throw Error('This ROM already changes the sprite engine. The reference gear cannot safely be applied.');
 const fingerprint=[],rows=[];
 for(const f of recipe.frames){const tiles=[];for(const t of f.tiles){const old=decode(base,{offset:t.source,compressed:t.compressed,length:t.length});fingerprint.push(...encode(old,false));const pixels=old.slice();for(const [i,value]of t.edits){if(!pixels[i])throw Error('Scott artwork has changed. The reference gear does not match this ROM.');pixels[i]=value;}tiles.push({relative:t.relative,pixels});}fingerprint.push(...base.slice(f.offset,f.offset+f.length));rows.push({frame:f,tiles});}
 const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new Uint8Array(fingerprint))),b=>b.toString(16).padStart(2,'0')).join('');
 if(digest!==recipe.source_fingerprint)throw Error('This ROM has different Scott sprite artwork. Keep its edits or load a matching original sprite version before applying the reference gear.');
 const result=new Uint8Array(0x600000);result.fill(255);result.set(base);result.fill(0,recipe.primary_table,recipe.primary_table+998*3);result.fill(0,recipe.secondary_table,recipe.secondary_table+722*3);let frameCursor=recipe.frames_start,packetCursor=recipe.packets_start;const tiles=new Map(),descriptors=new Map();
 for(const {frame:f,tiles:fields}of rows){const descriptor=base.slice(f.offset,f.offset+f.length);for(const t of fields){const raw=encode(t.pixels,false),key=Array.from(raw).join(',');let id=tiles.get(key);if(id===undefined){id=tiles.size;tiles.set(key,id);if((packetCursor&65535)+36>65536)packetCursor=(packetCursor+65535)&~65535;const packet=encode(t.pixels,true);if(packetCursor+36>recipe.packets_end||recipe.pointers+id*3+3>recipe.pointer_end)throw Error('Scott graphics exceed their reserved storage.');result.set(packet,packetCursor);result.set([packetCursor&255,packetCursor>>8&255,packetCursor>>16],recipe.pointers+id*3);packetCursor+=36;}descriptor[t.relative]=(0xc000|id)&255;descriptor[t.relative+1]=(0xc000|id)>>8;}
  const key=Array.from(descriptor).join(',');let address=descriptors.get(key);if(address===undefined){if((frameCursor&65535)+descriptor.length>65536)frameCursor=(frameCursor+65535)&~65535;if((frameCursor&65535)===0)frameCursor+=256;address=frameCursor;if(frameCursor+descriptor.length>recipe.frames_end)throw Error('Scott frames exceed their reserved storage.');result.set(descriptor,frameCursor);descriptors.set(key,address);frameCursor+=descriptor.length;}
  const table=f.kind==='primary'?recipe.primary_table:recipe.secondary_table;result.set([address&255,address>>8&255,address>>16],table+f.index*3);
 }
 for(const [i,color]of Object.entries(recipe.palette))result.set([color&255,color>>8],recipe.palette_offset+Number(i)*2);
 for(const p of recipe.programs){result.set(p.code,p.offset);result.set([0x5c,p.offset&255,p.offset>>8&255,p.offset>>16],p.hook);}
 result.set(Array.from(recipe.signature,c=>c.charCodeAt(0)),recipe.signature_offset);result[0xffd5]=0x25;result[0xffd7]=13;result.set(result.slice(0,0x10000),0x400000);for(const p of[0xffdc,0x40ffdc])result.set([255,255,0,0],p);let sum=0;for(let i=0;i<result.length;i++)sum=(sum+result[i]*(i>=0x400000?2:1))&65535;for(const p of[0xffdc,0x40ffdc])result.set([(sum^65535)&255,(sum^65535)>>8,sum&255,sum>>8],p);return result;
}
$('scott-reference-apply').onclick=async()=>{try{if(!rom)throw Error('Load your ROM first.');$('scott-reference-apply').disabled=true;status('Applying Scott reference gear and checking your existing sprites…');const next=await applyScottReferenceGear(playableROM());validateLoadedMod(next);const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',next)),b=>b.toString(16).padStart(2,'0')).join('');stop();stopMusicPreview();rom=next;baseDigest=digest;activateScottSources(rom);originals={};edits={};palettes={};selectionEdits={};selectionOriginals={};profileOriginals={};nativeNameFont=null;hudOriginals={};hudFont=null;paletteEdits={};history=[];for(const [key,source]of Object.entries(C.sources))originals[key]=decode(rom,source);loadCharacter('5');$('wrestler').value='5';render();status('Scott reference gear applied. Your portraits, bios and songs are preserved. Save playable ROM to keep this version.');}catch(e){status(e.message);}finally{$('scott-reference-apply').disabled=!rom||hasScottGear(rom);}};
