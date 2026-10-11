"""Verify exported labels in native game WRAM, across all 12 stock selectors."""
import argparse,json,os,subprocess,sys
from pathlib import Path
from decode_graphics import decode_block
parser=argparse.ArgumentParser();parser.add_argument('core',type=Path);parser.add_argument('rom',type=Path);parser.add_argument('capture_root',type=Path);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
rom=args.rom.read_bytes();graphics,_=decode_block(rom,0x3a0000);results=[]
for id in range(12):
 out=args.output/str(id);frame=3300 if id==0 else (id-1)*300;state=args.capture_root/'roster-menu-cycle-settled'/f'frame-{frame:06d}.state' if frame else args.capture_root/'roster-selection-ready/frame-000300.state'
 command=[sys.executable,str(Path(__file__).with_name('run_headless.py')),str(args.core),str(args.rom),'--output',str(out),'--load-state',str(state),'--frames','950','--interval','950','--press','100:8','--press','300:3','--press','500:8']
 env={**os.environ,'WWF_TRACE_DIR':str(out.resolve())};subprocess.run(command,env=env,check=True,stdout=subprocess.DEVNULL)
 wram=(out/'frame-000950-wram.bin').read_bytes();assert int.from_bytes(wram[0xb74:0xb76],'little')==id*2
 indices=rom[0x1a4451+id*8:0x1a4459+id*8];expected=b''.join(graphics[tile*32:tile*32+32] for tile in indices)
 assert wram[0x5040:0x5140]==expected,f'Native label differs for slot {id}'
 events=[json.loads(line) for line in (out/'decodes.jsonl').read_text().splitlines()];assert any(event['source']&0x3fffff==0x3a0000 and event['length']==8192 for event in events)
 results.append({'selector':id,'actor_directory_value':id*2,'native_label_bytes_checked':256,'native_hud_block_bytes':8192})
(args.output/'verification.json').write_text(json.dumps({'native_game_labels_verified':12,'characters':results},indent=2)+'\n');print('PASS: all 12 exported health-bar labels match native game drawing buffers')
