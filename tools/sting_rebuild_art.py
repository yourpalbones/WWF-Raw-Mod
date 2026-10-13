"""Authored Crow makeup and shoulder-length hair on native donor anatomy.

Faces are registered to specific drawings. Eyes, cheek lines, nose and mouth
are recorded separately; they are not inferred from a costume centroid.
"""
import json,hashlib
from functools import lru_cache
from pathlib import Path
from scott_frame_catalog import raster
from build_bret_gear import planar
from build_scott_hall_gear import components

SKIN={7,9,10,11,12,15}
SCORPION=['1100000000011','1010000000101','0110011100110','0011010101100',
          '0001111111000','0110011100110','1001011101001','0110011100110',
          '1001011101001','0110011100110','1001001001001','0000010100000',
          '0000010100000','0000001100000','0000000100000']

@lru_cache(maxsize=1)
def atlas():
    return json.loads((Path(__file__).resolve().parents[1]/'data/sting-rebuild-heads.json').read_text())

def author(frame):
    # Include transparent cells. New hair may replace the donor's head outline.
    masks={}
    changes={ref['field']:ref['pixels'].copy() for part in frame['parts']for ref in part['refs']}
    points,mapping=raster(frame)
    coverage={};covering={}
    for part in reversed(frame['parts']):
        size=part['size']
        for y in range(size):
            for x in range(size):
                sx=size-1-x if part['hflip']else x;sy=size-1-y if part['vflip']else y
                ref=part['refs'][(sy//8)*(size//8)+sx//8]
                q=(part['x']+x,part['y']+y);cell=(ref,sy%8*8+sx%8)
                coverage[q]=cell;covering.setdefault(q,[]).append(cell)
    def put(q,v,add=False):
        cell=mapping.get(q) or (coverage.get(q)if add else None)
        if cell:
            ref,k=cell;changes[ref['field']][k]=v
    # Native sleeveless body, trousers, boots and gloves become black. Skin
    # stays in its own shades, with face-white and scorpion-gray slots reserved.
    for part in frame['parts']:
        for ref in part['refs']:
            changes[ref['field']]=[({2:2,3:3,4:2,5:3,6:3,8:2,13:2,14:3}.get(v,v))for v in ref['pixels']]
            # The 426 wrestler-specific lower pieces contain legs, not heads.
            # Exact shared tile hashes alone cannot establish facial anatomy.
            mask={}if frame['kind']=='secondary'and frame['index']<426 else atlas().get('tile_masks',{}).get(hashlib.sha256(planar(ref['pixels'])).hexdigest(),{});masks[ref['field']]=mask
            for k,v in mask.items():changes[ref['field']][int(k)]=v
    if frame['kind']in {'primary','secondary'}:
        # Native hair is drawn with black plus the same brown shades as skin.
        # Shirt/glove pixels are separate colors, so hair-connected islands can
        # be located without a screen-relative head box or an arm centroid.
        candidates=[]
        for group in components(points,SKIN|{1}):
            black=sum(points[q]==1 for q in group)
            l=min(x for x,y in group);r=max(x for x,y in group)
            t=min(y for x,y in group);b=max(y for x,y in group)
            if black>=10 and len(group)>=45 and r-l<=28 and b-t<=32:
                candidates.append((black,group))
        if candidates:
            _,head=max(candidates,key=lambda e:e[0])
            for q in head:
                ref,k=mapping[q]
                if str(k)in masks.get(ref['field'],{}):continue
                v=points[q]
                neighbors=sum(points.get((q[0]+dx,q[1]+dy))==1 for dx,dy in[(-1,-1),(0,-1),(1,-1),(-1,0),(1,0),(-1,1),(0,1),(1,1)])
                if v in {9,10,12} and neighbors>=3:put(q,14 if v==12 else 1)
                elif v in {7,11,15} and neighbors>=4:put(q,14)
    identifier=str(frame['index'])if frame['kind']=='primary'else 'secondary:'+str(frame['index'])
    entry=atlas()['heads'].get(identifier)
    if entry:
        seed=atlas()['templates'][entry['template']]
        sx,sy,dx,dy=entry['transform'];world=lambda x,y:(sx*x+dx,sy*y+dy)
        replacement=seed.get('replace_head',False)
        if not replacement:
            l,t,r,b=seed['box']
            for y in range(t,b+1):
                for x in range(l,r+1):
                    q=world(x,y)
                    colors={1,9,10,12}if seed.get('hair_only')else SKIN|{1}
                    if q in points and points[q] in colors:
                        put(q,1 if points[q]in {1,9,10}else 14)
            for key,value in [('face',5),('face_shadow',13),('eyes',1),('cheeks',1),('mouth',1),('nose',13)]:
                for x,y in seed.get(key,[]):
                    q=world(x,y)
                    if points.get(q)in SKIN|{1}:put(q,value)
            for x,y,value in seed.get('hair',[]):put(world(x,y),value,True)
        # Authored revision heads replace the complete face plane, including
        # native hair/shirt colors inside the reviewed head silhouette. Gating
        # the eye sockets on skin shades dropped features in the previous pass.
        if replacement:
            # A transparent authored cell must erase every overlapping OBJ.
            # Clearing only the originally visible tile would expose another
            # donor head pixel underneath it. Nonzero paint belongs to the
            # foremost covering OBJ, even where that OBJ was transparent.
            for x,y,value in seed.get('paint',[]):
                if value==0:
                    for ref,k in covering.get(world(x,y),[]):changes[ref['field']][k]=0
            for x,y,value in seed.get('paint',[]):
                if value and (cell:=coverage.get(world(x,y))):
                    ref,k=cell;changes[ref['field']][k]=value
        else:
            for x,y,value in seed.get('paint',[]):put(world(x,y),value,True)
        # A raised hand must keep its foreground pixels. Known occluded head
        # drawings receive a dedicated mask instead of an entire frontal face.
        for x,y in seed.get('occlusion',[]):
            q=world(x,y)
            if replacement:
                # Restore native transparency above a foreground hand too;
                # restoring only its visible tile could leave new face paint
                # on a higher OBJ that originally contained no opaque pixel.
                for ref,k in covering.get(q,[]):changes[ref['field']][k]=ref['pixels'][k]
            elif q in mapping:
                ref,k=mapping[q];changes[ref['field']][k]=points[q]
    # These native drawings have a reviewed front torso. Anchor the scorpion
    # to its actual shirt island, independently of head translation/tilt.
    front_torsos={*range(1,9),16,17,18,19,20,24,33,34,35,36,37,38,47,48}
    if frame['kind']=='primary'and frame['index']in front_torsos:
        garments=components(points,{2,3,6})
        if garments:
            cloth=max(garments,key=len)
            l=min(x for x,y in cloth);r=max(x for x,y in cloth)
            t=min(y for x,y in cloth);b=max(y for x,y in cloth)
            if len(cloth)>=45 and r-l>=7 and b-t>=7:
                sideways=frame['index']in {18,19,20}and r-l>b-t+4
                width,height=(15,13)if sideways else(13,15)
                ox=(l+r-width+1)//2;oy=(t+b-height+1)//2
                for y,row in enumerate(SCORPION):
                    for x,v in enumerate(row):
                        q=(ox+y,oy+12-x)if sideways else(ox+x,oy+y)
                        if v=='1'and q in cloth:put(q,8 if(x+y)%3 else 6)
    # Shared submission bodies use a low neckline. Sting's shirt is filled in
    # these explicitly reviewed torso regions, without changing gripping arms.
    if frame['kind']=='primary':
        torso={623:[-4,-28,6,-14],732:[-13,-61,-2,-48],737:[-15,-39,-4,-28],738:[-1,-22,5,-12]}.get(frame['index'])
    else:
        torso={617:[0,-65,6,-52],618:[0,-65,6,-52],619:[-6,-50,1,-39],620:[-6,-48,3,-36],621:[-6,-40,3,-28],622:[1,-53,6,-42],628:[-6,-40,3,-28]}.get(frame['index'])
    if torso:
        l,t,r,b=torso
        for q,v in points.items():
            if l<=q[0]<=r and t<=q[1]<=b and v in SKIN:put(q,2 if v in {7,9,10,12}else 3)
        if frame['kind']=='primary'and frame['index']==737:
            glyph=['11000011','01100110','00111100','11011011','00111100','11011011','00011000','00001100','00000100']
            for y,row in enumerate(glyph):
                for x,v in enumerate(row):
                    if v=='1':put((-14+x,-39+y),8 if (x+y)%3 else 6)
        if frame['kind']=='secondary'and frame['index']==622:
            glyph=['11011','01110','10101','01110','00100','00010','00001']
            for y,row in enumerate(glyph):
                for x,v in enumerate(row):
                    if v=='1':put((1+x,-51+y),8 if (x+y)%3 else 6)
        if frame['kind']=='primary'and frame['index']==623:
            glyph=['110000011','101000101','011111110','001010100','110111011','001111100','110111011','001010100','000111000','000010100','000001100','000000100']
            for y,row in enumerate(glyph):
                for x,v in enumerate(row):
                    if v=='1':put((-3+x,-27+y),8 if (x+y)%3 else 6)
    if frame['kind']=='primary'and frame['index']==733:
        # This submission piece contains gripping hands, not a torso/head.
        # Keep the reference's black gloves through the crossing-leg stage.
        for q,v in points.items():
            if v in SKIN:put(q,2 if v in {7,9,10,12}else 3)
    if frame['kind']=='primary'and frame['index']==738:
        # Seated Deathlock: the bent arm occupies the left foreground. The
        # exposed flank/waist to its right is torso, and needs the full shirt.
        # The old short chest rectangle left a strip of Bret's bare abdomen.
        for y in range(-19,-4):
            left,right=(6,8)if y>=-19 and y<=-18 else(6,9)if y<=-12 else(0,7)if y<=-8 else(-1,7)
            for x in range(left,right+1):
                v=points.get((x,y))
                if v in SKIN:put((x,y),2 if v in {7,9,10,12}else 3)
    return changes
