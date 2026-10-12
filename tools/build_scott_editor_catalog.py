"""Add Scott's complete known frame pieces and captured native full-body poses.

Only address/position metadata is published. Pixels are decoded from the local ROM.
"""
import argparse,json
from pathlib import Path
from scott_frame_catalog import catalog
from decode_sprite_tile import decode_sprite_tile
from extract_oam import objects
p=argparse.ArgumentParser(description=__doc__);p.add_argument('original',type=Path);p.add_argument('edited',type=Path);p.add_argument('wram',type=Path);p.add_argument('report',type=Path);p.add_argument('captures',type=Path);p.add_argument('seed',type=Path);p.add_argument('--extra-captures',type=Path,action='append',default=[]);p.add_argument('--source-shift',action='append',default=[]);p.add_argument('--selector',type=int,default=5);p.add_argument('--destination',default='scott-layouts.js');p.add_argument('--window-name',default='RAW_SCOTT_MANIFEST');args=p.parse_args();repo=Path(__file__).resolve().parents[1];original=args.original.read_bytes();edited=args.edited.read_bytes();frames=catalog(original,args.wram.read_bytes(),args.selector);private={r['offset']:r for r in json.loads(args.report.read_text())['tile_sources']};sources={};pieces=[];captured=[]
for frame in frames:
 parts=[]
 for part in frame['parts']:
  keys=[]
  for ref in part['refs']:
   key=f"piece:{frame['kind']}:{frame['index']}:{ref['relative']}";keys.append(key);sources[key]={'offset':ref['source'],'length':ref['length'],'compressed':ref['compressed'],'frame_kind':frame['kind'],'frame_index':frame['index'],'field_relative':ref['relative']}
  parts.append({k:part[k]for k in['x','y','size','hflip','vflip']}|{'palette':0,'tiles':keys})
 left=min((part['x']for part in parts),default=0);top=min((part['y']for part in parts),default=0)
 for part in parts:part['x']-=left;part['y']-=top
 width=max((part['x']+part['size']for part in parts),default=1);height=max((part['y']+part['size']for part in parts),default=1)
 pieces.append({'label':f"{'Upper body'if frame['kind']=='primary'else'Lower body'} piece {frame['index']:03d}",'category':('common-'+frame['kind'])if frame.get('common')else frame['kind'],'capture':f"directory/{frame['kind']}/{frame['index']}",'width':width,'height':height,'parts':parts})

def source_offset(address):return address&0x3fffff if address>=0x800000 else address
shifts={Path(k).resolve():int(v)for k,v in(s.rsplit(':',1)for s in args.source_shift)}
cache={};trace_rows={};trace_cursors={};decoded={}
def trace(root,limit=None):
 if root not in trace_rows:trace_rows[root]=[json.loads(line)for line in(root/'tile_calls.jsonl').read_text().splitlines()];trace_cursors[root]=0
 rows=trace_rows[root];i=trace_cursors[root]
 while i<len(rows)and(limit is None or rows[i]['frame']<=limit):
  e=rows[i];offset=source_offset(e['source']);shift=next((v for p,v in shifts.items()if root.resolve().is_relative_to(p)),0);offset+=shift if 0x570000<=offset<0x5f0000 else 0;compressed=bool(e['compressed']);key=(offset,compressed)
  if key not in decoded:decoded[key]=decode_sprite_tile(edited,offset)if compressed else(edited[offset:offset+32],32)
  data,length=decoded[key];cache[(e['destination'],data)]=(offset,compressed,length);i+=1
 trace_cursors[root]=i
trace(args.seed)
folders=[folder for root in[args.captures,*args.extra_captures]for folder in sorted(root.iterdir())]
for folder in folders:
 if not folder.is_dir()or not(folder/'tile_calls.jsonl').exists():continue
 snapshots=sorted(folder.glob('frame-*.png'))
 for file in snapshots:
  number=int(file.stem.split('-')[1])
  if number<24:continue
  trace(folder,number);prefix=file.with_suffix('');read=lambda n:Path(str(prefix)+'-'+n+'.bin').read_bytes();vram=read('vram');palette=read('cgram');parts=[]
  for record,image in objects(vram,read('oam'),palette,read('registers')[0x2101]):
   if record['palette']!=0 or not 0<=record['y']<190 or not -20<=record['x']<256 or not image.getbbox():continue
   keys=[]
   for ty in range(record['size']//8):
    for tx in range(record['size']//8):
     n=((record['tile']&0xf0)+ty*16+((record['tile']+tx)&15))&255;raw=vram[n*32:n*32+32]
     if not any(raw):keys.append(None);continue
     match=cache.get((0x7e2000+n*32,raw))
     if match is None:raise ValueError(('Unresolved native tile',folder.name,number,n))
     offset,compressed,length=match;key=f'capture:{offset}';keys.append(key)
     if offset in private:sources[key]={**private[offset],'private_packet_offset':offset}
     else:sources[key]={'offset':offset,'compressed':compressed,'length':length}
   parts.append(record|{'tiles':keys})
  if not parts:continue
  left=min(part['x']for part in parts);top=min(part['y']for part in parts)
  for part in parts:part['x']-=left;part['y']-=top
  action=int.from_bytes(read('wram')[0x6b4:0x6b6],'little');labels={0:'Standing',6:'Walking',120:'Punch',126:'Kick',150:'Tie-up',152:'Tie-up',156:'Receiving grapple',158:'Receiving grapple',600:'Outsider’s Edge',610:'Jackknife',608:'Top-rope finisher',566:'Mega Move',586:'Mega Move',558:'Mega Move',12:'Walking',70:'Downed',76:'Getting up',238:'Fallaway slam',240:'Taking fallaway slam',242:'Body slam',248:'Taking faceplant',250:'Belly-to-belly suplex',256:'Taking piledriver',206:'Atomic drop',208:'Taking atomic drop',210:'Back suplex',212:'Taking back suplex'};label=labels.get(action,('Running / ropes'if folder.name=='run-ropes'else'Grapple / reaction')+f' · state {action:03X}');pose={'label':label+f' · frame {number:03d}','category':'captured','capture':folder.name+'/'+file.stem,'width':max(p['x']+p['size']for p in parts),'height':max(p['y']+p['size']for p in parts),'parts':parts}
  if not any(old['parts']==parts for old in captured):captured.append(pose)
manifest={'version':1,'selector':str(args.selector),'signature_offset':0x4bf000,'signature':'SCOTT-HALL-GEAR1','primary_table':0x4bc000,'secondary_table':0x4bd000,'pointer_table':0x4b0000,'descriptor_bank':0x42,'private_tag':0xc000,'private_mask':0x3fff,'sources':sources,'poses':captured+pieces,'captured_poses':len(captured),'known_pieces':len(pieces),'coverage':'953 wrestler-specific entries and 767 structurally parsed common entries, plus native full-body captures. Exhaustive live gameplay coverage remains unverified.'}
from build_nwo_gear import CONFIGS
config=CONFIGS[args.selector];manifest.update({k:config[k]for k in['signature_offset','signature','primary_table','secondary_table']});manifest['pointer_table']=config['pointers'];manifest['descriptor_bank']=config['frames_start']>>16;manifest['private_compressed']=False;manifest['coverage']='Known wrestler-specific and parsed common frame pieces, plus captured native poses. Complete live coverage remains unverified.'
(repo/'editor'/args.destination).write_text('window.'+args.window_name+' = '+json.dumps(manifest,separators=(',',':'))+';\n');print('Added',len(captured),'captured full-body poses and',len(pieces),'known frame pieces;',len(sources),'address references')
