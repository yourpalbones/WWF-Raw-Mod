"""Make a small browser-app download that can be distributed through GitHub."""
from pathlib import Path
import zipfile
repo=Path(__file__).resolve().parents[1]
output=repo/'downloads/WrestleEdit.zip'
with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
 z.write(repo/'editor/gear-workshop.html','WrestleEdit/WrestleEdit.html')
 z.writestr('WrestleEdit/START HERE.txt','WrestleEdit\r\n\r\n1. Extract ALL files from the downloaded ZIP.\r\n2. Open the WrestleEdit folder.\r\n3. Double-click WrestleEdit.html. It opens in your browser.\r\n4. Click Load ROM and select your original WWF Raw USA ROM.\r\n5. Choose a wrestler, then Sprites or Portrait & bio.\r\n6. Use Save & play to save your edited ROM.\r\n\r\nSave project before closing if you want to keep editing later.\r\nYour ROM stays on your computer. No internet is required after download.\r\nNo ROM is included. This package opens the browser editor, not an EXE.\r\n')
with zipfile.ZipFile(output) as z:
 assert z.testzip() is None
 assert z.read('WrestleEdit/WrestleEdit.html')==(repo/'editor/gear-workshop.html').read_bytes()
 assert not any(n.lower().endswith(('.sfc','.smc')) for n in z.namelist())
print(f'Created and verified {output.name}: {output.stat().st_size:,} bytes')
