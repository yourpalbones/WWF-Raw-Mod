"""Keep address-only captured previews for previously published native gear ROMs."""
import json,subprocess
from pathlib import Path
repo=Path(__file__).resolve().parents[1];result={}
for name in ['scott','nash','syxx']:
 text=subprocess.check_output(['git','show','29a97c9:editor/'+name+'-layouts.js'],cwd=repo,text=True);m=json.loads(text[text.index('=')+1:].rstrip(';\n '));poses=[p for p in m['poses']if p['category']=='captured'];keys={k for p in poses for part in p['parts']for k in part['tiles']if k is not None};result[m['selector']]={'signature':m['signature'],'poses':poses,'sources':{k:m['sources'][k]for k in keys},'private_compressed':m['private_compressed']}
(repo/'editor/legacy-gear-layouts.js').write_text('window.RAW_LEGACY_GEAR_MANIFESTS = '+json.dumps(result,separators=(',',':'))+';\n');print('Kept v0.9 captured previews for all three wrestlers')
