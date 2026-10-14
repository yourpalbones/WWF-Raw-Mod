/* Paired animation preview: performer and receiver composed the way the game places them. */
window.RAW_ANIMATION_PREVIEW=(()=>{
 const P=window.RAW_PARTS,long=(d,a)=>d[a]|d[a+1]<<8|d[a+2]<<16;
 // Frames each Perfect-Plex step stays on screen, measured natively in all ten verification captures
 // (evidence/perfect-plex-receivers/fixed/verification.json; per-scenario jitter is +/-1 frame). Later stream
 // entries (the held pin, release and recovery: docs/perfect-plex-exit.md) last STEP_FRAMES each.
 const PLEX_TIMING={frames:[7,7,7,6,7,8,7,7,7,7,6,7],source:'native capture'},STEP_FRAMES=7,AFTER_FRAMES=60;
 // After the streams: Raw's standing action (stream $C0:03A2) for Mr. Perfect, turned toward the receiver, and
 // its downed action (stream $C0:067A) for the receiver.
 const STANDING_STREAM=0x0403a2,DOWNED_STREAM=0x04067a;
 const SPACING=40,FLIP_PIVOT=8;
 const NAMES=['Luna Vachon','Bret Hart','Undertaker','Yokozuna','Bam Bam Bigelow','Razor Ramon / Scott Hall','Lex Luger','Doink / Sting','Shawn Michaels','1-2-3 Kid / Syxx','Diesel / Kevin Nash','Owen Hart','Mr. Perfect'];
 // Stream entries: [bank, profile, x move, y move, draw x, draw y]; x moves and draw x count along the facing.
 const signed=v=>v>127?v-256:v;
 function stream(rom,base){const out=[];for(let i=0;i<40;i++){const e=base+i*7;if(rom[e]===0xff)break;out.push({profile:P.fileOffset(rom[e]<<16|rom[e+1]|rom[e+2]<<8,rom.length),move:signed(rom[e+3]),draw:[signed(rom[e+5]),signed(rom[e+6])]});}return out;}
 function profile(rom,at){const out=[];let id;while((id=rom[at]|rom[at+1]<<8)!==0xffff){const dx=rom[at+2],dy=rom[at+3];out.push([id,dx>127?dx-256:dx,dy>127?dy-256:dy]);at+=4;}return out;}
 // Receiving drawings (RX2/RX3): descriptors listed per slot, tiles in the receiving namespace.
 function receiverPart(rom,slot,id){
  const marker=String.fromCharCode(...rom.slice(0x70fe40,0x70fe49)),table=long(rom,0x71d000+slot*3),i=id/3-1200;
  const d=P.parseDescriptor(rom,'primary',long(rom,table+i*3)),pointers=['ROYAL-RX3','ROYAL-RX4'].includes(marker)?0x7da000:0x5e0000;
  for(const p of d.parts){p.pixels=p.tiles.map(t=>{let o=long(rom,pointers+(t.id&0x3fff)*3);if(o>=0x3e0000&&o<0x400000)o+=0x400000;return decode(rom,o);});}
  return d.parts;
 }
 function decode(rom,o){const raw=new Uint8Array(32);let c=o+4;for(let i=0;i<32;i++)if(rom[o+(i>>3)]>>(7-i%8)&1)raw[i]=rom[c++];const px=new Array(64);for(let y=0;y<8;y++)for(let x=0;x<8;x++){let v=0;for(let p=0;p<4;p++)v|=((raw[(p>>1)*16+y*2+(p&1)]>>(7-x))&1)<<p;px[y*8+x]=v;}return px;}
 function actorParts(rom,slot,id){
  if(slot!==12&&id>=3600&&id<3636&&long(rom,0x71d000+slot*3))return receiverPart(rom,slot,id);
  return P.resolvePart(rom,slot,id).parts;
 }
 // Sequence of steps for a move. 'performer' and 'receiver' are slots.
 // Each step carries both actors' positions along their facing (moved by the entries so far) and draw offsets.
 function plexSteps(rom,receiver){
  const attacker=stream(rom,0x730000);
  const own=long(rom,0x71d040+receiver*3),receiving=own?stream(rom,own):stream(rom,0x735000);
  const steps=[],at={attacker:0,receiver:0},count=Math.max(attacker.length,receiving.length);
  const actor=(list,i,key)=>{const e=list[Math.min(i,list.length-1)];if(i<list.length)at[key]+=e.move;return {entries:profile(rom,e.profile),move:at[key],draw:e.draw};};
  for(let i=0;i<count;i++)steps.push({attacker:actor(attacker,i,'attacker'),receiver:actor(receiving,i,'receiver'),frames:i<12?PLEX_TIMING.frames[i]:STEP_FRAMES,label:i<12?'step '+(i+1):i<12+exitHold(rom)?'pin':'release'});
  const after=(base,move)=>{const e=stream(rom,base)[0];return {entries:profile(rom,e.profile),move,draw:e.draw};};
  if(attacker.length>12)steps.push({attacker:{...after(STANDING_STREAM,at.attacker),turn:true},receiver:after(DOWNED_STREAM,at.receiver),frames:AFTER_FRAMES,label:'Perfect stands; receiver down until P2 presses'});
  return {steps,receiverSource:own?'own receiving drawings':'generic stock receiving parts (no receiving drawings for this slot)'};
 }
 // Held bridge entries: those after step 11 that still show step 11's profile.
 function exitHold(rom){const a=stream(rom,0x730000);let n=0;while(12+n<a.length&&a[12+n].profile===a[11].profile)n++;return n;}
 // Paint one actor: unflipped objects at origin+dx; flipped at origin-dx-size+8 (measured flip rule).
 // Raw draws single-colour pieces (its shadows, e.g. in the stock get-up profiles) in the shadow palette.
 function paintActor(rom,slot,entries,ox,oy,flip,into,shadow,shadowPoints){
  for(const [id,dx,dy]of [...entries].reverse()){
   if(id===0x8024){shadow.push([flip?ox-dx:ox+dx,oy+dy]);continue;}
   const points=new Map();P.raster(actorParts(rom,slot,id),flip?ox-dx+FLIP_PIVOT:ox+dx,oy+dy,flip,points);
   if(new Set(points.values()).size<=1){for(const key of points.keys())shadowPoints.add(key);continue;}
   const target=into.get(slot)||into.set(slot,new Map()).get(slot);for(const [key,v]of points)target.set(key,v);
  }
 }
 // Actors start SPACING apart; an unflipped actor moves and draws toward +x, a flipped one toward -x.
 function compose(rom,receiver,step,attackerLeft){
  const layers=new Map(),shadows=[],shadowPoints=new Set(),y=150,start=128-SPACING/2*(attackerLeft?1:-1);
  const place=(x,flip,s)=>({x,origin:x+(flip?-1:1)*s.draw[0],y:y+s.draw[1]});
  const rFlip=attackerLeft,rx=start+(attackerLeft?SPACING:-SPACING)+(rFlip?-1:1)*step.receiver.move;
  let aFlip=!attackerLeft;const ax=start+(aFlip?-1:1)*step.attacker.move;
  if(step.attacker.turn)aFlip=rx<ax;   // Raw's standing action faces the opponent
  const r=place(rx,rFlip,step.receiver),a=place(ax,aFlip,step.attacker);
  paintActor(rom,receiver,step.receiver.entries,r.origin,r.y,rFlip,layers,shadows,shadowPoints);
  const recv=layers.get(receiver)||new Map();layers.delete(receiver);
  paintActor(rom,12,step.attacker.entries,a.origin,a.y,aFlip,layers,shadows,shadowPoints);
  return {receiver:recv,attacker:layers.get(12)||new Map(),shadows,shadowPoints};
 }
 function draw(canvas,rom,receiver,step,attackerLeft){
  const ctx=canvas.getContext('2d'),img=ctx.createImageData(canvas.width,canvas.height),c=compose(rom,receiver,step,attackerLeft);
  const rgb=v=>[0,5,10].map(s=>Math.floor((v>>s&31)*255/31));
  for(let i=0;i<img.data.length;i+=4)img.data.set([42,44,54,255],i);
  const put=(x,y,col)=>{if(x<0||y<0||x>=canvas.width||y>=canvas.height)return;img.data.set([...col,255],(y*canvas.width+x)*4);};
  for(const [sx,sy]of c.shadows)for(let x=-14;x<18;x++)for(let y=-3;y<3;y++)if((x+y)%2===0)put(sx+x,sy+y,[20,20,26]);
  for(const key of c.shadowPoints){const [x,y]=key.split(',').map(Number);put(x,y,[20,20,26]);}
  // The receiver is drawn first; the performer's objects come first in OAM, so it appears on top.
  for(const [slot,points]of [[receiver,c.receiver],[12,c.attacker]]){const pal=P.palette(rom,slot).map(rgb);for(const [key,v]of points){const [x,y]=key.split(',').map(Number);put(x,y,pal[v]);}}
  ctx.putImageData(img,0,0);
 }
 function mount(){
  const $=id=>document.getElementById(id);if(!$('anim-card'))return;
  let state={rom:null,steps:[],index:0,timer:null,frame:0};
  const render=()=>{if(!state.rom||!state.steps.length)return;try{const step=state.steps[state.index];draw($('anim-canvas'),state.rom,Number($('anim-receiver').value),step,$('anim-facing').value==='left');
   $('anim-frame').textContent=`Step ${state.index+1} of ${state.steps.length} (${step.label}) · ${step.frames} frames (${(step.frames/60).toFixed(2)} s) · timing: ${PLEX_TIMING.source}`;}catch(e){$('anim-source').textContent='Preview unavailable: '+e.message;}};
  const stop=()=>{clearInterval(state.timer);state.timer=null;$('anim-play').textContent='Play';};
  // Never let the preview interrupt loading or editing: report problems in the card instead.
  const load=()=>{stop();state.rom=typeof rom!=='undefined'?rom:null;$('anim-card').hidden=!state.rom||!(P.hasPerfect(state.rom));if($('anim-card').hidden)return;
   try{const plan=plexSteps(state.rom,Number($('anim-receiver').value));state.steps=plan.steps;state.index=0;$('anim-source').textContent='Receiver art: '+plan.receiverSource+'.';render();}
   catch(e){state.steps=[];$('anim-source').textContent='Preview unavailable for this ROM: '+e.message;}};
  $('anim-receiver').replaceChildren(...NAMES.map((n,i)=>new Option(n,i)));$('anim-receiver').value='2';
  $('anim-receiver').onchange=load;$('anim-facing').onchange=render;
  $('anim-step-back').onclick=()=>{stop();state.index=(state.index+state.steps.length-1)%state.steps.length;render();};
  $('anim-step').onclick=()=>{stop();state.index=(state.index+1)%state.steps.length;render();};
  $('anim-play').onclick=()=>{if(state.timer)return stop();$('anim-play').textContent='Pause';state.frame=0;
   state.timer=setInterval(()=>{if(++state.frame>=state.steps[state.index].frames){state.frame=0;state.index=(state.index+1)%state.steps.length;render();}},1000/60);};
  return load;
 }
 return {mount,compose,plexSteps,PLEX_TIMING,NAMES,stream};
})();
