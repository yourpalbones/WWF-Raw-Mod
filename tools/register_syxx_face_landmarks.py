"""Carry user-marked facial landmarks into repeated native face drawings.

Feature and skin masks must match, including reflected poses; skin shading
may vary within the recorded threshold. Other face drawings need their own
anchors; their beard is deliberately left unpainted.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

from native_gear_art import head_region, SKIN
from scott_frame_catalog import catalog, raster


def register(rom, wram):
    frames = catalog(rom, wram, 9)
    seeds=json.loads((Path(__file__).resolve().parents[1]/'data/syxx-face-seeds.json').read_text())['templates']
    templates={}
    for key,seed in seeds.items():
        original,_=raster(frames[seed['primary_piece']])
        l,t,r,b=seed['source_box']
        templates[key]={q:v for q,v in original.items()if l<=q[0]<=r and t<=q[1]<=b}
    heads = {}
    for frame in frames:
        if frame["kind"] != "primary":
            continue
        head, _ = head_region(frame, raster(frame)[0], True)
        if not head:
            continue
        matches = []
        for key,template in templates.items():
            for sx, sy in [(1, 1), (-1, 1), (1, -1), (-1, -1)]:
                votes = Counter((x - sx * tx, y - sy * ty)
                                for (tx, ty), v in template.items()
                                for (x, y), value in head.items() if value == v)
                for (dx, dy), _ in votes.most_common(2):
                    exact=sum(head.get((sx*x+dx,sy*y+dy))==v for (x,y),v in template.items())
                    # Native artists sometimes shade the same face differently.
                    # All eye/hair/non-skin values and every skin-mask pixel
                    # must still agree; allow only skin-shade substitutions.
                    shape=all((head.get((sx*x+dx,sy*y+dy))in SKIN if v in SKIN
                               else head.get((sx*x+dx,sy*y+dy))==v)
                              for (x,y),v in template.items())
                    if shape and exact>=len(template)*.75:
                        matches.append((exact,len(template),key,[sx, sy, dx, dy]))
        if matches:
            # A manually authored source uses its own mask. Repeated face
            # drawings elsewhere use one deterministic canonical template.
            direct=[m for m in matches if int(m[2])==frame['index']and m[3]==[1,1,0,0]]
            if direct:matches=direct
            matches.sort(key=lambda m:(-m[0],-m[1],int(m[2]),m[3]))
            exact,size,key,transform=matches[0]
            if sum(m[:3]==(exact,size,key) for m in matches)>1:continue
            heads[str(frame["index"])] = {"template": int(key),
                                         "transform": transform,
                                         "exact_pixels": exact,
                                         "template_pixels": size,
                                         "matching_skin_mask_and_features": True}
    return {"version": 1, "selector": 9,
            "method": "Every non-skin feature and every skin-mask pixel match under translation/reflection; at least 75 percent of original shades match exactly. No crown-relative beard placement.",
            "templates": seeds,
            "heads": heads}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rom", type=Path)
    parser.add_argument("wram", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = register(args.rom.read_bytes(), args.wram.read_bytes())
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print("Registered native facial landmarks for", len(result["heads"]), "primary pieces")
