/* Selection assets are decoded locally from the verified original ROM. */
const S=window.RAW_SELECTION_MANIFEST;
let selectionEdits={}, selectionOriginals={};
function decodePortrait(data,offset){
 const length=data[offset]|data[offset+1]<<8, mode=data[offset+2], out=new Uint8Array(length);let cursor=offset+3,y=length+(mode===2&&length%2===0?1:0),first=true;
 const read=()=>data[cursor++],put=(p,v)=>{if(p<0||p>=length)throw Error('Invalid portrait block');out[p]=v;};
 for(let limit=0;limit<length*2+1024;limit++){
  if(mode===2&&first&&y===1){y=length+(length&1);first=false;}
  const control=read(),step=mode===2?2:1;
  if(control&128){const distance=((control&7)<<8|read())+1,count=((control&120)>>3)+3;y-=step*count;let source=y+step*distance;if(mode===2&&source>=length)source=source-length+(length%2===0?1:0);for(let i=count-1;i>=0;i--)put(y+step*i,out[source+step*i]);}
  else if(control&64){const count=(control&63)+1,values=Array.from({length:count},read);y-=step*count;values.forEach((v,i)=>put(y+step*i,v));}
  else if(mode===1&&control&32){y--;put(y,out[y+(control&31)+1]);}
  else if(mode===2&&control&32){const count=(control&31)+3,value=read();for(let i=0;i<count;i++){y-=2;put(y,(value-i)&255);}}
  else if(control){const count=(control&31)+2,value=read();y-=step*count;for(let i=0;i<count;i++)put(y+step*i,value);}
  else return out;
 }
 throw Error('Portrait decoder did not finish');
}
function portraitPacket(pixels){
 const data=new Uint8Array(15360);
 for(let y=0;y<120;y++)for(let x=0;x<128;x++){const color=pixels[y*128+x]+64,base=((y>>3)*16+(x>>3))*64;for(let p=0;p<8;p++)data[base+(p>>1)*16+(y%8)*2+(p&1)]|=((color>>p)&1)<<(7-x%8);}
 const out=[0,60,1];for(let end=data.length;end>0;){const start=Math.max(0,end-64);out.push(64+(end-start)-1,...data.slice(start,end));end=start;}out.push(0);return new Uint8Array(out);
}
function originalSelection(id){
 if(selectionOriginals[id])return selectionOriginals[id];const meta=S.characters[id],bytes=decodePortrait(rom,romPointer(rom,meta.record)),pixels=[];
 for(let y=0;y<120;y++)for(let x=0;x<128;x++){let color=0,base=((y>>3)*16+(x>>3))*64;for(let p=0;p<8;p++)color|=((bytes[base+(p>>1)*16+(y%8)*2+(p&1)]>>(7-x%8))&1)<<p;if(color<64||color>127)throw Error('Unexpected portrait color range');pixels.push(color-64);}
 const colors=Array.from({length:64},(_,i)=>rom[meta.palette_offset+i*2]|rom[meta.palette_offset+i*2+1]<<8);
 const bio={};for(const [field,address]of Object.entries(meta.fields)){let pos=field==='weight'?address:0x2e0000+(rom[address]|rom[address+1]<<8),text='';while(rom[pos]!==0&&text.length<64)text+=String.fromCharCode(rom[pos++]);bio[field]=text.replaceAll('\r','\n');}
 return selectionOriginals[id]={pixels,colors,bio};
}
function selectionState(id){const original=originalSelection(id),edit=selectionEdits[id]||{};return {portrait:edit.portrait||original,bio:{...original.bio,...edit.bio}};}
function renderSelection(){if(!rom)return;const state=selectionState(M.id),canvas=$('portrait'),context=canvas.getContext('2d'),image=context.createImageData(128,120);
 state.portrait.pixels.forEach((value,i)=>{const w=state.portrait.colors[value];image.data.set([0,5,10].map(s=>Math.floor((w>>s&31)*255/31)).concat(255),i*4);});context.putImageData(image,0,0);
 for(const [field,value]of Object.entries(state.bio))$('bio-'+field).value=value;
 const newText=new Set();for(const id of Object.keys(S.characters))for(const [field,value]of Object.entries(selectionState(id).bio)){if(field==='weight')continue;const address=S.characters[id].fields[field],pointer=0x2e0000+(rom[address]|rom[address+1]<<8);if(value!==originalSelection(id).bio[field]||S.text_regions.some(r=>pointer>=r.offset&&pointer<r.offset+r.length))newText.add(value);}const textUsed=[...newText].reduce((n,text)=>n+text.length+1,0);
 $('selection-status').textContent=`128 × 120 portrait · 64 colors · ${Object.values(selectionEdits).filter(e=>e.portrait).length} imported portraits. Bio text space: ${textUsed} of 183 used. Original shared strings are preserved.`;renderProfileAssets();renderMatchName();renderCustomMusic();
}
function validateBio(bio,id=M.id){const limits={name:[1,14],from:[3,12],height:[1,8],special:[3,11],weight:[1,3]};
 if(!bio||typeof bio!=='object'||Array.isArray(bio))throw Error('Invalid bio data');
 for(const [field,value]of Object.entries(bio)){if(field==='name'&&value!==originalSelection(id).bio.name&&!/^[A-Z ]+$/.test(value))throw Error('New names support uppercase letters and spaces.');if(!Object.hasOwn(limits,field)||typeof value!=='string')throw Error('Invalid bio field');const [lines,width]=limits[field],parts=value.split('\n');if(!value||parts.length>lines||parts.some(p=>!p.length||(p.length>width&&(field!=='name'||value!==originalSelection(id).bio.name)))||!/^[A-Z0-9 .,\-'"%\n]+$/.test(value)||(field==='weight'&&!/^\d{1,3}$/.test(value)))throw Error(`Check ${field}: uppercase text, up to ${lines} lines of ${width} characters.`);}
}
function validateSelection(edits){if(!edits||typeof edits!=='object'||Array.isArray(edits))throw Error('Invalid selection edits');
 for(const [id,edit]of Object.entries(edits)){if(!Object.hasOwn(S.characters,id)||!edit||typeof edit!=='object'||Array.isArray(edit)||Object.keys(edit).some(k=>!['portrait','bio','monitor','logo','logoName','theme','hudName','hud','song'].includes(k)))throw Error('Invalid selection character');if(edit.song)compileSong(edit.song);if(edit.bio)validateBio(edit.bio,id);validateProfileAssets(edit,id);if(edit.hudName!==undefined)matchNamePixels(edit.hudName);if(edit.hud&&(!Array.isArray(edit.hud.pixels)||edit.hud.pixels.length!==512||edit.hud.pixels.some(v=>!Number.isInteger(v)||v<0||v>15)||edit.hudName!==undefined))throw Error('Invalid match name graphics');
 if(edit.portrait){const p=edit.portrait;if(!Array.isArray(p.pixels)||p.pixels.length!==15360||p.pixels.some(v=>!Number.isInteger(v)||v<0||v>63)||!Array.isArray(p.colors)||p.colors.length!==64||p.colors.some(v=>!Number.isInteger(v)||v<0||v>32767))throw Error('Invalid portrait pixels or colors');}}
}
function selectionRecords(){const records=[],strings=new Map(),regions=S.text_regions.map(r=>({...r}));let expanded=false;
 for(const id of Object.keys(S.characters)){
  const edit=selectionEdits[id]||{},meta=S.characters[id];
  if(edit.portrait){expanded=true;const address=S.portrait_base+Number(id)*S.portrait_stride,packet=portraitPacket(edit.portrait.pixels);records.push([address,packet],[meta.record,new Uint8Array([address&255,address>>8&255,(address>>16)|192])]);const palette=new Uint8Array(128);edit.portrait.colors.forEach((v,i)=>{palette[i*2]=v&255;palette[i*2+1]=v>>8;});records.push([meta.palette_offset,palette]);}
  for(const [field,value]of Object.entries(selectionState(id).bio)){
   const pointer=field==='weight'?0:0x2e0000+(rom[meta.fields[field]]|rom[meta.fields[field]+1]<<8),relocated=S.text_regions.some(r=>pointer>=r.offset&&pointer<r.offset+r.length);
   if(value===originalSelection(id).bio[field]&&(!relocated||!Object.values(selectionEdits).some(e=>e.bio)))continue;
   if(field==='weight'){const packet=new Uint8Array(4);packet.set(Array.from(value,c=>c.charCodeAt(0)));records.push([meta.fields.weight,packet]);continue;}
   let address=strings.get(value);
   if(address===undefined){const packet=new Uint8Array(Array.from(value.replaceAll('\n','\r')+'\0',c=>c.charCodeAt(0))),region=regions.find(r=>r.length>=packet.length);if(!region)throw Error('Edited bios exceed the available text space. Shorten some text before exporting.');address=region.offset;region.offset+=packet.length;region.length-=packet.length;strings.set(value,address);records.push([address,packet]);}
   records.push([meta.fields[field],new Uint8Array([address&255,address>>8&255])]);
  }
 }
 const companion=profileAssetRecords();records.push(...companion.records);expanded ||= companion.expanded;const match=matchNameRecords();records.push(...match.records);expanded ||= match.expanded;
 const music=customMusicRecords();records.push(...music.records);expanded ||= music.expanded;return {records,expanded};
}
function quantizePortrait(rgba,limit=64){
 const counts=new Map();for(let i=0;i<rgba.length;i+=4){const channels=[0,1,2].map(c=>Math.round(rgba[i+c]*31/255)),word=channels[0]|channels[1]<<5|channels[2]<<10;counts.set(word,(counts.get(word)||0)+1);}
 let boxes=[[...counts].map(([word,count])=>({word,count,rgb:[word&31,word>>5&31,word>>10&31]}))];
 const range=box=>[0,1,2].map(c=>Math.max(...box.map(p=>p.rgb[c]))-Math.min(...box.map(p=>p.rgb[c])));
 while(boxes.length<limit){let choice=-1,score=-1,axis=0;boxes.forEach((box,i)=>{if(box.length<2)return;const ranges=range(box),span=Math.max(...ranges);if(span>score){choice=i;score=span;axis=ranges.indexOf(span);}});if(choice<0)break;const box=boxes[choice].sort((a,b)=>a.rgb[axis]-b.rgb[axis]),total=box.reduce((n,p)=>n+p.count,0);let sum=0,cut=1;for(let i=0;i<box.length-1;i++){sum+=box[i].count;cut=i+1;if(sum>=total/2)break;}boxes.splice(choice,1,box.slice(0,cut),box.slice(cut));}
 const colors=boxes.map(box=>{const total=box.reduce((n,p)=>n+p.count,0),rgb=[0,1,2].map(c=>Math.round(box.reduce((n,p)=>n+p.rgb[c]*p.count,0)/total));return rgb[0]|rgb[1]<<5|rgb[2]<<10;});while(colors.length<limit)colors.push(colors[0]);const cache=new Map(),pixels=[];
 for(let i=0;i<rgba.length;i+=4){const rgb=[0,1,2].map(c=>Math.round(rgba[i+c]*31/255)),word=rgb[0]|rgb[1]<<5|rgb[2]<<10;if(!cache.has(word)){let best=0,dist=Infinity;colors.forEach((v,k)=>{const d=[0,5,10].reduce((n,s,c)=>n+(rgb[c]-(v>>s&31))**2,0);if(d<dist){dist=d;best=k;}});cache.set(word,best);}pixels.push(cache.get(word));}return {pixels,colors};
}
$('portrait-import').onchange=async event=>{try{if(!rom)throw Error('Load the original ROM first');const file=event.target.files[0];if(!file||file.size>16*1024*1024)throw Error('Choose an image smaller than 16 MB');const id=M.id,bitmap=await createImageBitmap(file),temp=document.createElement('canvas');temp.width=128;temp.height=120;const context=temp.getContext('2d');context.fillStyle='black';context.fillRect(0,0,128,120);const scale=Math.max(128/bitmap.width,120/bitmap.height);context.drawImage(bitmap,(128-bitmap.width*scale)/2,(120-bitmap.height*scale)/2,bitmap.width*scale,bitmap.height*scale);bitmap.close();const portrait=quantizePortrait(context.getImageData(0,0,128,120).data);remember();const edit=selectionEdits[id] ||= {};edit.portrait=portrait;if($('sync-monitor').checked)edit.monitor=monitorFromPortrait(portrait,id);render();status('Portrait imported, centered and cropped to 128 × 120 with 64 SNES colors.');}catch(e){status(e.message);}event.target.value='';};
$('bio-apply').onclick=()=>{try{const bio={};for(const field of Object.keys(S.characters[M.id].fields))bio[field]=$('bio-'+field).value.toUpperCase();validateBio(bio);matchNamePixels(bio.name);const nameChanged=bio.name!==selectionState(M.id).bio.name;remember();const edit=selectionEdits[M.id] ||= {};edit.bio=bio;if(matchNamePixels(bio.name).every((v,i)=>v===originalHUD(M.id)[i]))delete edit.hudName;else edit.hudName=bio.name;delete edit.hud;if(nameChanged&&$('sync-logo').checked){edit.logoName=bio.name;delete edit.logo;}render();status('Bio saved. The name above the health bar will update too.');}catch(e){status(e.message);}};
$('selection-restore').onclick=()=>{remember();delete selectionEdits[M.id];render();};
