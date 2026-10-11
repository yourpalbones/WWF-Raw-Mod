"""Inventory address-only native audio banks and per-song voice streams."""
import argparse,hashlib,json
from pathlib import Path
from build_bret_gear import ORIGINAL_HASH

def inventory(data):
 if hashlib.sha256(data).hexdigest()!=ORIGINAL_HASH:raise ValueError('Requires the verified original USA ROM')
 bank_count=data[0x11900]+1;song_count=data[0x11901];banks=[]
 for bank in range(bank_count):
  address=int.from_bytes(data[0x11903+bank*3:0x11906+bank*3],'little')&0x3fffff;count=int.from_bytes(data[address:address+2],'little');records=[]
  for index in range(count):
   at=address+2+index*7;r=data[at:at+7];length=int.from_bytes(r[:2],'little');source=int.from_bytes(r[2:5],'little')&0x3fffff;destination=int.from_bytes(r[5:],'little')
   if length and (source+length>len(data) or destination+length>65536):raise ValueError('Audio upload exceeds source or SPC RAM')
   records.append({'record_offset':at,'length':length,'source_offset':source,'spc_destination':destination})
  banks.append({'bank_id':bank,'directory_offset':address,'upload_count':count,'records':records})
 song_bank_table=0x11903+bank_count*3;songs=[]
 for song in range(song_count):
  bank=data[song_bank_table+song];records=banks[bank]['records'];pointer_record=next(r for r in records if r['spc_destination']==0x24e0+song*2 and r['length']==2);header_pointer=int.from_bytes(data[pointer_record['source_offset']:pointer_record['source_offset']+2],'little');header=next(r for r in records if r['spc_destination']==header_pointer);voices=data[header['source_offset']];assert voices<=20;streams=[]
  for voice in range(voices):
   address=int.from_bytes(data[header['source_offset']+1+voice*2:header['source_offset']+3+voice*2],'little');stream=next(r for r in records if r['spc_destination']==address);streams.append({'voice':voice,**stream})
  songs.append({'song_id':song,'bank_id':bank,'voice_count':voices,'header':header,'streams':streams})
 return {'original_sha256':ORIGINAL_HASH,'bootstrap_offset':0x10000,'driver_offset':0x100e0,'driver_spc_destination':0x700,'driver_length':0x17e0,'driver_signature':'SNDDRVR / REN AND STIMPY','bank_directory':0x11903,'song_bank_table':song_bank_table,'spc_song_pointer_table':0x24e0,'banks':banks,'songs':songs,'notes':'Address inventory; not a complete decoder or arbitrary-audio importer'}
if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('rom',type=Path);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();result=inventory(args.rom.read_bytes());args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2)+'\n');print(f"Mapped {len(result['banks'])} native audio banks and {len(result['songs'])} song headers")
