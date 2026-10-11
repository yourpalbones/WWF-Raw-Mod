"""Build a portable Windows app from checksum-verified official Electron files."""
import argparse,hashlib,shutil,zipfile
from pathlib import Path
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--runtime-dir',type=Path,default=Path('outputs/desktop-runtime'));args=parser.parse_args()
repo=Path(__file__).resolve().parents[1];runtime=args.runtime_dir
archive=runtime/'electron-v44.7.0-win32-x64.zip'
checksums={name.lstrip('*'):digest for digest,name in (line.split() for line in (runtime/'SHASUMS256.txt').read_text().splitlines())}
assert hashlib.sha256(archive.read_bytes()).hexdigest()==checksums[archive.name], 'Official Electron checksum mismatch'
folder=repo/'outputs/desktop/WrestleEdit';folder.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(archive) as z:z.extractall(folder)
(folder/'electron.exe').rename(folder/'WrestleEdit.exe')
app=folder/'resources/app';app.mkdir(parents=True,exist_ok=True)
for name in ['main.js','package.json']:shutil.copyfile(repo/'desktop'/name,app/name)
shutil.copyfile(repo/'editor/gear-workshop.html',app/'gear-workshop.html')
(folder/'START HERE.txt').write_text('WrestleEdit for Windows 10/11 (64-bit)\n\n1. Extract ALL files from the ZIP.\n2. Open the extracted WrestleEdit folder.\n3. Double-click WrestleEdit.exe.\n4. Click Load ROM and select your original WWF Raw USA ROM.\n5. Choose a wrestler and edit Sprites or Portrait & bio.\n6. Under Save & play, save your playable ROM.\n\nKeep all supporting files in this folder. No installation needed.\nNo ROM is included. Your original ROM stays unchanged.\nSave your project before closing to continue editing later.\n\nThis is an unsigned preview build. Only open it if you trust the source.\nSource: https://github.com/yourpalbones/WWF-Raw-Mod\n')
output=repo/'outputs/desktop/WrestleEdit-Windows-x64.zip'
with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for p in sorted(folder.rglob('*')):
  if p.is_file():z.write(p,p.relative_to(folder.parent))
checksum=hashlib.sha256(output.read_bytes()).hexdigest();output.with_suffix('.zip.sha256').write_text(checksum+'  '+output.name+'\n');print(output);print(checksum)
