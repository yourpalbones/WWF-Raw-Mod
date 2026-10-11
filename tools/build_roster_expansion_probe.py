"""Build a menu-only 13th profile probe. This is NOT a playable roster expansion."""
import argparse,hashlib,json
from pathlib import Path
from build_bret_gear import ORIGINAL_HASH
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('rom',type=Path);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
original=args.rom.read_bytes();assert hashlib.sha256(original).hexdigest()==ORIGINAL_HASH
b=bytearray(original+b'\xff'*0x100000);base=0x3b8000;b[base:base+12*45]=original[0x2efaf5:0x2efd11];b[base+12*45:base+13*45]=original[0x2efaf5+45:0x2efaf5+90];changes=[]
def write(address,expected,new):
 assert b[address:address+len(expected)]==expected,hex(address);b[address:address+len(new)]=new;changes.append({'offset':hex(address),'before':expected.hex(),'after':new.hex()})
helper=bytes.fromhex('a2 2d 00 22 5f ff ad 18 69 f5 fa aa f4 fa ae ab ab 60');at=original.index(helper);write(at+9,bytes.fromhex('f5 fa'),bytes.fromhex('00 80'));write(at+13,bytes.fromhex('fa ae'),bytes.fromhex('80 fb'))
for field in [40,41,42,43]:
 old=(0x2efaf5+field)|0x800000;pattern=b'\xbf'+old.to_bytes(3,'little');at=original.index(pattern,0x2afebc,0x2aff20);write(at+1,old.to_bytes(3,'little'),((base+field)|0xc00000).to_bytes(3,'little'))
write(0x19d43f,b'\x0c',b'\x0d');back=original.index(bytes.fromhex('a9 0b 00'),0x19d420,0x19d440);write(back+1,b'\x0b',b'\x0c')
checksum=sum(b)&65535;b[0xffdc:0xffe0]=(checksum^65535).to_bytes(2,'little')+checksum.to_bytes(2,'little');(args.output/'13-slot-menu-probe.sfc').write_bytes(b);(args.output/'patch.json').write_text(json.dumps({'profile_table':hex(base),'record_count':13,'probe_scope':'menu-only duplicated Bret profile; not a playable expanded roster','changes':changes},indent=2)+'\n');print('Built local menu-only 13th profile probe; not for gameplay or editor import')
