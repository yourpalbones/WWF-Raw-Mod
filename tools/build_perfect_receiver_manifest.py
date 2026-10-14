"""Bundle receiving geometry, source addresses and authored hooks, never pixels."""
import json
from pathlib import Path
from build_perfect_receivers import SLOTS,LAYOUT,OWN_NATIVE_STEPS,worker_hook,lookup_hook,sequence_hook

root=Path(__file__).resolve().parents[1]
recipes=json.loads((root/'data/perfect-receivers.json').read_text())
recipes['slots']={str(k):v for k,v in SLOTS.items()}
recipes['layout']=LAYOUT
recipes['own_native_steps']=OWN_NATIVE_STEPS
# Each step's chosen pose (the first storable candidate); alternatives stay in the plan file for review.
plan=json.loads((root/'data/receiver-profile-plan.json').read_text())['slots']
pick=lambda p:{'donor':p['donor'],'steps':[{k:c[0][k] for k in ('profile','hflip','vflip','dx','dy')} for c in p['steps']]}
recipes['own_profiles']={slot:{**(pick(p) if 'steps' in p else {}),**({'gear':pick(p['gear'])} if 'gear' in p else {})}
                         for slot,p in plan.items()}
# Royal's drawings rebuilt from each own-art wrestler's pixels (tools/plan_receiver_reskin.py); piece indices and
# offsets only.
recipes['reskin']=json.loads((root/'data/receiver-reskin-plan.json').read_text())['slots']
recipes.pop('raw_royal_map',None)
recipes['programs']=[[0x70f000,0x71eb00,list(worker_hook())],
                     [0x70f200,0x71ec00,list(lookup_hook())],
                     [0x70f400,0x71ed00,list(sequence_hook())]]
(root/'editor/perfect-receiver-layouts.js').write_text('window.RAW_PERFECT_RECEIVERS='+json.dumps(recipes,separators=(',',':'))+';\n')
print('Wrote receiving recipes and hooks; no ROM pixels included.')
