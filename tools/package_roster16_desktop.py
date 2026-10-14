"""Package the ROM-free roster-16 editor using the verified official Windows runtime."""
import hashlib,json,shutil,zipfile
from pathlib import Path
root=Path(__file__).resolve().parents[1];runtime=root/'outputs/desktop-runtime';archive=runtime/'electron-v44.7.0-win32-x64.zip';checks={n.lstrip('*'):h for h,n in (line.split()for line in (runtime/'SHASUMS256.txt').read_text().splitlines())}
if hashlib.sha256(archive.read_bytes()).hexdigest()!=checks[archive.name]:raise SystemExit('Official Electron checksum mismatch')
out=root/'outputs/roster16';out.mkdir(parents=True,exist_ok=True);target=out/'WrestleEdit-Roster16-Windows-x64.zip';prefix='WrestleEdit-Roster16/'
with zipfile.ZipFile(archive) as src,zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as dst:
 for info in src.infolist():
  name=prefix+('WrestleEdit.exe' if info.filename=='electron.exe' else info.filename)
  if info.is_dir():dst.writestr(name,b'');continue
  with src.open(info) as reader,dst.open(name,'w') as writer:shutil.copyfileobj(reader,writer,1024*1024)
 dst.write(root/'desktop/main.js',prefix+'resources/app/main.js')
 dst.writestr(prefix+'resources/app/package.json',json.dumps({'name':'wrestleedit-roster16','productName':'WrestleEdit Roster 16 Preview','version':'0.17.0','private':True,'main':'main.js'}))
 dst.write(root/'editor-v01/gear-workshop.html',prefix+'resources/app/gear-workshop.html')
 dst.writestr(prefix+'START HERE.txt','''WrestleEdit Roster 16 Preview — Windows 10/11 x64

1. Right-click this ZIP and choose Extract All.
2. Open the extracted WrestleEdit-Roster16 folder.
3. Double-click WrestleEdit.exe. Keep its supporting files together.
4. Click Load ROM and choose your original, edited, or prepared 16-wrestler Raw ROM.
5. Choose a wrestler. Edit sprites, portrait, small monitor photo, names, bio or theme.
6. Save a project to keep working. Save a playable ROM for your emulator.

This preview recognizes Mr. Perfect, Hogan, Big Boss Man and Ric Flair in the
prepared sixteen-slot build. It does not automatically add the three latest
workers to an arbitrary ROM. No ROM is included in this download.

Some imported move artwork and finishers are unfinished, including Flair's
Figure Four. This editor preview is not a completed v0.1 game release.

Source: https://github.com/yourpalbones/WWF-Raw-Mod/tree/codex/roster16-editor
''')
digest=hashlib.sha256(target.read_bytes()).hexdigest();target.with_suffix('.zip.sha256').write_text(digest+'  '+target.name+'\n');print(target);print('SHA-256',digest);print('bytes',target.stat().st_size)
