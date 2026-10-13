"""Bundle receiving geometry, source addresses and authored hooks, never pixels."""
import json
from pathlib import Path
from build_perfect_receivers import RAW_ROYAL,worker_hook,lookup_hook,sequence_hook

root=Path(__file__).resolve().parents[1]
recipes=json.loads((root/'data/perfect-receivers.json').read_text())
recipes['raw_royal_map']=RAW_ROYAL
recipes['programs']=[[0x70f000,0x71eb00,list(worker_hook())],
                     [0x70f200,0x71ec00,list(lookup_hook())],
                     [0x70f400,0x71ed00,list(sequence_hook())]]
(root/'editor/perfect-receiver-layouts.js').write_text('window.RAW_PERFECT_RECEIVERS='+json.dumps(recipes,separators=(',',':'))+';\n')
print('Wrote receiving recipes and hooks; no ROM pixels included.')
