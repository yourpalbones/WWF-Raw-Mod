"""Check native face landmarks, untouched leg drawings and Deathlock shirt coverage."""
import argparse,json
from pathlib import Path
from scott_frame_catalog import catalog,raster
from publish_sting_head_study import decoded

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['before','after','wram']:p.add_argument(name,type=Path)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    before=a.before.read_bytes();after=a.after.read_bytes();frames=catalog(before,a.wram.read_bytes(),2)
    lower_changes=[]
    for f in frames:
        if f['kind']=='secondary'and f['index']<426:
            old=decoded(f,before);new=decoded(f,after);native=raster(f)[0]
            for q in set(old)|set(new):
                if old.get(q)!=new.get(q):
                    # v0.13 carried a white face-paint pixel in a shared black
                    # tile used by several leg drawings. Restore native black.
                    assert(old.get(q),new.get(q))==(5,1),(f['index'],q,old.get(q),new.get(q))
                    assert native[q]==1
                    lower_changes.append({'piece':f['index'],'point':list(q),'before':5,'after':1})
    f=next(f for f in frames if f['kind']=='primary'and f['index']==1);points=decoded(f,after)
    # Independently read the emitted descriptor/tiles at the accepted Kid face
    # landmarks, translated two pixels left into Sting's native head.
    assert all(points[q]==1 for q in [(-1,-35),(0,-35),(2,-35),(1,-31)])
    assert points[1,-33]==5 and points[0,-33]==13
    f=next(f for f in frames if f['kind']=='primary'and f['index']==738)
    old=decoded(f,before);new=decoded(f,after)
    assert old[9,-13]in {7,9,10,11,12,15}and new[9,-13]in {2,3}
    assert old[2,-9]in {7,9,10,11,12,15}and new[2,-9]in {2,3}
    assert old[-5,-18]==new[-5,-18]==7,'Foreground arm must remain bare'
    assert before[0x2cc5ba:0x2cc5da]==after[0x2cc5ba:0x2cc5da]
    report={'native_kid_eye_nose_lip_landmarks_verified':True,'eye_nose_lip_rows':[-35,-33,-31],
            'wrestler_specific_lower_body_drawings_checked':426,'unchanged_lower_drawings':426-len({x['piece']for x in lower_changes}),
            'stray_white_leg_pixels_corrected':lower_changes,'palette_unchanged':True,
            'deathlock_shirt_covers_flank_and_waist':True,'foreground_arm_preserved':True,
            'art_likeness_requires_visual_review':True}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n');print(report)
