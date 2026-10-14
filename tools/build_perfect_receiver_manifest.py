"""Bundle receiving geometry, source addresses and authored hooks, never pixels."""
import json
from pathlib import Path
from build_perfect_receivers import SLOTS,LAYOUT,worker_hook,lookup_hook,sequence_hook

root=Path(__file__).resolve().parents[1]
recipes=json.loads((root/'data/perfect-receivers.json').read_text())
recipes['slots']={str(k):v for k,v in SLOTS.items()}
recipes['layout']=LAYOUT
recipes.pop('raw_royal_map',None)
recipes['programs']=[[0x70f000,0x71eb00,list(worker_hook())],
                     [0x70f200,0x71ec00,list(lookup_hook())],
                     [0x70f400,0x71ed00,list(sequence_hook())]]
(root/'editor/perfect-receiver-layouts.js').write_text('window.RAW_PERFECT_RECEIVERS='+json.dumps(recipes,separators=(',',':'))+';\n')
print('Wrote receiving recipes and hooks; no ROM pixels included.')
