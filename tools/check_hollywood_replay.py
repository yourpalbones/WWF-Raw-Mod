"""Compare native original/converted replays made with identical controller inputs."""
import argparse,json
from pathlib import Path
from extract_oam import objects
p=argparse.ArgumentParser(description=__doc__);p.add_argument('original',type=Path);p.add_argument('converted',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[]
for path in sorted(a.converted.glob('*-wram.bin')):
 old=(a.original/path.name).read_bytes();new=path.read_bytes()
 # Documented actor control/position/action state. Renderer scratch/cache lives
 # outside this range and legitimately changes when compressed art changes.
 assert old[0x500:0xe00]==new[0x500:0xe00],path.name
 prefix=path.name[:-9]
 def other_objects(directory):
  read=lambda name:(directory/(prefix+'-'+name+'.bin')).read_bytes()
  return [(o,im.tobytes())for o,im in objects(read('vram'),read('oam'),read('cgram'),read('registers')[0x2101])if o['palette']!=0 and o['y']<224]
 assert other_objects(a.original)==other_objects(a.converted),path.name
 rows.append(path.name)
assert rows,'No snapshots checked'
r={'snapshots':len(rows),'player_state_0500_to_0dff_identical_every_snapshot':True,'all_other_visible_OBJ_records_and_colors_identical_every_snapshot':True,'note':'Same-input native replay; not proof of all match modes or unobserved moves.'};a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
