"""Crow Sting colors and attached native-size scorpion artwork for Doink's slot.

Head locations come from the original clown hair, not torso centroids. Pixels
remain in their original object silhouettes, with face paint isolated from skin.
"""
from scott_frame_catalog import raster
from functools import lru_cache
from pathlib import Path
import json
from build_scott_hall_gear import components

SCORPION = [
    '1100000000011',
    '1010000000101',
    '0110011100110',
    '0011010101100',
    '0001111111000',
    '0110011100110',
    '1001011101001',
    '0110011100110',
    '1001011101001',
    '0110011100110',
    '1001001001001',
    '0000010100000',
    '0000010100000',
    '0000001100000',
    '0000000100000',
]

@lru_cache(maxsize=1)
def common_heads():
    heads=json.loads((Path(__file__).resolve().parents[1]/'data/syxx-common-heads.json').read_text())['heads']
    # Reviewed against native Doink-slot full-body frames of the Sharpshooter.
    for index,bounds in {732:[0,-69,15,-55],737:[-20,-53,-5,-38],738:[-6,-33,7,-20]}.items():
        heads[str(index)]={'bounds':bounds}
    return heads

def decorate(frame):
    points, mapping = raster(frame)
    changes = {}
    def put(q, v):
        if q in mapping:
            ref, k = mapping[q]
            changes.setdefault(ref['field'], ref['pixels'].copy())[k] = v
    hair = {q for q, v in points.items() if v in {4, 14}}
    # Green is native Doink hair in upper-body pieces. Do not borrow this rule
    # for shared full-body poses, where green can belong to another body part.
    head = set()
    if frame['kind'] == 'primary' and not frame.get('common') and hair:
        groups = components({q:1 for q in hair}, {1})
        core = max(groups, key=len)
        l=min(x for x,y in core);r=max(x for x,y in core)
        t=min(y for x,y in core);b=max(y for x,y in core)
        if r-l <= 25 and b-t <= 25:
            head={q for q in points if l-2<=q[0]<=r+5 and t-1<=q[1]<=b+4}
    elif frame['kind']=='primary' and frame.get('common'):
        entry=common_heads().get(str(frame['index']))
        if entry:
            l,t,r,b=entry['bounds']
            head={q for q in points if l<=q[0]<=r and t<=q[1]<=b}
    front=any(points[q]==1 for q in head)
    def submission_face(q):
        x,y=q
        if frame['index']==732:
            return (-63<=y<=-58 and 9<=x<=14) or (-60<=y<=-56 and 7<=x<=12)
        if frame['index']==737:
            return -47<=y<=-40 and -17<=x<=-10
        if frame['index']==738:
            return -30<=y<=-21 and -6<=x<=-2
        return True
    for q,v in points.items():
        if q in head:
            if frame.get('common') and frame['index']==732 and q[0]<=5 and q[1]>=-60:
                continue # Shoulder under the bent head remains exposed skin.
            elif frame.get('common') and frame['index'] in {732,737,738} and not submission_face(q):
                put(q,4 if v in {1,9,10,12,4,6} else 14)
            elif frame.get('common') and v in {6,8}:put(q,4 if v==6 else 14)
            elif v in {4,14,2,3}:put(q,4 if v in {4,2} else 14)
            elif not front and v in {7,9,10,11,12,15}:put(q,4 if v in {7,9,10,12} else 14)
            elif v in {7,11,12,15}:put(q,5 if v in {11,15} else 13)
            elif v in {9,10}:put(q,1 if v==9 else 13)
            elif v in {5,13}:put(q,1) # Clown nose/lips become black paint.
        elif frame['kind']=='primary' and not frame.get('common'):
            # Native blue sleeves become exposed shoulders; red/yellow singlet
            # becomes black cloth. Original grayscale body shades become skin.
            if v in {2,3}:put(q,10 if v==2 else 11)
            elif v in {5,13,6,8}:put(q,2 if v in {5,6} else 3)
            elif v in {4,14}:put(q,4 if v==4 else 14)
        elif frame['kind']=='secondary' and not frame.get('common') and v in {7,9,10,11,12,15}:
            # Doink's exposed legs become Sting's full-length black tights.
            put(q,2 if v in {7,9,10,12} else 3)
        elif v in {2,3,4,5,6,8,13,14}:
            put(q,2 if v in {2,4,5,6,13} else 3)
    if frame['kind']=='primary' and frame.get('common'):
        # The submission's shared body uses a low-cut singlet. Fill only its
        # reviewed torso region, leaving gripping hands and upper arms intact.
        torso={732:[-13,-61,-2,-48],737:[-15,-42,-4,-28],738:[-1,-22,5,-12]}.get(frame['index'])
        if torso:
            l,t,r,b=torso
            for q,v in points.items():
                if l<=q[0]<=r and t<=q[1]<=b and q not in head and v in {7,9,10,11,12,15}:
                    put(q,2 if v in {7,9,10,12} else 3)
            if frame['index']==737:
                glyph=['11000011','01100110','00111100','11011011','00111100','11011011','00011000','00001100','00000100']
                for y,row in enumerate(glyph):
                    for x,v in enumerate(row):
                        q=(-14+x,-39+y)
                        if v=='1' and q in points:put(q,8 if (x+y)%3 else 6)
    if head:
        # Only wide, upright front torso islands receive the scorpion. Side,
        # inverted, obscured and back pieces keep attached plain black cloth.
        face = sum(points[q] in {7,11,12,15} for q in head) if front else 0
        if not frame.get('common'):
            # Attach dark strands to an upright head's native shoulder pixels.
            # Rotated heads keep their original geometry until individually
            # authored; this must not turn into a screen-aligned floating mark.
            l=min(x for x,y in head);r=max(x for x,y in head)
            t=min(y for x,y in head);b=max(y for x,y in head)
            below=[q for q,v in points.items() if q not in head and v in {5,13,6,8}]
            if below and 13<=b-t<=22 and sum(y for x,y in below)/len(below)>b+5:
                for y in range(b-1,b+8):
                    for x in range(l+2,l+5-(y>=b+5)):
                        q=x,y
                        if q in points:put(q,4 if x==l+2 else 14)
        garments=components({q:v for q,v in points.items() if q not in head},{5,13,6,8})
        if garments and face>=35:
            cloth=max(garments,key=len)
            l=min(x for x,y in cloth);r=max(x for x,y in cloth)
            t=min(y for x,y in cloth);b=max(y for x,y in cloth)
            if r-l>=12 and b-t>=15 and t>=min(y for x,y in head)+10:
                ox=(l+r-12)//2;oy=t+max(1,(b-t-14)//2)
                for y,row in enumerate(SCORPION):
                    for x,v in enumerate(row):
                        q=ox+x,oy+y
                        if v=='1' and q in cloth:put(q,8 if (x+y)%3 else 6)
    return changes
