/* Receiving drawings painted with each wrestler's own Raw art (plans in data/receiving-art.json). */
window.RAW_RECEIVING_ART=(()=>{
 const SIZE=144,OX=72,OY=105;
 // Choose 8x8/16x16 objects covering an image, within an actor's limits (15 objects incl. headroom for
 // the shadow, 60 tiles). Same search and tie-breaking as tools/build_shawn_superkick_animation.pack +
 // tools/canonical_perfect_geometry.chunks_for.
 function pack(image){
  const at=(x,y)=>x>=0&&y>=0&&x<SIZE&&y<SIZE?image[y*SIZE+x]:0,options=[];
  for(let gy=0;gy<16;gy+=4)for(let gx=0;gx<16;gx+=4){
   const groups=[];
   for(let y=gy-16;y<SIZE;y+=16)for(let x=gx-16;x<SIZE;x+=16){
    const small=[];for(const [ty,tx]of [[0,0],[0,1],[1,0],[1,1]]){let any=false;for(let yy=0;yy<8&&!any;yy++)for(let xx=0;xx<8;xx++)if(at(x+tx*8+xx,y+ty*8+yy)){any=true;break;}if(any)small.push([x+tx*8,y+ty*8,8]);}
    if(small.length)groups.push([x,y,small]);
   }
   let states=new Map([['0,0',[0,0,[]]]]);
   for(const [x,y,small]of groups){
    const next=new Map();
    for(const [objects,tiles,chosen]of states.values())for(const [parts,cost]of [[small,small.length],[[[x,y,16]],4]]){
     const o=objects+parts.length,t=tiles+cost;if(o<=17&&t<=60)next.set(o+','+t,[o,t,chosen.concat(parts)]);
    }
    states=next;
   }
   for(const s of states.values())options.push(s);
  }
  const legal=options.filter(([o,t])=>o+2<=17&&t+4<=64);if(!legal.length)throw Error('Receiving drawing exceeds the object limits.');
  let best=legal[0];for(const s of legal)if(s[1]<best[1]||(s[1]===best[1]&&s[0]<best[0]))best=s;
  const out=best[2].map(([x,y,s])=>[x-OX,y-OY,s]).sort((a,b)=>b[2]-a[2]||a[1]-b[1]||a[0]-b[0]);
  for(const [x,y]of out)if(x<-64||x>=64||y<-105||y>=23)throw Error('Receiving drawing exceeds the descriptor range.');
  return out;
 }
 // Donor pose in canonical facing, as the Raw counterpart's colour-role indices, plus the Royal component
 // (0 upper body, 1 lower body) that drew each pixel.
 function donorImage(source,recipes,selector,pose,colourMap,regions){
  const RI=window.RAW_ROYAL_IMPORT_CORE,shift=recipes.canonical.mirror_shift,image=new Uint8Array(SIZE*SIZE),cache=new Map();
  for(const part of [...recipes.workers[selector].poses[pose].parts].reverse())for(let y=0;y<part.size;y++)for(let x=0;x<part.size;x++){
   const sx=part.hflip?part.size-1-x:x,sy=part.vflip?part.size-1-y:y,ref=part.refs[Math.floor(sy/8)*(part.size/8)+Math.floor(sx/8)],key=ref?ref.join(':'):'blank';
   if(!cache.has(key))cache.set(key,RI.tile(source,ref));const v=cache.get(key)[sy%8*8+sx%8];
   const X=OX+shift-(part.x+x),Y=OY+part.y+y;if(v&&X>=0&&X<SIZE&&Y>=0&&Y<SIZE){image[Y*SIZE+X]=colourMap[v];if(regions)regions[Y*SIZE+X]=part.component||0;}
  }
  return image;
 }
 // Colour roles differ by body region between workers (one worker's tights index is another's kneepad).
 // Learn counterpart -> target index maps from co-located pixels of the same frame parts in the loaded ROM,
 // separately for upper-body (primary) and lower-body (secondary) parts. Majority vote; unseen = same index.
 function roleMaps(base,counterpart,target){
  const P=window.RAW_PARTS,maps=[];
  for(const [kind,count]of [['primary',527],['secondary',426]]){
   const votes=Array.from({length:16},()=>new Map());
   for(let i=0;i<count;i+=2){
    let a,b;try{a=P.raster(P.resolveIndex(base,counterpart,kind,i).parts);b=P.raster(P.resolveIndex(base,target,kind,i).parts);}catch(e){continue;}
    for(const [k,v]of a){const w=b.get(k);if(w)votes[v].set(w,(votes[v].get(w)||0)+1);}
   }
   maps.push(votes.map((m,v)=>{let best=v,n=-1;for(const [w,c]of m)if(c>n||(c===n&&w<best)){best=w;n=c;}return best;}));
  }
  return maps;
 }
 // One slot's drawings from a donor plan: the slot's own parts (clipped to the donor silhouette, dilated by
 // one pixel) on top, donor colour roles underneath where no own part reaches.
 function render(base,source,recipes,slot,spec){
  const plan=recipes.receiving_art.donors[String(spec.donor)],P=window.RAW_PARTS;
  if(!plan)throw Error(`No receiving plan for donor ${spec.donor}.`);
  const roles=roleMaps(base,plan.counterpart_slot,slot);
  return plan.poses.map(({pose,parts})=>{
   const regions=new Uint8Array(SIZE*SIZE),donor=donorImage(source,recipes,spec.donor,pose,plan.colour_map,regions),near=new Uint8Array(SIZE*SIZE),image=new Uint8Array(SIZE*SIZE);
   for(let y=0;y<SIZE;y++)for(let x=0;x<SIZE;x++)if(donor[y*SIZE+x])for(let dy=-1;dy<=1;dy++)for(let dx=-1;dx<=1;dx++){const X=x+dx,Y=y+dy;if(X>=0&&Y>=0&&X<SIZE&&Y<SIZE)near[Y*SIZE+X]=1;}
   for(const p of [...parts].reverse()){
    for(const [key,v]of P.raster(P.resolvePart(base,slot,p.part).parts,0,0,p.flip)){
     const [x,y]=key.split(',').map(Number),X=OX+p.x+x,Y=OY+p.y+y;if(X>=0&&Y>=0&&X<SIZE&&Y<SIZE&&near[Y*SIZE+X])image[Y*SIZE+X]=v;
    }
   }
   for(let i=0;i<image.length;i++)if(!image[i]&&donor[i])image[i]=roles[regions[i]][donor[i]];
   const row=recipes.workers[spec.donor].poses[pose];
   return {image,chunks:pack(image),body_dx:row.body_dx,shadow_dx:row.shadow_dx};
  });
 }
 // The slot's own native receiving sequence (Raw's stock receiving-suplex drawings, positioned exactly as
 // the generic path places them: stock profile entries + the importer's per-step translate), copied into
 // private drawings. Identity, gear and user edits come from the loaded ROM; nothing is borrowed from
 // another worker. Choreography is Raw's lift-and-fall, not Royal's exact Perfect-Plex frames.
 function ownNative(base,slot){
  const P=window.RAW_PARTS,victim=window.RAW_ROYAL_IMPORT_MANIFEST.victim;
  return victim.map(row=>{
   const points=new Map();
   for(const [id,dx,dy]of P.profileParts(base,row.profile)){if(id===0x8024)continue;P.raster(P.resolvePart(base,slot,id).parts,dx+row.translate[0],dy+row.translate[1],false,points);}
   let left=Infinity,right=-Infinity;for(const k of points.keys()){const x=Number(k.split(',')[0]);left=Math.min(left,x);right=Math.max(right,x);}
   const body=Math.round((left+right+1)/2),image=new Uint8Array(SIZE*SIZE);
   for(const [k,v]of points){const [x,y]=k.split(',').map(Number),X=OX+x-body,Y=OY+y;if(X<0||Y<0||X>=SIZE||Y>=SIZE)throw Error('Receiving drawing exceeds its canvas.');image[Y*SIZE+X]=v;}
   // Stock shadow extent is [-14, 18) from its origin: centre it under the body.
   return {image,chunks:pack(image),body_dx:body,shadow_dx:body-2};
  });
 }
 return {pack,render,donorImage,roleMaps,ownNative};
})();
