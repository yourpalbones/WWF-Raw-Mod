/* Local ROM-to-ROM conversion. The manifest supplies addresses, never game pixels. */
'use strict';
window.RAW_ROYAL_IMPORT_CORE=(()=>{
 const word=(b,p)=>b[p]|b[p+1]<<8, long=(b,p)=>word(b,p)|b[p+2]<<16;
 const putWord=(b,p,v)=>{b[p]=v&255;b[p+1]=v>>>8&255;};
 const putLong=(b,p,v)=>{putWord(b,p,v);b[p+2]=v>>>16&255;};
 const equal=(b,p,a)=>a.every((v,i)=>b[p+i]===v);
 const PLEX_MARKER='PLEX-CANON1',POSES_MARKER='POSES-ROYAL3';
 const bytes=s=>Uint8Array.from(s.trim().split(/\s+/),v=>parseInt(v,16));
 const search=(b,pattern,start=0,end=b.length)=>{outer:for(let p=start;p+pattern.length<=end;p++){for(let i=0;i<pattern.length;i++)if(b[p+i]!==pattern[i])continue outer;return p;}return -1;};
 function tile(data,ref){
  if(ref===null)return Array(64).fill(0);
  const [offset,packed,length]=ref;if(offset<0||offset+length>data.length)throw Error('A source tile is outside the ROM.');
  const raw=packed?new Uint8Array(32):data.slice(offset,offset+32);let cursor=offset+4;
  if(packed)for(let i=0;i<32;i++){const group=i>>>2,mask=(data[offset+(group>>>1)]>>(group%2?0:4))&15;if(mask&(8>>(i&3)))raw[i]=data[cursor++];}
  if(packed&&cursor>offset+length)throw Error('A source tile has invalid compression.');
  return Array.from({length:64},(_,i)=>{let value=0;for(let p=0;p<4;p++)value|=((raw[(p>>>1)*16+(i>>>3)*2+(p&1)]>>(7-(i&7)))&1)<<p;return value;});
 }
 function planar(pixels,bpp=4,width=8,height=8){
  const out=new Uint8Array(width*height*bpp/8);
  pixels.forEach((v,i)=>{const x=i%width,y=Math.floor(i/width),at=((y>>>3)*(width>>>3)+(x>>>3))*bpp*8;
   for(let p=0;p<bpp;p++)out[at+(p>>>1)*16+(y&7)*2+(p&1)]|=((v>>>p)&1)<<(7-(x&7));});return out;
 }
 function packed(raw){const out=new Uint8Array(36),payload=[];for(let i=0;i<32;i++)if(raw[i]){out[i>>>3]|=(8>>(i&3))<<((i&7)<4?4:0);payload.push(raw[i]);}out.set(payload,4);return out.slice(0,4+payload.length);}
 function royalBlock(data,offset){
  if(offset<0||offset+5>data.length)throw Error('Royal graphics header outside the ROM.');
  const length=(word(data,offset+2)+1)&65534,mode=data[offset+4];
  if(!length||![0,1,2].includes(mode))throw Error('Unsupported Royal graphics block.');
  const out=new Uint8Array(length),seen=new Uint8Array(length);let cursor=offset+5,pos=0,count=0;
  const read=()=>{if(cursor>=data.length)throw Error('Truncated Royal graphics.');return data[cursor++];};
  const write=v=>{if(pos<0||pos>=length||seen[pos])throw Error('Royal graphics output overflow.');out[pos]=v;seen[pos]=1;count++;pos+=mode===2?2:1;if(mode===2&&pos>=length)pos=1;};
  for(let limit=0;limit<length*2+1024;limit++){const mask=read();for(let bit=0;bit<8;bit++){
   if(mask>>bit&1){write(read());continue;}const low=read(),high=read();
   if(high&128){for(let n=0;n<(high&63)+1;n++)write((low+(high&64?n:0))&255);}
   else {const distance=(high>>>4)*256+low;if(!distance){if(count!==length)throw Error('Royal graphics are incomplete.');return out;}
    const step=mode===2?2:1;for(let n=0;n<(high&15)+3;n++){let source=pos-distance*step;if(mode===2&&source<0)source+=length-1;if(source<0||!seen[source])throw Error('Invalid Royal graphics reference.');write(out[source]);}}
  }}throw Error('Royal graphics command limit exceeded.');
 }
 function royalPortrait(data,selector=1){
  const loRom=a=>((a>>>16)&127)*32768+(a&32767);
  const address=(words,banks)=>loRom(word(data,banks+selector*2)<<16|word(data,words+selector*2));
  const graphics=royalBlock(data,address(0x734,0x71c)),map=royalBlock(data,address(0x764,0x74c));
  const palette=loRom(0x890000|word(data,0x77c+selector*2)),rgba=new Uint8ClampedArray(128*120*4);
  for(let i=0;i<240;i++)for(let y=0;y<8;y++)for(let x=0;x<8;x++){
   let color=0;for(let p=0;p<8;p++)color|=((graphics[map[i]*64+(p>>>1)*16+y*2+(p&1)]>>(7-x))&1)<<p;
   if(color>=96)throw Error('Royal photo color outside its palette.');const value=word(data,palette+color*2),at=((Math.floor(i/16)*8+y)*128+(i%16)*8+x)*4;
   rgba.set([0,5,10].map(s=>Math.floor((value>>>s&31)*255/31)).concat(255),at);
  }return rgba;
 }
 // Adapted pieces show Bret's dark hair (Perfect index 7 dithered with black). Brown regions whose neighbours are
 // mostly dark and dithered with black are hair: 7 -> pale blond 13, black inside the dither -> beige 9, black on its edge -> dark brown 12.
 // Brown skin shading stays. points: Map 'x,y' -> index. Same rule as tools/convert_perfect_poses.hair_changes.
 const SKIN=new Set([2,3,11,6]),N8=[[-1,-1],[-1,0],[-1,1],[0,-1],[0,1],[1,-1],[1,0],[1,1]],N4=[[1,0],[-1,0],[0,1],[0,-1]];
 function hairChanges(points){
  const at=(x,y)=>points.get(x+','+y),seen=new Set(),hair=new Set(),out=new Map();
  for(const [key,v]of points){
   if(v!==7||seen.has(key))continue;const comp=[key];seen.add(key);
   for(let i=0;i<comp.length;i++){const [x,y]=comp[i].split(',').map(Number);for(const [dx,dy]of N8){const q=(x+dx)+','+(y+dy);if(points.get(q)===7&&!seen.has(q)){seen.add(q);comp.push(q);}}}
   let dark=0,skin=0;const members=new Set(comp),black=new Set();
   for(const c of comp){const [x,y]=c.split(',').map(Number);for(const [dx,dy]of N8){const n=at(x+dx,y+dy);if(n===1||n===7)dark++;else if(SKIN.has(n))skin++;}
    for(const [dx,dy]of N4)if(at(x+dx,y+dy)===1)black.add((x+dx)+','+(y+dy));}
   // Hair is dithered (black pixels with >= 2 brown 4-neighbours); solid brown patches such as armpit shadow are not.
   let dither=0;for(const b of black){const [x,y]=b.split(',').map(Number);let n=0;for(const [dx,dy]of N4)if(members.has((x+dx)+','+(y+dy)))n++;if(n>=2)dither++;}
   if(dark>=1.5*skin&&(comp.length<=2||dither>=0.3*comp.length))for(const c of comp)hair.add(c);
  }
  for(const [key,v]of points){
   if(hair.has(key)){out.set(key,13);continue;}if(v!==1)continue;
   const [x,y]=key.split(',').map(Number);let n=0;for(const [dx,dy]of N4)if(hair.has((x+dx)+','+(y+dy)))n++;
   if(n)out.set(key,n>=2?9:12);
  }
  return out;
 }
 // Apply index changes (Map 'x,y' -> index, piece coordinates) to parts with per-tile pixel arrays.
 function recolourParts(parts,changes){
  return parts.map(p=>({...p,pixels:p.pixels.map((tilePixels,t)=>tilePixels.map((v,i)=>{
   if(!v)return v;const sx=(t%(p.size/8))*8+i%8,sy=Math.floor(t/(p.size/8))*8+Math.floor(i/8);
   const x=p.x+(p.hflip?p.size-1-sx:sx),y=p.y+(p.vflip?p.size-1-sy:sy),c=changes.get(x+','+y);return c===undefined?v:c;}))}));
 }
 function checksum(out){
  out[0xffd5]=0x25;out[0xffd7]=13;out.set(out.slice(0,65536),0x400000);
  for(const at of [0xffdc,0x40ffdc])out.set([255,255,0,0],at);
  let sum=0;for(const v of out)sum=(sum+v)&65535;
  for(const at of [0xffdc,0x40ffdc]){putWord(out,at,sum^65535);putWord(out,at+2,sum);}
 }

 // Perfect-Plex attacker drawings (canonical facing), their profiles and 20-step stream, and the generic
 // receiving stream for receivers without Royal art. Shared by build() and updatePlex().
 function writePlex(out,base,source,manifest,store,pixel){
  let descriptor=0x730100;
  if(!manifest.orientation)throw Error('Perfect-Plex recipes are not in canonical facing.');
  for(let i=0;i<manifest.finisher.length;i++){
   const f=manifest.finisher[i],image=new Uint8Array(112*112);
   for(const p of [...f.parts].reverse())for(let y=0;y<p.size;y++)for(let x=0;x<p.size;x++){
    const sx=p.hflip?p.size-1-x:x,sy=p.vflip?p.size-1-y:y,value=pixel(p.refs[Math.floor(sy/8)*(p.size/8)+Math.floor(sx/8)])[sy%8*8+sx%8];
    if(!value)continue;/* canonical facing: Royal's Perfect faces right, as Raw art does unflipped */const px=56+p.x+x,py=100+p.y+y;if(px<0||px>=112||py<0||py>=112)throw Error('Finisher image exceeds its canvas.');image[py*112+px]=value;
   }
   const record=[f.chunks.length,f.chunks.filter(c=>c[2]===16).length];
   if(f.chunks.length+2>17)throw Error('Finisher exceeds the wrestler object limit.');
   for(const [x,y,size]of f.chunks){record.push(0,x&127,(y+105)&127);
    for(let ty=0;ty<size/8;ty++)for(let tx=0;tx<size/8;tx++){
     const tilePixels=[];for(let yy=0;yy<8;yy++)for(let xx=0;xx<8;xx++){const px=x+56+tx*8+xx,py=y+100+ty*8+yy;tilePixels.push(px<0||py<0||px>=112||py>=112?0:image[py*112+px]);}
     const id=0xc000|store(planar(tilePixels),'primary',false);record.push(id&255,id>>>8);
    }
   }
   if(descriptor+record.length>0x734000)throw Error('Finisher descriptions exceed their space.');out.set(record,descriptor);putLong(out,0x710000+(1000+i)*3,descriptor);descriptor+=record.length;
   const profile=0x734000+i*14;putWord(out,profile,(1000+i)*3);putWord(out,profile+2,0);out.set([36,128,0,255,255,255],profile+4);
   out.set([115,profile&255,profile>>>8&255,0,0,0,0],0x730000+i*7);
  }
  for(let i=12;i<20;i++)out.set(out.slice(0x73004d,0x730054),0x730000+i*7);out[0x73008c]=255;
  for(let i=0;i<20;i++){
   const row=manifest.victim[Math.min(i,11)],profile=0x735100+i*32;let n=0;
   for(;n<8;n++){
    const at=row.profile+n*4,id=word(base,at);putWord(out,profile+n*4,id);if(id===65535)break;
    const dx=(base[at+2]<<24>>24)+row.translate[0],dy=(base[at+3]<<24>>24)+row.translate[1];
    if(dx< -128||dx>127||dy< -128||dy>127)throw Error('Opponent animation position overflow.');out[profile+n*4+2]=dx&255;out[profile+n*4+3]=dy&255;
   }if(n===8)throw Error('Invalid opponent profile.');out.set([115,profile&255,profile>>>8&255,0,0,0,0],0x735000+i*7);
  }out[0x73508c]=255;
 out.set(Array.from(PLEX_MARKER,c=>c.charCodeAt(0)),0x70fe20);
 }
 function build(base,source,manifest){
  if(![0x300000,0x400000,0x600000,0x800000].includes(base.length))throw Error('Unsupported WWF Raw size.');
  if(source.length!==0x200000)throw Error('Use the USA SNES Royal Rumble ROM.');
  const out=new Uint8Array(0x800000);out.fill(255);out.set(base);
  for(let i=0x708000;i<0x7e0000;i++)if(out[i]!==255)throw Error('The extra wrestler space is already occupied. This version adds one new slot.');
  const native=equal(base,0xecc1,[92,0,225,75]);
  const expected=native?[[0xecc1,'5c 00 e1 4b'],[0xed19,'5c 00 e2 4b'],[0x2cf6e4,'5c 00 e0 4b']]:[[0xecc1,'7f 13 d5 ad'],[0xed19,'7f 47 d5 ad'],[0x2cf6e4,'cf 48 0f 00']];
  for(const [at,hex]of [...expected,[0x2cecb0,'22 dd ee ac'],[0xf073,'85 7c a7 7c'],[0xf08e,'22 b7 f6 80'],[0x2cf212,'9a c4'],[0x2cf218,'ac']])if(!equal(base,at,bytes(hex)))throw Error('This ROM has an unsupported code change; no import was applied.');
  const tables={primary:0x710000,secondary:0x711000},pointers={primary:0x7d0000,secondary:0x749800};
  const cursor={primary:0x720100,secondary:0x740100},tiles={primary:new Map(),secondary:new Map()},counts={primary:0,secondary:0};let packet=0x750000;
  out.fill(0,0x710000,0x710000+998*3);out.fill(0,0x711000,0x711000+722*3);
  function store(raw,kind,dedup=true){
   const key=String.fromCharCode(...raw);if(dedup&&tiles[kind].has(key))return tiles[kind].get(key);
   const index=counts[kind]++,encoded=packed(raw);
   if(index>=16384||(kind==='secondary'&&pointers[kind]+index*3+3>0x750000))throw Error('Imported wrestler exceeds its tile pointer space.');
   if((packet&65535)+encoded.length>65536)packet=(packet+65535)&~65535;
   if(packet+encoded.length>0x7d0000)throw Error('Imported wrestler exceeds its sprite space.');
   out.set(encoded,packet);putLong(out,pointers[kind]+index*3,packet);packet+=encoded.length;if(dedup)tiles[kind].set(key,index);return index;
  }
  const colors=[0,1,4,8,4,8,13,2,14,7,6,3,2,15,14,11],descriptors={primary:new Map(),secondary:new Map()},cache=new Map();
  const pixels=(data,ref,royal)=>{const key=(royal?'r':'w')+(ref?ref.join(':'):'blank');if(!cache.has(key))cache.set(key,tile(data,ref));return cache.get(key);};
  for(const f of manifest.frames){
   const kind=f.kind,parts=[...f.parts].sort((a,b)=>b.size-a.size),record=[parts.length,parts.filter(p=>p.size===16).length];
   let changes=null;
   if(f.hair){const points=new Map();for(const p of [...f.parts].reverse())for(let y=0;y<p.size;y++)for(let x=0;x<p.size;x++){
     const sx=p.hflip?p.size-1-x:x,sy=p.vflip?p.size-1-y:y,v=colors[pixels(base,p.refs[Math.floor(sy/8)*(p.size/8)+Math.floor(sx/8)],false)[sy%8*8+sx%8]];if(v)points.set((p.x+x)+','+(p.y+y),v);}
    changes=hairChanges(points);}
   if(!parts.length){record[0]=1;record.push(0,0,105);const id=store(new Uint8Array(32),kind);record.push((0xc000|id)&255,(0xc000|id)>>>8);}
   for(const p of parts){
    if(p.x< -64||p.x>=64||p.y< -105||p.y>=23)throw Error('Imported sprite position is outside Raw’s format.');
    record.push(0,p.x&127,(p.y+105)&127);
    for(let ty=0;ty<p.size/8;ty++)for(let tx=0;tx<p.size/8;tx++){
     const image=[];for(let y=0;y<8;y++)for(let x=0;x<8;x++){
      let sx=tx*8+x,sy=ty*8+y;if(p.hflip)sx=p.size-1-sx;if(p.vflip)sy=p.size-1-sy;
      const ref=p.refs[Math.floor(sy/8)*(p.size/8)+Math.floor(sx/8)],value=pixels(f.royal?source:base,ref,f.royal)[sy%8*8+sx%8];
     let out=f.royal?value:colors[value];if(changes&&out){const c=changes.get((p.x+tx*8+x)+','+(p.y+ty*8+y));if(c!==undefined)out=c;}image.push(out);
     }const id=0xc000|store(planar(image),kind);record.push(id&255,id>>>8);
    }
   }
   const key=String.fromCharCode(...record);let address=descriptors[kind].get(key);
   if(address===undefined){address=cursor[kind];const end=kind==='primary'?0x730000:0x749800;
    if((address&65535)+record.length>65536)address=(address+65535)&~65535;
    if(address+record.length>end)throw Error('Imported sprite descriptions exceed their space.');
    out.set(record,address);cursor[kind]=address+record.length;descriptors[kind].set(key,address);
   }putLong(out,tables[kind]+f.index*3,address);
  }
  writePlex(out,base,source,manifest,store,ref=>pixels(source,ref,true));
  // Copy profiles, palettes and signature tables instead of overwriting another worker.
  out.set(base.slice(0x2efaf5,0x2efd11),0x708000);out.set(base.slice(0x2efaf5+45,0x2efaf5+90),0x708000+12*45);
  const helper=bytes('a2 2d 00 22 5f ff ad 18 69 f5 fa aa f4 fa ae ab ab 60'),at=search(base,helper);
  if(at<0)throw Error('Unsupported Raw profile loader.');putWord(out,at+9,0x8000);putWord(out,at+13,0x7080);
  if(base[0x2afe99]!==0xae)throw Error('Unsupported inline weight reader.');out[0x2afe99]=0x70;
  for(const field of [40,41,42,43]){const old=0xaefaf5+field,pattern=[191,old&255,old>>>8&255,old>>>16];const p=search(base,pattern,0x2afebc,0x2aff20);if(p<0)throw Error('Unsupported Raw attributes.');putLong(out,p+1,0x708000+field);}
  const stats=out.slice(0x708000+12*45+40,0x708000+12*45+44),values=[(-(stats[0]-6)*4)&65535,stats[2]+4,stats[1],stats[3]],tail=search(base,bytes('a9 f0 ff 99 36 0e a9 0e 00 99 50 0e'),0x2afebc,0x2aff30);
  if(tail<0)throw Error('Unsupported Raw extra attribute entry.');[1,7,13,19].forEach((d,i)=>putWord(out,tail+d,values[i]));
  if(base[0x19d43f]!==12)throw Error('This ROM already changes the roster count.');out[0x19d43f]=13;const back=search(base,bytes('a9 0b 00'),0x19d420,0x19d440);if(back<0)throw Error('Unsupported Raw character selector.');out[back+1]=12;
  out.set(base.slice(0x2cc49a,0x2cc6fa),0x70e800);out.set(source.slice(manifest.palette.offset,manifest.palette.offset+32),0x70e9c0);putWord(out,0x2cf212,0xe800);out[0x2cf218]=0x70;
  const specials=[1,600,540,266,65535,65535];
  [0x2dd36f,0x2dd387,0x2dd39f,0x2dd3b7,0x2dd3cf,0x2dd3e7].forEach((old,i)=>{
   const target=0x708600+i*32;out.set(base.slice(old,old+24),target);putWord(out,target+24,specials[i]);let refs=0;
   for(const bank of [128,192]){const address=old|bank<<16,pattern=[address&255,address>>>8&255,address>>>16&255];let pos=0;
    while((pos=search(base,pattern,pos,0x300000))>=0){if([191,127,255].includes(base[pos-1])){putLong(out,pos,target);refs++;}pos++;}}
   if(!refs)throw Error('Unsupported Raw signature table.');
  });
  for(const [address,code,hook]of manifest.programs[native?'native':'stock']){out.set(code,address);out[hook]=92;putLong(out,hook+1,address);}
  out.set(Array.from('PERFECT-SLOT-PROTO1',c=>c.charCodeAt(0)),0x70fe00);
  if(manifest.coverage.matched_royal_poses)out.set(Array.from(POSES_MARKER,c=>c.charCodeAt(0)),0x70fe60);
  return {bytes:out,report:{...manifest.coverage,slot:12,primary_tiles:counts.primary,secondary_tiles:counts.secondary,packet_end:packet}};
 }
 // Older imports (v0.16) hold mirrored attacker drawings and the previous hooks. Rewrite the Perfect-Plex in
 // place: new attacker tiles are appended to the slot's private space (the old ones become unused), and the
 // hook programs and streams are replaced. Everything else in the ROM is kept.
 function plexCurrent(data){return data.length===0x800000&&String.fromCharCode(...data.slice(0x70fe20,0x70fe20+PLEX_MARKER.length))===PLEX_MARKER;}
 function updatePlex(data,source,manifest){
  if(data.length!==0x800000||String.fromCharCode(...data.slice(0x70fe00,0x70fe13))!=='PERFECT-SLOT-PROTO1')throw Error('Add Mr. Perfect first.');
  if(source.length!==0x200000)throw Error('Use the USA SNES Royal Rumble ROM.');
  const out=data.slice(),cache=new Map();let count=0;
  while(count<16384&&!(out[0x7d0000+count*3]===255&&out[0x7d0001+count*3]===255&&out[0x7d0002+count*3]===255))count++;
  let packet=long(out,0x70fdf0);
  const store=raw=>{
   const encoded=packed(raw);if(count>=16384)throw Error('The added wrestler has no free tile entries.');
   if((packet&65535)+encoded.length>65536)packet=(packet+65535)&~65535;
   if(packet<0x750000||packet+encoded.length>0x7d0000)throw Error('The added wrestler has no more sprite space.');
   out.set(encoded,packet);putLong(out,0x7d0000+count*3,packet);packet+=encoded.length;return count++;
  };
  const pixel=(d,ref)=>{const key=ref?ref.join(':'):'blank';if(!cache.has(key))cache.set(key,tile(d,ref));return cache.get(key);};
  // The generic receiving stream reads stock profiles; those addresses are unchanged in an imported ROM.
  writePlex(out,data,source,manifest,store,ref=>pixel(source,ref));putLong(out,0x70fdf0,packet);
  // The slot worker chains to the gear dispatcher (JML $4BE100) only in the 'native' variant.
  const variant=search(data,[92,0,225,75],0x70f000,0x70f100)>=0?'native':'stock';
  if(String.fromCharCode(...data.slice(0x70fe40,0x70fe49)).startsWith('ROYAL-RX'))throw Error('Remove the receiving sprites before updating the Perfect-Plex.');
  for(const [address,code,hook]of manifest.programs[variant]){out.fill(255,address,address+256);out.set(code,address);out[hook]=92;putLong(out,hook+1,address);}
  checksum(out);return out;
 }
 // Older imports hold adapted Raw Bret art in pieces where Royal Perfect has the pose (manifest rows with
 // 'replaces'). Rebuild the slot's pieces: a piece is replaced only while its pixels still hash to the adapted
 // art it supersedes; every other piece, including the user's edits and the Perfect-Plex frames, is decoded
 // and stored again pixel for pixel. The slot's tile space is repacked, so the new art fits.
 function posesCurrent(data){return data.length===0x800000&&String.fromCharCode(...data.slice(0x70fe60,0x70fe60+POSES_MARKER.length))===POSES_MARKER;}
 function pieceHash(points){
  const list=[...points].map(([k,v])=>{const [x,y]=k.split(',').map(Number);return [x,y,v];}).sort((a,b)=>a[1]-b[1]||a[0]-b[0]);
  let h=0x811c9dc5;for(const [x,y,v]of list)for(const c of `${x},${y},${v};`){h^=c.charCodeAt(0);h=Math.imul(h,0x01000193)>>>0;}return h;
 }
 function upgradePoses(data,source,manifest){
  if(data.length!==0x800000||String.fromCharCode(...data.slice(0x70fe00,0x70fe13))!=='PERFECT-SLOT-PROTO1')throw Error('Add Mr. Perfect first.');
  if(String.fromCharCode(...data.slice(0x70fe40,0x70fe49)).startsWith('ROYAL-RX'))throw Error('Remove the receiving sprites before updating the poses.');
  const P=window.RAW_PARTS,out=data.slice(),cache=new Map(),rows=new Map(manifest.frames.map(f=>[f.kind+':'+f.index,f]));
  const royalPixels=ref=>{const key=ref?ref.join(':'):'blank';if(!cache.has(key))cache.set(key,tile(source,ref));return cache.get(key);};
  // Packets of other identities' edits relocated into this space would be lost; refuse instead.
  for(const r of Object.values(window.RAW_NWO_GEAR_PATTERNS||{}))for(const [a,b]of [[r.pointers,r.pointer_end],[r.secondary_pointers,r.secondary_pointer_end]]){
   if(a===undefined||b===undefined)continue;for(let p=a;p+3<=b;p+=3){const v=long(data,p);if(v>=0x750000&&v<0x7d0000)throw Error('Another wrestler’s edited tile is stored in Mr. Perfect’s space; the poses were not updated.');}
  }
  const frames=[],report={replaced:0,recoloured:0,kept_edited:0,kept:0};
  for(const [kind,indices]of [['primary',[...Array(998).keys(),...Array.from({length:12},(_,i)=>1000+i)]],['secondary',[...Array(722).keys()]]])for(const index of indices){
   let current;try{current=P.resolveIndex(data,12,kind,index);}catch(e){throw Error(`Mr. Perfect's ${kind} piece ${index} cannot be read (${e.message}); the poses were not updated.`);}
   const row=rows.get(kind+':'+index);let parts=current.parts;
   if(row&&row.replaces!==undefined){
    const points=P.raster(current.parts);
    if(pieceHash(points)===row.replaces){parts=row.royal?row.parts.map(p=>({...p,pixels:p.refs.map(royalPixels)})):recolourParts(current.parts,hairChanges(points));
     report[row.royal?'replaced':'recoloured']=(report[row.royal?'replaced':'recoloured']||0)+1;}
    else report.kept_edited++;
   }else report.kept++;
   frames.push({kind,index,parts,descriptor:index>=1000?current.descriptor:null});
  }
  let count={primary:0,secondary:0};while(count.primary<16384&&!equal(data,0x7d0000+count.primary*3,[255,255,255]))count.primary++;
  out.fill(255,0x7d0000,Math.min(0x7da000,0x7d0000+count.primary*3));out.fill(255,0x749800,0x750000);out.fill(255,0x750000,0x7d0000);
  out.fill(255,0x720100,0x730000);out.fill(255,0x740100,0x749800);
  const tiles={primary:new Map(),secondary:new Map()},pointers={primary:0x7d0000,secondary:0x749800};let packet=0x750000;
  const store=(raw,kind)=>{
   const key=String.fromCharCode(...raw);if(tiles[kind].has(key))return tiles[kind].get(key);
   const index=count[kind]=tiles[kind].size,encoded=packed(raw);
   if(pointers[kind]+index*3+3>(kind==='primary'?0x7da000:0x750000))throw Error('Mr. Perfect’s poses exceed the tile pointer space; the poses were not updated.');
   if((packet&65535)+encoded.length>65536)packet=(packet+65535)&~65535;
   if(packet+encoded.length>0x7d0000)throw Error('Mr. Perfect’s poses exceed the sprite space; the poses were not updated.');
   out.set(encoded,packet);putLong(out,pointers[kind]+index*3,packet);packet+=encoded.length;tiles[kind].set(key,index);return index;
  };
  const cursor={primary:0x720100,secondary:0x740100},descriptors={primary:new Map(),secondary:new Map()};
  for(const f of frames){
   const parts=[...f.parts].sort((a,b)=>b.size-a.size),record=[parts.length,parts.filter(p=>p.size===16).length];
   if(!parts.length){record[0]=1;record.push(0,0,105);const id=0xc000|store(new Uint8Array(32),f.kind);record.push(id&255,id>>>8);}
   for(const p of parts){
    if(p.x< -64||p.x>=64||p.y< -105||p.y>=23)throw Error('A sprite position is outside Raw’s format.');
    record.push(0,p.x&127,(p.y+105)&127);
    for(let ty=0;ty<p.size/8;ty++)for(let tx=0;tx<p.size/8;tx++){
     const image=[];for(let y=0;y<8;y++)for(let x=0;x<8;x++){let sx=tx*8+x,sy=ty*8+y;if(p.hflip)sx=p.size-1-sx;if(p.vflip)sy=p.size-1-sy;image.push(p.pixels[Math.floor(sy/8)*(p.size/8)+Math.floor(sx/8)][sy%8*8+sx%8]);}
     const id=0xc000|store(planar(image),f.kind);record.push(id&255,id>>>8);
    }
   }
   let address;
   if(f.descriptor!==null){address=f.descriptor;out.set(record,address);}
   else{const key=String.fromCharCode(...record);address=descriptors[f.kind].get(key);
    if(address===undefined){address=cursor[f.kind];const end=f.kind==='primary'?0x730000:0x749800;
     if((address&65535)+record.length>65536)address=(address+65535)&~65535;
     if(address+record.length>end)throw Error('Mr. Perfect’s pose descriptions exceed their space; the poses were not updated.');
     out.set(record,address);cursor[f.kind]=address+record.length;descriptors[f.kind].set(key,address);}}
   putLong(out,(f.kind==='primary'?0x710000:0x711000)+f.index*3,address);
  }
  putLong(out,0x70fdf0,packet);out.set(Array.from(POSES_MARKER,c=>c.charCodeAt(0)),0x70fe60);checksum(out);
  return {bytes:out,report:{...report,primary_tiles:tiles.primary.size,secondary_tiles:tiles.secondary.size,packet_end:packet}};
 }
 return {build,updatePlex,plexCurrent,posesCurrent,upgradePoses,pieceHash,hairChanges,tile,planar,packed,royalBlock,royalPortrait,checksum,word,long,putWord,putLong,search};
})();
