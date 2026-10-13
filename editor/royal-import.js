/* Import a verified source ROM locally, append slot 13, and keep it editable. */
const RI=window.RAW_ROYAL_IMPORT_CORE,RM=window.RAW_ROYAL_IMPORT_MANIFEST;
const originalSelectionManifest=structuredClone(S);
let royalSource=null;
function hasImportedWorker(data){return data.length===0x800000&&String.fromCharCode(...data.slice(0x70fe00,0x70fe00+'PERFECT-SLOT-PROTO1'.length))==='PERFECT-SLOT-PROTO1';}
function importedPaletteRecords(data){
 if(!hasImportedWorker(data)||RI.word(data,0x2cf212)!==0x8400)return [];
 for(let p=0x70e800;p<0x70ea60;p++)if(data[p]!==255)throw Error('Referee repair space is occupied; no repair was applied.');
 const palette=new Uint8Array(0x260);palette.set(data.slice(0x708400,0x7085e0));palette.set(data.slice(0x2cc67a,0x2cc6fa),0x1e0);
 return [[0x70e800,palette],[0x2cf212,new Uint8Array([0,232])]];
}
function resetImportedMetadata(){for(const key of Object.keys(S))delete S[key];Object.assign(S,structuredClone(originalSelectionManifest));H.destination=0x3a0000;}
function importedProfileAssets(base,result){
 const out=result.bytes,record=0x708000+12*45,rgba=RI.royalPortrait(royalSource),photo=quantizePortrait(rgba);
 const put=(at,packet,limit)=>{if(at+packet.length>limit)throw Error('Imported profile exceeds its allocation.');for(let i=at;i<at+packet.length;i++)if(out[i]!==255)throw Error('Imported profile space is occupied.');out.set(packet,at);};
 const palette=colors=>new Uint8Array(colors.flatMap(v=>[v&255,v>>>8]));
 put(0x708800,portraitPacket(photo.pixels),0x70c800);
 const oldPalette=romPointer(base,0x2efaf5+45+4);put(0x708700,new Uint8Array([...base.slice(oldPalette,oldPalette+64),...palette(photo.colors)]),0x708800);
 RI.putLong(out,record,0x708800);RI.putLong(out,record+4,0x708700);
 const monitorRGBA=new Uint8ClampedArray(48*48*4);
 for(let y=0;y<48;y++)for(let x=0;x<48;x++){const sx=4+Math.floor(x*120/48),sy=Math.floor(y*120/48);monitorRGBA.set(rgba.slice((sy*128+sx)*4,(sy*128+sx)*4+4),(y*48+x)*4);}
 const monitor=quantizePortrait(monitorRGBA,31),monitorPixels=monitor.pixels.map(v=>v+1);
 put(0x70c800,nativeBlock(imageTiles(monitorPixels,48,48,8)),0x70d200);put(0x70d200,palette([0,...monitor.colors]),0x70d400);
 RI.putLong(out,record+20,0x70c800);RI.putLong(out,record+24,0x70d200);
 // The Raw bio reader keeps its original string bank. Use only vacant text.
 for(const [field,text]of [[28,'MR PERFECT'],[30,'MINNESOTA'],[36,'6\'4"'],[38,'PERFECT-\rPLEX']]){
  const bytes=new Uint8Array(Array.from(text+'\0',c=>c.charCodeAt(0))),at=RI.search(out,new Uint8Array(bytes.length).fill(255),0x2eff49,0x2f0000);
  if(at<0)throw Error('Not enough bio text space to add Mr. Perfect. Shorten existing edited bios and save before importing.');out.set(bytes,at);RI.putWord(out,record+field,at&65535);
 }out.set([50,53,55,0],record+32);
 const logo=generateNameLogo('MR PERFECT','1'),packedLogo=logoTiles(logo,'1');
 put(0x70d400,nativeBlock(packedLogo.graphics),0x70d800);put(0x70d800,nativeBlock(packedLogo.map),0x70e200);put(0x70e200,palette(logo.colors),0x70e400);
 for(const [field,address]of [[8,0x70d400],[12,0x70d800],[16,0x70e200]])RI.putLong(out,record+field,address);
 for(const [old,target,stride,address]of [[0x2ee90f,0x70e400,2,0x70c800],[0x2ee927,0x70e420,1,0x70c800],[0x2ee93f,0x70e440,2,0x70d200],[0x2ee957,0x70e460,1,0x70d200]]){
  out.set(base.slice(old,old+12*stride),target);if(stride===2)RI.putWord(out,target+24,address&65535);else out[target+12]=address>>>16;
  const reference=old|0x800000,pattern=[reference&255,reference>>>8&255,reference>>>16&255];let pos=0,refs=0;
  while((pos=RI.search(base,pattern,pos,0x300000))>=0){if(base[pos-1]===191){RI.putLong(out,pos,target);refs++;}pos++;}if(refs!==2)throw Error('Unsupported announcer monitor table.');
 }
 // Preserve the twelve loaded HUD names and add a dedicated thirteenth label.
 const atlas=decodePortrait(base,hudSource(base)),font=new Uint8Array(atlas),name=matchNamePixels('MR PERFECT');
 font.set(imageTiles(name,64,8,4),135*32);put(0x738000,nativeBlock(font),0x73b000);
 out[H.bankOperand]=0x73;RI.putWord(out,H.addressOperand,0x8000);out.set([135,136,137,138,139,140,141,142],H.table+12*8);
 // Keep the editor's auxiliary directory entries separate from the twelve stock rows.
 RI.putLong(out,0x70e580,0x70c800);RI.putLong(out,0x70e584,0x70d200);
 RI.putLong(out,0x70fdf0,result.report.packet_end);
 RI.checksum(out);return out;
}
function activateImportedWorker(data){
 if(!hasImportedWorker(data))return;
 if(data[0x19d43f]!==13||data[0xffd5]!==0x25||RI.long(data,0x70fdf0)<0x750000||RI.long(data,0x70fdf0)>0x7d0000)throw Error('Imported wrestler metadata is invalid.');
 H.destination=0x738000;
 const paletteBase=0x700000+RI.word(data,0x2cf212);if(![0x708400,0x70e800].includes(paletteBase))throw Error('Unsupported imported palette location.');
 for(const [id,meta]of Object.entries(S.characters)){
  const index=Number(id),record=0x708000+index*45;meta.record=record;meta.theme_offset=record+44;
  meta.fields={name:record+28,from:record+30,weight:record+32,height:record+36,special:record+38};
  meta.announcer_monitor_word=0x70e400+index*2;meta.announcer_monitor_bank=0x70e420+index;meta.announcer_palette_word=0x70e440+index*2;meta.announcer_palette_bank=0x70e460+index;
  C.characters.find(c=>c.id===id).palette_offset=paletteBase+64+index*32;
 }
 const record=0x708000+12*45;
 S.characters['12']={...structuredClone(S.characters['1']),record,portrait_offset:0x708800,palette_offset:0x708740,
  portrait_length:15604,monitor_offset:0x70c800,monitor_palette_offset:0x70d200,
  monitor_directory_offset:0x70e580,monitor_palette_directory_offset:0x70e584,
  announcer_monitor_word:0x70e418,announcer_monitor_bank:0x70e42c,announcer_palette_word:0x70e458,announcer_palette_bank:0x70e46c,
  logo_offset:0x70d400,logo_map_offset:0x70d800,logo_palette_offset:0x70e200,logo_tile_limit:146,
  theme_offset:record+44,theme:data[record+44],fields:{name:record+28,from:record+30,weight:record+32,height:record+36,special:record+38}};
 const sources={},poses=[],pointerUsers=new Map();
 function descriptor(address,kind){
  if(address<0x720000||address>=0x750000)throw Error('Imported sprite descriptor outside its banks.');
  const count=data[address],large=data[address+1];if(!count||count>64||large>count)throw Error('Imported sprite object count is invalid.');let cursor=address+2;const parts=[];
  for(let n=0;n<count;n++){
   if(data[cursor++]!==0)throw Error('Unsupported imported sprite position encoding.');const px=data[cursor++]&127,py=data[cursor++]&127,size=n<large?16:8,tiles=[];
   for(let t=0;t<(size===16?4:1);t++){
    const id=RI.word(data,cursor);cursor+=2;if(id<0xc000)throw Error('Imported tile is not isolated.');
    const pointer=(kind==='primary'?0x7d0000:0x749800)+(id&16383)*3,offset=RI.long(data,pointer);
    if(offset<0x750000||offset>=0x7d0000)throw Error('Imported tile packet is outside its allocation.');
    let length=4;for(let i=0;i<4;i++)for(let bit=0;bit<8;bit++)length+=(data[offset+i]>>bit)&1;
    const key=String(offset);sources[key]={offset,length,compressed:true};(pointerUsers.get(key)||pointerUsers.set(key,[]).get(key)).push(pointer);tiles.push(key);
   }parts.push({x:px&64?px-128:px,y:py-105,size,hflip:false,vflip:false,tiles});
  }return parts;
 }
 function pose(label,category,parts){
  if(!parts.length)return;const left=Math.min(...parts.map(p=>p.x)),top=Math.min(...parts.map(p=>p.y)),right=Math.max(...parts.map(p=>p.x+p.size)),bottom=Math.max(...parts.map(p=>p.y+p.size));
  poses.push({label,category,width:right-left,height:bottom-top,parts:parts.map(p=>({...p,x:p.x-left,y:p.y-top}))});
 }
 for(let i=0;i<12;i++)pose('Perfect-Plex · '+(i+1),'Perfect-Plex',descriptor(RI.long(data,0x710000+(1000+i)*3),'primary'));
 for(const f of RM.frames){const address=RI.long(data,(f.kind==='primary'?0x710000:0x711000)+f.index*3);pose((f.common?'Common ':'')+(f.kind==='primary'?'Upper':'Lower')+' piece '+f.index,(f.common?'common-':'')+f.kind,descriptor(address,f.kind));}
 for(const [key,p]of pointerUsers)sources[key].pointer_offsets=[...new Set(p)];
 Object.assign(C.sources,sources);C.characters.push({id:'12',character:'Mr. Perfect',palette_offset:paletteBase+0x1c0,sources,poses,
  scope:`${RM.coverage.royal_poses} Royal source pieces; ${RM.coverage.adapted_raw_poses} adapted Raw pieces; native Perfect-Plex. Remaining art conversion is listed in the import coverage.`});
}
function refreshRoyalImport(){
 const loaded=Boolean(rom),added=loaded&&hasImportedWorker(rom);$('royal-rom').disabled=!loaded;$('royal-add').disabled=!loaded||!royalSource||added;
 $('royal-worker').disabled=!loaded||!royalSource||added;
 if(added)$('royal-status').textContent='Mr. Perfect occupies slot 13, including the Perfect-Plex. 289 pieces use Royal artwork; 1,431 use adapted Raw artwork. Save this ROM to keep editing it later. One extra slot is supported.';
 if(added&&RI.word(rom,0x2cf212)===0x8400)$('royal-status').textContent+=' Save playable ROM to restore the referee and announcer palettes in this older import.';
}
$('royal-rom').onchange=async event=>{try{
 const file=event.target.files[0];if(!file)return;let data=new Uint8Array(await file.arrayBuffer());if(data.length%1024===512)data=data.slice(512);
 const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',data)),v=>v.toString(16).padStart(2,'0')).join('');
 if(hash!==RM.source_sha256)throw Error('Choose the unmodified USA SNES WWF Royal Rumble ROM.');royalSource=data;
 const image=$('royal-preview'),context=image.getContext('2d'),frame=context.createImageData(128,120);frame.data.set(RI.royalPortrait(data));context.putImageData(frame,0,0);
 $('royal-worker').replaceChildren(...RM.roster.map((name,index)=>{const o=new Option(name,String(index));o.disabled=index!==1;return o;}));$('royal-worker').value='1';$('royal-add').textContent='Add Mr. Perfect';
 $('royal-status').textContent='Royal Rumble verified. Mr. Perfect is the first supported import, including his photo, bio, blue attire and Perfect-Plex. Other source wrestlers need their own move and graphics mappings.';refreshRoyalImport();
 }catch(e){royalSource=null;$('royal-status').textContent=e.message;refreshRoyalImport();}event.target.value='';};
$('royal-add').onclick=async()=>{try{
 if(!rom||!royalSource)throw Error('Load Raw and Royal Rumble first.');$('royal-add').disabled=true;$('royal-status').textContent='Building the new slot…';await new Promise(r=>setTimeout(r,0));
 const base=playableROM(),result=RI.build(base,royalSource,RM);importedProfileAssets(base,result);
 const file=new File([result.bytes],'WWF-Raw-Mr-Perfect.sfc',{type:'application/octet-stream'});
 await $('rom').onchange({target:{files:[file]}});if(!rom||!hasImportedWorker(rom))throw Error('The imported ROM could not be reopened: '+$('status').textContent);
 download('WWF-Raw-Mr-Perfect.sfc',result.bytes,'application/octet-stream');$('wrestler').value='12';loadCharacter('12');
 $('royal-status').textContent=`Mr. Perfect added to slot 13 with the Perfect-Plex. ${result.report.royal_poses} pieces come from Royal; ${result.report.adapted_raw_poses} use adapted Raw art. Save this imported ROM as the base for your project.`;
 status('New slot added. The imported ROM was saved; it can be reopened and edited.');
 }catch(e){$('royal-status').textContent=e.message;}finally{refreshRoyalImport();}};
