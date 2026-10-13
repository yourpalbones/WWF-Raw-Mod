"""Author Crow makeup around native face shading and reviewed Kid landmarks.

The front face borrows Kid's actual facial anatomy, while the body's native
movement and outfit remain Undertaker-based. Other views retain their own native
face planes. No flat white polygon or synthetic black eye rectangle is used.
"""
import argparse,json
from pathlib import Path
from scott_frame_catalog import catalog,raster

SHADE={7:8,9:13,10:13,11:5,12:8,15:5}

def build(rom,taker_wram,kid_wram,seeds):
    native={(f['kind'],f['index']):raster(f)[0]for f in catalog(rom,taker_wram,2)}
    kid=raster(next(f for f in catalog(rom,kid_wram,9)if f['kind']=='primary'and f['index']==1))[0]
    for key,seed in seeds.items():
        face={tuple(q)for q in seed.get('face',[])}
        if not face:continue
        points=native[seed.get('kind','primary'),seed['piece']]
        if key=='profile':
            face={(x+2,y)for x,y in face};seed['box'][2]=10
        paint={q:SHADE.get(points.get(q),1 if points.get(q)==1 else 13)for q in face}
        # Native eye shapes are retained; the makeup adds a single upper edge
        # and a narrow one-pixel trail, with nose/lip shading remaining visible.
        eyes=seed.get('eyes',[])
        if eyes:
            eye_y=min(y for x,y in eyes)
            for x,y in eyes:
                if y==eye_y:paint[x,y]=1
            for x in sorted({x for x,y in eyes if y==eye_y})[::2]:
                if(x,eye_y+1)in face:paint[x,eye_y+1]=1
        for x,y in seed.get('nose',[]):
            paint[x,y]=5
            if(x-1,y)in face:paint[x-1,y]=13
        for x,y in seed.get('mouth',[]):paint[x,y]=1
        if key=='profile':
            for q in [(8,-35),(9,-35),(8,-36),(8,-34),(8,-32),(9,-32)]:paint[q]=1
            paint[10,-34]=5;paint[9,-34]=13
        if key=='profile-walking':
            for q in [(6,-34),(7,-34),(6,-35),(6,-33),(6,-31),(7,-31)]:paint[q]=1
            paint[8,-33]=5;paint[7,-33]=13
        if key in ['front','deathlock-entry-stand']:
            # User-marked eyes/nose/lips from Kid's native front face, shifted
            # into the donor's head. Shading is read from the supplied ROM.
            paint={}
            for y in range(-38,-28):
                for x in range(-1,6):
                    if(x,y)in kid:paint[x-2,y]=SHADE.get(kid[x,y],1 if kid[x,y]==1 else 13)
            for q in [(-1,-35),(0,-35),(2,-35),(-1,-36),(2,-36),(-1,-34),(2,-34)]:paint[q]=1
            paint[1,-33]=5;paint[0,-33]=13
            for q in [(0,-31),(1,-31),(2,-31)]:paint[q]=1
            seed['landmarks']={'eyes':[[-1,-35],[0,-35],[2,-35]],'nose':[1,-33],'mouth':[[1,-31]],'jaw':[1,-29]}
            seed['face_donor']='1-2-3 Kid primary 1, x shift -2; user-marked native landmarks'
        # Tapered dark locks with sparse charcoal highlights replace the old
        # straight gray strips. Paint coverage remains inside existing OBJs.
        bottom=max(y for x,y in face)
        for x,y,value in seed.get('hair',[]):
            if y<=bottom+5 and not(y>=bottom+4 and(x+y)%2):paint[x,y]=14 if(x+y)%5==0 else 1
        seed['paint']=[[x,y,v]for(x,y),v in sorted(paint.items(),key=lambda e:(e[0][1],e[0][0]))]
        seed['reference']='Magazine and full-body Crow reference; native anatomy and grayscale face shading'
        for field in ['face','face_shadow','eyes','cheeks','mouth','nose','hair']:seed[field]=[]
    return seeds

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['rom','taker_wram','kid_wram','seeds','output']:p.add_argument(name,type=Path)
    a=p.parse_args();a.output.write_text(json.dumps(build(a.rom.read_bytes(),a.taker_wram.read_bytes(),a.kid_wram.read_bytes(),json.loads(a.seeds.read_text())),indent=2)+'\n')
