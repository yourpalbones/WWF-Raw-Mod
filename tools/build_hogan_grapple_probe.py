"""Source-Hogan body-slam/suplex artwork experiment, not verified complete art.

Retimes actual source throwing frames to Raw's native sequences. Placement and
all partner/ending frames need native review; unmatched actions remain standing.
"""
import argparse,json
from pathlib import Path
from PIL import Image
from build_hogan_motion_probe import ROOTS
from build_hogan_legdrop_probe import build_test

BINDINGS={0x4c08:157,0x4c38:157,
          **dict(zip((0x4c70,0x4c84,0x4c98,0x4cac,0x4cc0,0x4cd4,0x4ce2,0x4cf2,0x4cfc),(157,158,159,160,161,162,163,164,164))),
          **dict(zip((0x55ee,0x55fc,0x5610,0x5624,0x5638,0x564c,0x565c),(189,190,191,192,193,194,195))),
          0x47be:38,0x47d6:40,0x47e4:41,0x47f2:43}


def build(base,genesis,stock,portrait):
    old=dict(ROOTS)
    try:
        ROOTS.update(BINDINGS)
        out,report=build_test(base,genesis,stock,portrait)
        report.update(grapple_animation_experiment=True,grapple_pair_alignment_verified=False,
                      source_A_throw_implemented=False,warning='Source artwork is retimed; pair/ending art is incomplete and needs review.')
        return out,report
    finally:ROOTS.clear();ROOTS.update(old)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('base','genesis','stock','portrait'):p.add_argument(n,type=Path)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    out,report=build(a.base.read_bytes(),a.genesis.read_bytes(),a.stock.read_bytes(),Image.open(a.portrait))
    a.output.write_bytes(out);a.output.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items()if k!='poses'},indent=2))
