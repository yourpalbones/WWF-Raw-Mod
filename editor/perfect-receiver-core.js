/* Decode paired receiving drawings locally; isolate each worker's new tiles. */
window.RAW_PERFECT_RECEIVER_CORE=(()=>{
 // Canonical facing: receiver drawings are mirrored (descriptor column = mirror_shift - Royal column).
 const ORIGIN_X=72;
 const RI=window.RAW_ROYAL_IMPORT_CORE;
 const marker=data=>String.fromCharCode(...data.slice(0x70fe40,0x70fe49));
 function installed(data){return data.length===0x800000&&['ROYAL-RX1','ROYAL-RX2'].includes(marker(data));}
 function outdated(data){return data.length===0x800000&&marker(data)==='ROYAL-RX1';}
 function install(base,source,recipes){
  if(installed(base))throw Error('Receiving sprites are already imported. Use the sprite editor to change them.');
  if(base.length!==0x800000||String.fromCharCode(...base.slice(0x70fe00,0x70fe13))!=='PERFECT-SLOT-PROTO1')throw Error('Add Mr. Perfect before updating the receiving sprites.');
  if(!recipes.canonical||recipes.canonical.origin[0]!==ORIGIN_X)throw Error('Receiving recipes are not in canonical facing.');
  const out=base.slice(),shift=recipes.canonical.mirror_shift;
  for(const [start,end]of [[0x5d0000,0x5f0000],[0x6d0000,0x6e0000],[0x71d000,0x720000]])for(let p=start;p<end;p++)if(out[p]!==255)throw Error('The receiving sprite space is occupied. Your ROM was kept unchanged.');
  out.fill(0,0x71d000,0x71d027);out.fill(0,0x71d040,0x71d067);
  const paletteBase=0x700000+RI.word(base,0x2cf212),pools=[[0x5d0000,0x5e0000],[0x5ec000,0x5f0000],[0x6d8000,0x6e0000]],cache=new Map(),report=[];
  let pool=0,packet=pools[0][0],descriptor=0x6d0000,count=0;
  const rgb=value=>[0,5,10].map(s=>value>>>s&31);
  for(const [slotText,selector]of Object.entries(recipes.raw_royal_map)){
   const slot=Number(slotText),worker=recipes.workers[selector],privateTiles=new Map();
   const colors=Array.from({length:16},(_,i)=>RI.word(source,0x17c26+selector*32+i*2)),target=Array.from({length:16},(_,i)=>RI.word(base,paletteBase+64+slot*32+i*2));
   const mapping=[0,...colors.slice(1).map(color=>{let best=1,distance=Infinity;for(let j=1;j<16;j++){const d=rgb(color).reduce((sum,v,i)=>sum+(v-rgb(target[j])[i])**2,0);if(d<distance){distance=d;best=j;}}return best;})];
   const table=0x71d100+slot*36,profiles=0x71d400+slot*168,sequence=0x71e000+slot*141;
   RI.putLong(out,0x71d000+slot*3,table);RI.putLong(out,0x71d040+slot*3,sequence);
   for(let i=0;i<worker.poses.length;i++){
    const row=worker.poses[i],image=new Uint8Array(144*144);
    for(const part of [...row.parts].reverse())for(let y=0;y<part.size;y++)for(let x=0;x<part.size;x++){
     const sx=part.hflip?part.size-1-x:x,sy=part.vflip?part.size-1-y:y,ref=part.refs[Math.floor(sy/8)*(part.size/8)+Math.floor(sx/8)],key=ref?ref.join(':'):'blank';
     if(!cache.has(key))cache.set(key,RI.tile(source,ref));const value=cache.get(key)[sy%8*8+sx%8];
     if(value)image[(part.y+y+105)*144+ORIGIN_X+shift-(part.x+x)]=mapping[value];
    }
    const chunks=row.canonical_chunks,record=[chunks.length,chunks.filter(c=>c[2]===16).length];
    for(const [x,y,size]of chunks){record.push(0,x&127,(y+105)&127);
     for(let ty=0;ty<size/8;ty++)for(let tx=0;tx<size/8;tx++){
      const pixels=[];for(let yy=0;yy<8;yy++)for(let xx=0;xx<8;xx++)pixels.push(image[(y+105+ty*8+yy)*144+x+ORIGIN_X+tx*8+xx]);
      const raw=RI.planar(pixels),key=String.fromCharCode(...raw);
      if(!privateTiles.has(key)){
       const encoded=RI.packed(raw);if(packet+encoded.length>pools[pool][1]){pool++;if(pool>=pools.length)throw Error('Receiving sprite space is full.');packet=pools[pool][0];}
       if(count>=16384)throw Error('Receiving tile directory is full.');privateTiles.set(key,count);out.set(encoded,packet);RI.putLong(out,0x5e0000+count*3,packet);packet+=encoded.length;count++;
      }const id=0xc000|privateTiles.get(key);record.push(id&255,id>>>8);
     }
    }
    if(descriptor+record.length>0x6d8000)throw Error('Receiving pose space is full.');out.set(record,descriptor);RI.putLong(out,table+i*3,descriptor);descriptor+=record.length;
    const profile=profiles+i*14;RI.putWord(out,profile,(1200+i)*3);out.set([row.body_dx&255,0,36,128,row.shadow_dx&255,255,255,255],profile+2);
   }
   for(let i=0;i<20;i++){const profile=profiles+Math.min(i,11)*14;out.set([113,profile&255,profile>>>8&255,0,0,0,0],sequence+i*7);}out[sequence+140]=255;
   report.push({raw_slot:slot,royal_selector:selector,receiving_drawings:12,private_tiles:privateTiles.size});
  }
  for(const [original,copy]of [[0x70f000,0x71e800],[0x70f200,0x71e900],[0x70f400,0x71ea00]])out.set(base.slice(original,original+256),copy);
  for(const [original,address,code]of recipes.programs){out.set(code,address);out[original]=92;RI.putLong(out,original+1,address);}
  out.set(Array.from('ROYAL-RX2',c=>c.charCodeAt(0)),0x70fe40);RI.checksum(out);
  return {bytes:out,report:{receivers:report,tile_namespace_count:count,descriptor_end:descriptor,last_packet:packet,raw_only_receiving_art_complete:false,custom_gear_receiving_art_complete:false}};
 }
 // Remove an installed receiving build: restore the three chained hooks from their saved copies and free
 // the receiving allocations, leaving the ROM exactly as install() found those regions.
 function uninstall(data){
  if(!installed(data))return data;
  const out=data.slice();
  for(const [original,copy]of [[0x70f000,0x71e800],[0x70f200,0x71e900],[0x70f400,0x71ea00]])out.set(data.slice(copy,copy+256),original);
  for(const [start,end]of [[0x5d0000,0x5f0000],[0x6d0000,0x6e0000],[0x71d000,0x720000]])out.fill(255,start,end);
  out.fill(255,0x70fe40,0x70fe49);RI.checksum(out);return out;
 }
 return {installed,outdated,install,uninstall};
})();
