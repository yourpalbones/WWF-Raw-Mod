"""Make a small browser-app download that can be distributed through GitHub."""
from pathlib import Path
import shutil
import zipfile
repo=Path(__file__).resolve().parents[1]
output=repo/'downloads/WrestleEdit.zip'
with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
 z.write(repo/'editor/gear-workshop.html','WrestleEdit/WrestleEdit.html')
 z.writestr('WrestleEdit/START HERE.txt','WrestleEdit\r\n\r\n1. Extract ALL files from the downloaded ZIP.\r\n2. Open the WrestleEdit folder.\r\n3. Double-click WrestleEdit.html. It opens in your browser.\r\n4. Click Load ROM and select your original or edited WWF Raw USA ROM.\r\n5. Choose a wrestler, then Sprites or Portrait & bio.\r\n   Profiles include the main portrait, small monitor photo, in-match name, name artwork existing themes and custom MIDI songs.\r\n   Saving the bio updates the name above the health bar too.\r\n   For Scott, Nash, Syxx or Sting: choose Sprites, then the reference gear button.\r\n   For Sting, choose Doink, then Rebuild Sting sprites.\r\n   Sting includes the Scorpion Deathlock and updated names.\r\n   Gear preserves existing edits; Sting creates an 8 MiB ROM for Snes9x.\r\n6. To add Mr. Perfect: use Add wrestler, load your USA SNES Royal Rumble ROM, then click Add Mr. Perfect.\r\n   One new slot is supported. Some poses still use adapted Raw artwork.\r\n7. Use Save & play to save your edited ROM.\r\n\r\nSave project before closing if you want to keep editing later.\r\nYour ROM stays on your computer. No internet is required after download.\r\nNo ROM is included. This package opens the browser editor, not an EXE.\r\n')
with zipfile.ZipFile(output) as z:
 assert z.testzip() is None
 assert z.read('WrestleEdit/WrestleEdit.html')==(repo/'editor/gear-workshop.html').read_bytes()
 assert not any(n.lower().endswith(('.sfc','.smc')) for n in z.namelist())
shutil.copyfile(output,repo/'downloads/WrestleEdit-v0.16.zip')
print(f'Created and verified {output.name}: {output.stat().st_size:,} bytes')
