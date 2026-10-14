"""Build the separate editor from a pinned, reviewed Claude snapshot plus our adapter."""
import hashlib,json,subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[1];config=json.loads((root/'editor-v01/source.json').read_text())
base=subprocess.run(['git','show',config['commit']+':editor/gear-workshop.html'],cwd=root,check=True,capture_output=True).stdout
if hashlib.sha256(base).hexdigest()!=config['html_sha256']:raise SystemExit('Pinned editor source hash mismatch')
text=base.decode().replace('WWF Raw · Character editor · v0.16.1','WWF Raw · Character editor · Roster 16 preview');start=text.index('function customMusicRecords(){');end=text.index('function stopMusicPreview',start);part=text[start:end]
for old,new in [('address=MUSIC.base+Number(id)*MUSIC.stride','address=v01MusicAddress(Number(id))'),('source>>16|192','v01MusicCPU(source)>>>16'),('address>>16|192','v01MusicCPU(address)>>>16')]:
 if part.count(old)!=1:raise SystemExit('Music source changed; review required: '+old)
 part=part.replace(old,new)
text=text[:start]+part+text[end:];adapter=(root/'editor-v01/roster16.js').read_text().replace('</script','<\\/script')
if text.count('</body>')!=1:raise SystemExit('Unexpected base editor structure')
text=text.replace('</body>','<script>\n'+adapter+'\n</script>\n</body>');(root/'editor-v01/gear-workshop.html').write_text(text);print('Built the ROM-free roster-16 editor from',config['commit'])
