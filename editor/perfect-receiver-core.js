/* Decode paired receiving drawings locally; isolate each worker's new tiles. */
window.RAW_PERFECT_RECEIVER_CORE=(()=>{
 // Canonical facing: receiver drawings are mirrored (descriptor column = mirror_shift - Royal column).
 const ORIGIN_X=72;
 const RI=window.RAW_ROYAL_IMPORT_CORE;
 const marker=data=>String.fromCharCode(...data.slice(0x70fe40,0x70fe49));
 // Layouts. RX1/RX2 used fixed pools inside the Syxx and Sting gear reservations; RX3 uses space that only
 // the Perfect import and these drawings use (docs/complete-wrestler-art.md, "Receiving storage").
 const OLD_REGIONS=[[0x5d0000,0x5f0000],[0x6d0000,0x6e0000],[0x71d000,0x720000]];
 const HOOKS=[[0x70f000,0x71e800],[0x70f200,0x71e900],[0x70f400,0x71ea00]];
 function installed(data){return data.length===0x800000&&['ROYAL-RX1','ROYAL-RX2','ROYAL-RX3','ROYAL-RX4'].includes(marker(data));}
 // RX4 adds Royal's held pin, release and recovery after the bridge; RX3 keeps the same layout for the drawings themselves.
 function current(data,recipes=window.RAW_PERFECT_RECEIVERS){return installed(data)&&marker(data)===recipes.layout.marker;}
 function outdated(data){return data.length===0x800000&&['ROYAL-RX1','ROYAL-RX2'].includes(marker(data));}
 function regions(layout){return [layout.descriptors,[layout.pointer_table,layout.pointer_end],...layout.pools,layout.tables];}
 // CPU address of a file offset: banks $40-$7D map directly; 7E8000-7EFFFF / 7F8000-7FFFFF are $3E/$3F:8000+.
 const cpu=offset=>offset>=0x7e0000?offset-0x400000:offset;
 // Gear identities reserve these ranges (editor/nwo-gear-patterns.js); an uninstall must not clear them.
 function gearReserved(data){
  const out=[],P=window.RAW_NWO_GEAR_PATTERNS||{};
  for(const r of Object.values(P)){
   const text=String.fromCharCode(...data.slice(r.signature_offset,r.signature_offset+r.signature.length-1));
   if(!r.signature.startsWith(text)||!text)continue;
   for(const [a,b]of [[r.frames_start,r.frames_end],[r.packets_start,r.packets_end],[r.pointers,r.pointer_end],[r.secondary_pointers,r.secondary_pointer_end]])if(a!==undefined&&b!==undefined)out.push([a,b]);
  }
  return out;
 }
 function gearIdentity(data,slot){
  const r=(window.RAW_NWO_GEAR_PATTERNS||{})[slot];if(!r)return false;
  const prefix=r.signature.slice(0,-1);
  return String.fromCharCode(...data.slice(r.signature_offset,r.signature_offset+prefix.length))===prefix;
 }
 function nearestMapping(colors,target){
  const rgb=value=>[0,5,10].map(s=>value>>>s&31);
  return [0,...colors.slice(1).map(color=>{let best=1,distance=Infinity;for(let j=1;j<16;j++){const d=rgb(color).reduce((sum,v,i)=>sum+(v-rgb(target[j])[i])**2,0);if(d<distance){distance=d;best=j;}}return best;})];
 }
 // One receiving drawing for a slot: {image:144x144 palette indices, chunks, body_dx, shadow_dx}.
 function royalDrawing(source,recipes,selector,i,mapping,cache,shift){
  const row=recipes.workers[selector].poses[i],image=new Uint8Array(144*144);
  for(const part of [...row.parts].reverse())for(let y=0;y<part.size;y++)for(let x=0;x<part.size;x++){
   const sx=part.hflip?part.size-1-x:x,sy=part.vflip?part.size-1-y:y,ref=part.refs[Math.floor(sy/8)*(part.size/8)+Math.floor(sx/8)],key=ref?ref.join(':'):'blank';
   if(!cache.has(key))cache.set(key,RI.tile(source,ref));const value=cache.get(key)[sy%8*8+sx%8];
   if(value)image[(part.y+y+105)*144+ORIGIN_X+shift-(part.x+x)]=mapping[value];
  }
  return {image,chunks:row.canonical_chunks,body_dx:row.body_dx,shadow_dx:row.shadow_dx};
 }
 function drawings(base,source,recipes,slot,spec){
  const shift=recipes.canonical.mirror_shift,cache=new Map(),paletteBase=0x700000+RI.word(base,0x2cf212);
  if(spec.source==='royal'){
   const colors=Array.from({length:16},(_,i)=>RI.word(source,0x17c26+spec.selector*32+i*2)),target=Array.from({length:16},(_,i)=>RI.word(base,paletteBase+64+slot*32+i*2));
   const mapping=nearestMapping(colors,target);
   return recipes.workers[spec.selector].poses.map((_,i)=>royalDrawing(source,recipes,spec.selector,i,mapping,cache,shift));
  }
  if(spec.source==='own_native'&&window.RAW_RECEIVING_ART)return window.RAW_RECEIVING_ART.ownNative(base,slot,recipes.own_native_steps);
  if(spec.source==='own_profiles'&&window.RAW_RECEIVING_ART){
   // A gear identity has its own plan (its drawings can differ in shape); otherwise the stock plan.
   const plan=recipes.own_profiles[slot];if(!plan)throw Error(`No receiving plan for slot ${slot}.`);
   return window.RAW_RECEIVING_ART.ownProfiles(base,source,recipes,slot,gearIdentity(base,slot)&&plan.gear?plan.gear:plan);
  }
  if(spec.source==='reskin'&&window.RAW_RECEIVING_ART){
   // Royal's drawing in the wrestler's own pixels; a gear identity has its own plan (its pieces differ).
   const plan=recipes.reskin[slot];if(!plan)throw Error(`No receiving plan for slot ${slot}.`);
   const use=gearIdentity(base,slot)&&plan.gear?plan.gear:plan;if(!use.steps)throw Error(`No receiving plan for slot ${slot} with this identity.`);
   return window.RAW_RECEIVING_ART.reskin(base,source,recipes,slot,use);
  }
  if(spec.source==='authored'&&window.RAW_RECEIVING_ART)return window.RAW_RECEIVING_ART.render(base,source,recipes,slot,spec);
  throw Error(`No receiving art source for slot ${slot}.`);
 }
 function install(base,source,recipes){
  if(installed(base))throw Error('Receiving sprites are already imported. Use the sprite editor to change them.');
  if(base.length!==0x800000||String.fromCharCode(...base.slice(0x70fe00,0x70fe13))!=='PERFECT-SLOT-PROTO1')throw Error('Add Mr. Perfect before updating the receiving sprites.');
  if(!recipes.canonical||recipes.canonical.origin[0]!==ORIGIN_X)throw Error('Receiving recipes are not in canonical facing.');
  const L=recipes.layout,out=base.slice();
  for(const [start,end]of regions(L))for(let p=start;p<end;p++)if(out[p]!==255)throw Error('The receiving sprite space is occupied. Your ROM was kept unchanged.');
  out.fill(0,L.tables[0],L.tables[0]+0x27);out.fill(0,L.tables[0]+0x40,L.tables[0]+0x67);
  const report=[];let pool=0,packet=L.pools[0][0],descriptor=L.descriptors[0],count=0;
  const skipped=[];
  for(const [slotText,spec]of Object.entries(recipes.slots)){
   const slot=Number(slotText);
   // A Royal counterpart is the same identity only while the slot keeps its original character.
   let use=spec;
   if(spec.stock_identity_only&&gearIdentity(base,slot)){
    if(!spec.fallback){skipped.push({raw_slot:slot,reason:'gear identity applied; Royal '+spec.selector+' art would replace it'});continue;}
    use={source:spec.fallback};
   }
   const privateTiles=new Map(),poses=drawings(base,source,recipes,slot,use);
   const X=recipes.exit,table=0x71d100+slot*36,profiles=0x71d400+slot*168,sequence=X.sequences+slot*X.sequence_stride;
   RI.putLong(out,0x71d000+slot*3,table);RI.putLong(out,0x71d040+slot*3,sequence);
   poses.forEach((pose,i)=>{
    const record=[pose.chunks.length,pose.chunks.filter(c=>c[2]===16).length];
    for(const [x,y,size]of pose.chunks){record.push(0,x&127,(y+105)&127);
     for(let ty=0;ty<size/8;ty++)for(let tx=0;tx<size/8;tx++){
      const pixels=[];for(let yy=0;yy<8;yy++)for(let xx=0;xx<8;xx++)pixels.push(pose.image[(y+105+ty*8+yy)*144+x+ORIGIN_X+tx*8+xx]);
      const raw=RI.planar(pixels),key=String.fromCharCode(...raw);
      if(!privateTiles.has(key)){
       const encoded=RI.packed(raw);
       // Packets never cross a bank (the decoder reads with a 16-bit index).
       while(packet+encoded.length>L.pools[pool][1]||(packet&0xffff)+encoded.length>0x10000){pool++;if(pool>=L.pools.length)throw Error('Receiving sprite space is full.');packet=L.pools[pool][0];}
       if(L.pointer_table+(count+1)*3>L.pointer_end)throw Error('Receiving tile directory is full.');
       privateTiles.set(key,count);out.set(encoded,packet);RI.putLong(out,L.pointer_table+count*3,cpu(packet));packet+=encoded.length;count++;
      }const id=0xc000|privateTiles.get(key);record.push(id&255,id>>>8);
     }
    }
    if((descriptor&0xffff)+record.length>0x10000||descriptor+record.length>L.descriptors[1])throw Error('Receiving pose space is full.');
    out.set(record,descriptor);RI.putLong(out,table+i*3,descriptor);descriptor+=record.length;
    const profile=profiles+i*14;RI.putWord(out,profile,(1200+i)*3);out.set([pose.body_dx&255,0,36,128,pose.shadow_dx&255,255,255,255],profile+2);
   });
   // Steps 0-11, then Royal's held pin and release (docs/perfect-plex-exit.md). An entry is [bank, profile, x move,
   // y move, draw x, draw y]; x moves and draw x count along the facing. The bridge is held for X.hold entries; the
   // first release entry moves the receiver's actor X.forward px past Mr. Perfect, then Raw's own roll-off and lying
   // profiles (the receiver's own art) draw at the offsets planned from Royal (tools/plan_perfect_plex_exit.py);
   // lying keeps Raw's downed-action offsets, so the downed action continues the drawing.
   const entries=[];for(let i=0;i<12;i++)entries.push([113,profiles+i*14,0,0,0]);
   for(let i=0;i<X.hold;i++)entries.push([113,profiles+11*14,0,0,0]);
   for(const step of X.steps){
    if(RI.word(base,step.profile&0xffff|0x080000)!==step.first_part)throw Error('Unsupported Raw receiving animation.');
    for(let n=0;n<step.entries;n++)entries.push([200,step.profile,entries.length===12+X.hold?X.forward:0,...step.draw]);
   }
   if(entries.length*7+1>X.sequence_stride)throw Error('Receiving sequence exceeds its space.');
   entries.forEach(([bank,address,move,dx,dy],i)=>out.set([bank,address&255,address>>>8&255,move&255,0,dx&255,dy&255],sequence+i*7));out[sequence+entries.length*7]=255;
   report.push({raw_slot:slot,source:use.source,royal_selector:use.selector??null,receiving_drawings:poses.length,private_tiles:privateTiles.size});
  }
  for(const [original,copy]of HOOKS)out.set(base.slice(original,original+256),copy);
  for(const [original,address,code]of recipes.programs){out.set(code,address);out[original]=92;RI.putLong(out,original+1,address);}
  out.set(Array.from(L.marker,c=>c.charCodeAt(0)),0x70fe40);RI.checksum(out);
  return {bytes:out,report:{receivers:report,skipped,tile_namespace_count:count,descriptor_end:descriptor,last_packet:packet,pool,
   raw_only_receiving_art_complete:false,custom_gear_receiving_art_complete:false}};
 }
 // Remove an installed receiving build: restore the three chained hooks from their saved copies and free
 // the receiving allocations. RX1/RX2 pools overlap gear reservations; bytes inside an active gear
 // identity's reserved range are left alone.
 function uninstall(data,recipes=window.RAW_PERFECT_RECEIVERS){
  if(!installed(data))return data;
  const out=data.slice(),old=outdated(data),keep=old?gearReserved(data):[];
  for(const [original,copy]of HOOKS)out.set(data.slice(copy,copy+256),original);
  for(const [start,end]of old?OLD_REGIONS:regions(recipes.layout))for(let p=start;p<end;p++)if(!keep.some(([a,b])=>p>=a&&p<b))out[p]=255;
  out.fill(255,0x70fe40,0x70fe49);RI.checksum(out);return out;
 }
 return {installed,outdated,current,install,uninstall,cpu};
})();
