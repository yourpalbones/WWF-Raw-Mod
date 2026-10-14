/* Resolve any slot's frame parts the way the game routes them (mirror of tools/raw_parts.py). */
window.RAW_PARTS=(()=>{
 const DIR=window.RAW_TILE_DIRECTORY;
 const TABLES={primary:[0x2dd513,0x2dd52d,527,998],secondary:[0x2dd547,0x2dd561,426,722]};
 const ORIGIN={primary:[0x70,0x4a],secondary:[0x78,0x3a]},DELTAS={primary:[0xbf2e,0xbf4e],secondary:[0xbf6e,0xbf8e]};
 const GEAR={5:{sig:[0x4bf000,'SCOTT-HALL-GEAR3'],tables:[0x4bc000,0x4bd000],banks:[0x42,0x43],pointers:[0x4b0000,0x4b0000]},
  10:{sig:[0x416000,'NASH-NATIVE-GEAR2'],tables:[0x410000,0x411000],banks:[0x4c,0x4d],pointers:[0x5f0000,0x5f0000]},
  9:{sig:[0x417000,'SYXX-NATIVE-GEAR3'],tables:[0x413000,0x414000],banks:[0x56,0x57],pointers:[0x5fa000,0x5fa000]},
  7:{sig:[0x6ff000,'STING-NATIVE-GEAR4'],tables:[0x6fc000,0x6fd000],banks:[0x60,0x61],pointers:[0x6e0000,0x6f0000]}};
 const long=(d,a)=>d[a]|d[a+1]<<8|d[a+2]<<16,text=(d,a,n)=>String.fromCharCode(...d.slice(a,a+n));
 function fileOffset(address,size){const bank=address>>16;if(size>0x400000&&bank>=0x40&&bank<=0x7d)return address;if(size>0x400000&&bank<0x40&&address&0x8000)return address+0x400000;return address&0x3fffff;}
 function activeGear(rom,slot){const g=GEAR[slot];return g&&rom.length>=0x600000&&text(rom,g.sig[0],g.sig[1].length)===g.sig[1]?g:null;}
 const hasPerfect=rom=>rom.length>=0x800000&&text(rom,0x70fe00,12)==='PERFECT-SLOT';
 function descriptorAddress(rom,slot,kind,index){
  const [table,banks,own,count]=TABLES[kind],total=slot===12&&kind==='primary'?1012:count;if(index<0||index>=total)throw Error(kind+' index out of range');
  if(slot===12){if(!hasPerfect(rom))throw Error('ROM has no imported slot 12');return long(rom,(kind==='secondary'?0x711000:0x710000)+index*3);}
  const gear=activeGear(rom,slot);if(gear){const e=long(rom,gear.tables[kind==='secondary'?1:0]+index*3);if(e&0xffff)return e;}
  const selector=index<own?slot:8,dir=fileOffset(rom[banks+selector*2]<<16|rom[table+selector*2]|rom[table+selector*2+1]<<8,rom.length),entry=dir+index*3;
  return rom[entry]<<16|rom[entry+1]|rom[entry+2]<<8;
 }
 const packetLength=(rom,o)=>{let n=4;for(let b=0;b<4;b++)for(let i=0;i<8;i++)n+=rom[o+b]>>i&1;return n;};
 function decodePacket(rom,o){const out=new Uint8Array(32);let c=o+4;for(let i=0;i<32;i++)if(rom[o+(i>>3)]>>(7-i%8)&1)out[i]=rom[c++];return out;}
 function planarPixels(raw){const px=new Array(64);for(let y=0;y<8;y++)for(let x=0;x<8;x++){let v=0;for(let p=0;p<4;p++)v|=((raw[(p>>1)*16+y*2+(p&1)]>>(7-x))&1)<<p;px[y*8+x]=v;}return px;}
 function tileSource(rom,kind,id,bank){
  for(const g of Object.values(GEAR))if(g.banks.includes(bank)&&id>=0xc000)return {offset:fileOffset(long(rom,g.pointers[bank===g.banks[1]?1:0]+(id&0x3fff)*3),rom.length),compressed:false};
  if(bank>=0x72&&bank<=0x75&&id>=0xc000)return {offset:long(rom,(bank>=0x74?0x749800:0x7d0000)+(id&0x3fff)*3),compressed:true};
  const k=DIR.kinds[kind];if(id<k.threshold)return {offset:((k.direct_bank<<16)+k.direct_base+id*32)&0x3fffff,compressed:false};
  const i=id-k.threshold,[start,page]=k.groups[i>>7];return {offset:start+DIR.pages[page][i&127],compressed:true};
 }
 function parseDescriptor(rom,kind,address){
  const offset=fileOffset(address,rom.length),total=rom[offset],large=rom[offset+1];if(large>total||total>64)throw Error('Invalid descriptor');
  let c=offset+2,[x,y]=ORIGIN[kind];const [xt,yt]=DELTAS[kind],parts=[];
  for(let o=0;o<total;o++){
   const control=rom[c++];
   if(!control){x=rom[c];y=rom[c+1];c+=2;}
   else{const dx=control>>4,dy=control&15;
    if(dx)x=(x+(rom[xt+dx*2]|rom[xt+dx*2+1]<<8))&255;else x=rom[c++];
    if(dy)y=(y+(rom[yt+dy*2]|rom[yt+dy*2+1]<<8))&255;else y=rom[c++];}
   const size=o<large?16:8,tiles=[];for(let s=0;s<(size===16?4:1);s++){tiles.push({id:rom[c]|rom[c+1]<<8,field:c});c+=2;}
   const px=x&127;parts.push({x:px&64?px-128:px,y:(y&127)-105,size,hflip:!!(x&128),vflip:!!(y&128),tiles});
  }
  return {parts,offset,length:c-offset};
 }
 // Profile part IDs are byte offsets into the slot's directory (frame index * 3); bit 15 = secondary.
 function resolvePart(rom,slot,partId){
  if((partId&0x7fff)%3)throw Error('Part ID is not a directory offset');
  return resolveIndex(rom,slot,partId&0x8000?'secondary':'primary',(partId&0x7fff)/3);
 }
 function resolveIndex(rom,slot,kind,index){
  const address=descriptorAddress(rom,slot,kind,index);
  const d=parseDescriptor(rom,kind,address),bank=rom.length>0x400000&&d.offset>=0x400000?d.offset>>16:-1;
  for(const p of d.parts){p.pixels=[];p.sources=[];for(const t of p.tiles){const s=tileSource(rom,kind,t.id,bank);p.sources.push(s);p.pixels.push(planarPixels(s.compressed?decodePacket(rom,s.offset):rom.slice(s.offset,s.offset+32)));}}
  return {kind,index,descriptor:d.offset,length:d.length,parts:d.parts};
 }
 // Paint objects (first listed on top) into a Map 'x,y' -> colour; flip mirrors about the actor origin.
 function raster(parts,dx=0,dy=0,flip=false,into=new Map()){
  for(const p of [...parts].reverse()){const s=p.size;
   for(let y=0;y<s;y++)for(let x=0;x<s;x++){const sx=p.hflip?s-1-x:x,sy=p.vflip?s-1-y:y,v=p.pixels[(sy>>3)*(s>>3)+(sx>>3)][sy%8*8+sx%8];if(!v)continue;const px=p.x+x;into.set(`${dx+(flip?-px-1:px)},${dy+p.y+y}`,v);}}
  return into;
 }
 function profileParts(rom,address){const out=[];let a=fileOffset(address,rom.length),id;while((id=rom[a]|rom[a+1]<<8)!==0xffff){const dx=rom[a+2],dy=rom[a+3];out.push([id,dx>127?dx-256:dx,dy>127?dy-256:dy]);a+=4;}return out;}
 function palette(rom,slot){const base=fileOffset(rom[0x2cf218]<<16|rom[0x2cf212]|rom[0x2cf213]<<8,rom.length)+64+slot*32;return Array.from({length:16},(_,i)=>rom[base+i*2]|rom[base+i*2+1]<<8);}
 return {descriptorAddress,parseDescriptor,tileSource,resolvePart,resolveIndex,raster,profileParts,palette,fileOffset,activeGear,hasPerfect,packetLength};
})();
