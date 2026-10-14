/* Roster-16 preview integration. ROM bytes stay local; Claude's source editor is unchanged. */
'use strict';
const V01={baseline:structuredClone(C),oldValidate:validateLoadedMod,oldActivate:activateImportedWorker,oldReset:resetImportedMetadata,oldPatch:patch,oldRefresh:refreshApp,oldRoyal:refreshRoyalImport,oldMatch:matchNamePixels};
const vword=(d,a)=>d[a]|d[a+1]<<8,vlong=(d,a)=>vword(d,a)|d[a+2]<<16;
const vphysical=a=>a>=0x400000&&a<0x7e0000?a:a&0x3fffff;
const vcpu=a=>a>=0x300000&&a<0x400000?a|0xc00000:a;
const vbytes=a=>new Uint8Array([a&255,a>>>8&255,a>>>16&255]);
function vexpanded(data){return data.length===0x800000&&data[0x19d43f]===16&&String.fromCharCode(...data.slice(0x34ef00,0x34ef0d))==='FLAIR16-PROBE';}
resetImportedMetadata=function(){V01.oldReset();H.table=0x1a4451;for(const key of Object.keys(C))delete C[key];Object.assign(C,structuredClone(V01.baseline));};
validateLoadedMod=function(data){if(!vexpanded(data))return V01.oldValidate(data);if(String.fromCharCode(...data.slice(0xffc0,0xffd5)).trim()!=='WWF RAW'||data[0xffd5]!==0x25)throw Error('Choose the supported 16-wrestler Raw preview.');let sum=0;for(const b of data)sum=(sum+b)&65535;if(sum!==vword(data,0xffde)||(vword(data,0xffdc)^sum)!==65535)throw Error('The ROM checksum is invalid. Choose a complete saved ROM.');if(vword(data,0x40ffde)!==sum)throw Error('The expanded ROM header is incomplete.');for(let i=0;i<16;i++){const r=0x708000+i*45;for(const field of [0,4,8,12,16,20,24]){const p=vphysical(vlong(data,r+field));if(p<0||p>=data.length)throw Error('Wrestler graphics pointer is outside the ROM.');}}};
function vextra(data,slot,bank,descriptorBank,name,pools){
 const base=bank<<16,character={id:String(slot),character:name,palette_offset:base+0x6a00,sources:{},poses:[],v01:true,v01Pools:pools},record=0x708000+slot*45;
 const readPointer=field=>vphysical(vlong(data,record+field));
 S.characters[String(slot)]={...structuredClone(S.characters['1']),record,portrait_offset:readPointer(0),portrait_length:15604,palette_offset:readPointer(4)+64,monitor_offset:readPointer(20),monitor_palette_offset:readPointer(24),logo_offset:readPointer(8),logo_map_offset:readPointer(12),logo_palette_offset:readPointer(16),logo_tile_limit:146,theme_offset:record+44,theme:data[record+44],announcer_monitor_word:0x70e400+slot*2,announcer_monitor_bank:0x70e420+slot*2,announcer_palette_word:0x70e440+slot*2,announcer_palette_bank:0x70e460+slot*2,fields:{name:record+28,from:record+30,weight:record+32,height:record+36,special:record+38}};
 const labels=root=>root>=0xf000?'Leg-drop study':root>=0x4c08&&root<=0x4cfc?'Grapple study':root>=0x55ee&&root<=0x565c?'Body-slam study':root>=0x47be&&root<=0x47f2?'Recovery study':root>=0x49e2&&root<=0x4a0c?'Punch':root>=0x4a36&&root<=0x4a60?'Kick':root>=0x48d2&&root<=0x48ee?'Run':'Stance and walking';
 for(let i=0;i<256;i++){
  const root=vword(data,base+0x7000+i*4);if(root===65535)break;const at=vphysical(vlong(data,base+0xb000+i*3)),count=data[at],large=data[at+1];if(count<1||count>17||large>count)throw Error('Added wrestler descriptor is invalid.');let cursor=at+2,parts=[];
  for(let n=0;n<count;n++){
   if(data[cursor++]!==0)throw Error('Unsupported added wrestler position encoding.');let x=data[cursor++]&127,y=data[cursor++]&127;const size=n<large?16:8;x=x&64?x-128:x;y-=105;const tiles=[];
   for(let t=0;t<size*size/64;t++){
    const id=vword(data,cursor);cursor+=2;if(id<0xc000)throw Error('Added wrestler tile is not private.');const pointer=descriptorBank*65536+0x8000+(id&16383)*3,offset=vphysical(vlong(data,pointer));if(!pools.some(([a,b])=>offset>=a&&offset+4<=b))throw Error('Added wrestler packet is outside its storage.');let length=4;for(let k=0;k<4;k++){let bits=data[offset+k];while(bits){length+=bits&1;bits>>=1;}}if(offset+length>data.length)throw Error('Added wrestler tile is truncated.');const key=`v01:${slot}:${id&16383}`;character.sources[key]={offset,compressed:true,length,pointer_offsets:[pointer],v01Slot:slot,v01Tile:id&16383};tiles.push(key);
   }
   parts.push({x:x+80,y:y+112,size,hflip:false,vflip:false,tiles});
  }
  character.v01DescriptorEnd=Math.max(character.v01DescriptorEnd||0,cursor);
  character.poses.push({label:`${labels(root)} · ${i+1}`,category:'Imported full-body poses',v01Root:root,width:160,height:160,parts});
 }
 if(!character.poses.length)throw Error('Added wrestler has no pose metadata.');Object.assign(C.sources,character.sources);C.characters.push(character);
}
activateImportedWorker=function(data){if(!vexpanded(data))return V01.oldActivate(data);const compatible=data.slice();compatible[0x19d43f]=13;V01.oldActivate(compatible);
 vextra(data,13,0x4a,0x54,'Hulk Hogan',[[0x550000,0x558000],[0x55b000,0x560000],[0x54a000,0x550000]]);
 vextra(data,14,0x5d,0x5e,'Big Boss Man',[[0x6d0000,0x6d8000],[0x6db000,0x6e0000],[0x5ea000,0x5f0000]]);
 vextra(data,15,0x34,0x35,'Ric Flair',[[0x3b0000,0x3b8000],[0x3bb000,0x3c0000],[0x35a000,0x360000]]);
 C.characters.find(c=>c.id==='15').v01Pools=C.characters.find(c=>c.id==='15').v01Pools.filter(([a])=>a!==0x3bb000);H.table=0x349000;H.destination=0x3b8000;for(const meta of Object.values(S.characters))meta.logo_tile_limit=Math.max(meta.logo_tile_limit,146);
};
refreshRoyalImport=function(){V01.oldRoyal();const card=$('royal-status').closest('.card');if(card)card.hidden=Boolean(rom&&vexpanded(rom));if(rom&&vexpanded(rom)){for(const id of ['royal-add','royal-update'])if($(id))$(id).disabled=true;$('royal-status').textContent='16-wrestler preview loaded. Save a project to keep editing this roster.';}};
refreshApp=function(){V01.oldRefresh();if(rom&&vexpanded(rom)){$('scott-reference-apply').disabled=true;if(M.v01)$('character-title').textContent=selectionState(M.id).bio.name+' · Imported poses · Other moves unfinished';}};
matchNamePixels=function(name){if(!rom||!vexpanded(rom))return V01.oldMatch(name);const saved=C.characters;C.characters=saved.filter(c=>Number(c.id)<12);try{const f=matchFont();f.I ||= {width:3,pixels:[0,0,0,1,1,1,0,1,0,0,1,0,0,1,0,0,1,0,1,1,1,0,0,0]};return V01.oldMatch(name);}finally{C.characters=saved;}};
function v16Selection(result){
 const records=[],put=(at,bytes)=>{if(!Number.isInteger(at)||at<0||at+bytes.length>result.length)throw Error('Profile write is outside the ROM.');result.set(bytes,at);records.push([at,bytes]);},pointer=(at,a)=>put(at,vbytes(vcpu(a))),palette=colors=>new Uint8Array(colors.flatMap(c=>[c&255,c>>8]));
 const allBios=C.characters.map(c=>[c.id,selectionState(c.id).bio]),strings=new Map(),regions=[{offset:0x2efaf5,length:540},{offset:0x2eff49,length:183}];
 for(const [id,bio]of allBios){const meta=S.characters[id];for(const [field,value]of Object.entries(bio)){
  if(field==='weight'){const bytes=new Uint8Array(4);bytes.set(Array.from(value,c=>c.charCodeAt(0)));put(meta.fields.weight,bytes);continue;}
  let address=strings.get(value);if(address===undefined){const bytes=new Uint8Array(Array.from(value.replaceAll('\n','\r')+'\0',c=>c.charCodeAt(0))),region=regions.find(r=>r.length>=bytes.length);if(!region)throw Error('The combined bios are too long. Shorten some text before saving.');address=region.offset;region.offset+=bytes.length;region.length-=bytes.length;strings.set(value,address);put(address,bytes);}put(meta.fields[field],new Uint8Array([address&255,address>>8&255]));
 }}
 const displacedLogo=[0x4a9100,0x4ad100,0x5d9100,0x5dd100],extraLogo=[0x349100,0x34d100,0x4a7200,0x5d7200];
 for(const [id,edit]of Object.entries(selectionEdits)){
  const n=Number(id),meta=S.characters[id];validateProfileAssets(edit,id);
  if(edit.portrait){const address=n<12?0x300000+n*0x4000:meta.portrait_offset;put(address,portraitPacket(edit.portrait.pixels));pointer(meta.record,address);put(meta.palette_offset,palette(edit.portrait.colors));}
  if(edit.monitor){const address=n<12?0x330000+n*0x1000:meta.monitor_offset,colors=n<12?address+0xf00:meta.monitor_palette_offset;const bytes=nativeBlock(imageTiles(edit.monitor.pixels,48,48,8));if(bytes.length>0xb00)throw Error('This monitor image needs more storage.');put(address,bytes);put(colors,palette(edit.monitor.colors));pointer(meta.record+20,address);pointer(meta.record+24,colors);if(n<12){pointer(meta.monitor_directory_offset,address);pointer(meta.monitor_palette_directory_offset,colors);}}
  if(edit.logo||edit.logoName){const logo=edit.logo||generateNameLogo(edit.logoName,id),packed=logoTiles(logo,id),address=n<4?displacedLogo[n]:n<12?0x340000+n*0x8000:extraLogo[n-12];const graphics=nativeBlock(packed.graphics),map=nativeBlock(packed.map);const tight=n>=14,mapAt=tight?0xd00:0x1400,paletteAt=tight?0x1560:0x1dc0;if(graphics.length>mapAt||map.length>0x900)throw Error('This name image exceeds its reserved storage.');put(address,graphics);put(address+mapAt,map);put(address+paletteAt,palette(logo.colors));pointer(meta.record+8,address);pointer(meta.record+12,address+mapAt);pointer(meta.record+16,address+paletteAt);}
  if(edit.theme!==undefined)put(meta.theme_offset,new Uint8Array([edit.theme]));
 }
 // Rebuild the word-stride announcer directories for every slot.
 for(const [at,field,bank]of [[0x70e400,20,false],[0x70e420,20,true],[0x70e440,24,false],[0x70e460,24,true]]){const bytes=new Uint8Array(32);for(let i=0;i<16;i++){const p=vlong(result,0x708000+i*45+field),value=bank?p>>>16:p&65535;bytes[i*2]=value&255;bytes[i*2+1]=value>>8;}put(at,bytes);}
 if(Object.values(selectionEdits).some(e=>e.hudName||e.hud)){
  const graphics=new Uint8Array(8192);graphics.set(decodePortrait(rom,hudSource(rom)));const pool=[...Array.from({length:79},(_,i)=>64+i),...Array.from({length:19},(_,i)=>237+i)],lookup=new Map([[Array(32).fill(0).join(','),0]]);let used=0;
  for(const c of C.characters){const data=imageTiles(matchState(c.id),64,8,4),indices=new Uint8Array(8);for(let i=0;i<8;i++){const bytes=data.slice(i*32,i*32+32),key=Array.from(bytes).join(',');let n=lookup.get(key);if(n===undefined){n=pool[used++];if(n===undefined)throw Error('These match names need more space. Shorten some names.');lookup.set(key,n);graphics.set(bytes,n*32);}indices[i]=n;}put(H.table+Number(c.id)*8,indices);}
  put(H.destination,nativeBlock(graphics));put(H.bankOperand,new Uint8Array([vcpu(H.destination)>>>16]));put(H.addressOperand,new Uint8Array([H.destination&255,H.destination>>8&255]));
 }
 for(const [at,bytes]of customMusicRecords().records)put(at,bytes);
 return records;
}
patch=function(){if(!rom||!vexpanded(rom))return V01.oldPatch();const result=rom.slice();
 // Repack each added wrestler in its own protected pools; never share packets
 // between workers, and never write over the HUD atlas or descriptor directory.
 for(const c of C.characters.filter(c=>c.v01)){
  for(const [a,b]of c.v01Pools)result.fill(255,a,b);let pool=0,cursor=c.v01Pools[0][0];
  for(const [key,s]of Object.entries(c.sources).sort((a,b)=>a[1].v01Tile-b[1].v01Tile)){
   const bytes=encode(pixels(key),true);while(cursor+bytes.length>c.v01Pools[pool][1]){pool++;if(pool>=c.v01Pools.length)throw Error(c.character+' has no more sprite storage.');cursor=c.v01Pools[pool][0];}result.set(bytes,cursor);for(const p of s.pointer_offsets)result.set(vbytes(vcpu(cursor)),p);cursor+=bytes.length;
  }
 }
 for(const [key,p]of Object.entries(edits)){
  const s=C.sources[key];if(s.v01Slot!==undefined)continue;const bytes=encode(p,s.compressed);
  if(bytes.length<=s.length)result.set(bytes,s.offset);
  else{if(!s.pointer_offsets?.length)throw Error('This original tile needs more space. Simplify that edit.');let next=vlong(result,0x70fdf0);if((next&65535)+bytes.length>65536)next=(next+65535)&~65535;if(next<0x750000||next+bytes.length>0x7d0000)throw Error('Mr. Perfect has no more editing space.');result.set(bytes,next);for(const at of s.pointer_offsets)result.set(vbytes(next),at);result.set(vbytes(next+bytes.length),0x70fdf0);}
 }
 for(const c of C.characters)for(const [i,v]of Object.entries(palettes[c.id]||{}))result.set(new Uint8Array([v&255,v>>8]),c.palette_offset+Number(i)*2);
 v16Selection(result);result.set(new Uint8Array([255,255,0,0]),0xffdc);result.set(result.slice(0,65536),0x400000);let sum=0;for(const b of result)sum=(sum+b)&65535;const crc=new Uint8Array([(sum^65535)&255,(sum^65535)>>8,sum&255,sum>>8]);result.set(crc,0xffdc);result.set(crc,0x40ffdc);
 const ips=[80,65,84,67,72];for(let at=0;at<result.length;){if(result[at]===rom[at]){at++;continue;}let start=at;if(start===0x454f46)start--;while(at<result.length&&result[at]!==rom[at]&&at-start<65535)at++;const bytes=result.slice(start,at);ips.push(start>>>16,start>>>8&255,start&255,bytes.length>>>8,bytes.length&255,...bytes);}ips.push(69,79,70);return new Uint8Array(ips);
};
const v01Header=document.createElement('p');v01Header.textContent='Roster 16 preview · Expanded roster editing · Some imported moves are unfinished';v01Header.style.cssText='padding:12px 18px;background:#253a51;color:#fff;border-radius:8px';document.body.prepend(v01Header);

const v01Recover=$('recover-rom').onchange;
$('recover-rom').onchange=async event=>{if(rom&&vexpanded(rom))return $('rom').onchange({target:{files:event.target.files}});return v01Recover(event);};
const v01Play=$('play').onclick;
$('play').onclick=()=>{if(!M.v01)return v01Play();if(timer){stop();return;}const root=M.poses[Number($('pose').value)].v01Root,group=r=>r>=0x4606&&r<=0x463e?'walk':r>=0x46ae&&r<=0x46f4?'large-walk':r>=0x4702&&r<=0x473a?'large-turn':r>=0x49e2&&r<=0x4a0c?'punch':r>=0x4a36&&r<=0x4a60?'kick':r>=0x48d2&&r<=0x48ee?'run':r>=0xf000?'landing':r>=0x4c70&&r<=0x4cfc?'suplex':r>=0x55ee&&r<=0x565c?'slam':'stance',indices=M.poses.map((p,i)=>group(p.v01Root)===group(root)?i:null).filter(i=>i!==null);let n=indices.indexOf(Number($('pose').value));$('play').textContent='Stop preview';timer=setInterval(()=>{$('pose').value=indices[n=(n+1)%indices.length];render();},120);};

function v01MusicAddress(id){if(!rom||!vexpanded(rom)||id<12)return MUSIC.base+id*MUSIC.stride;const locations=[0x543000,0x5e3000,0x353000,0x3bb000],address=locations[id-12];if(!address)throw Error('Unknown music slot.');if(id<15){const owner=C.characters.find(c=>Number(c.id)===id+1);if(owner.v01DescriptorEnd>address)throw Error('This ROM has no safe space for that song.');}return address;}
function v01MusicCPU(a){return a>=0x400000&&a<0x7e0000?a:(a&0x3fffff)|0xc00000;}
const v01RenderMusic=renderCustomMusic;
renderCustomMusic=function(){v01RenderMusic();if(rom&&vexpanded(rom)&&!selectionEdits[M.id]?.song){const source=romPointer(rom,MUSIC.bankDirectory+rom[0x11936+S.characters[M.id].theme]*3);if([0x543000,0x5e3000,0x353000,0x3bb000].includes(source))$('song-status').textContent='A custom song is saved in this ROM. Import its MIDI to change it.';}};
