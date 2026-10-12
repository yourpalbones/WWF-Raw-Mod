"""Show corrected, landmark-anchored Syxx face pixels; not gameplay proof."""
import argparse
import copy
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw

from native_gear_art import decorate
from scott_frame_catalog import catalog, raster


def colors(rom, revised=False):
    palette = [int.from_bytes(rom[0x2cc4da+9*32+i*2:0x2cc4dc+9*32+i*2], "little")
               for i in range(16)]
    if revised:
        for i, (r,g,b) in {2:(29,2,2),3:(16,0,0),4:(1,1,1),5:(29,29,29),
                            6:(2,1,1),8:(6,6,6)}.items():
            palette[i] = r | g<<5 | b<<10
    return [tuple((v>>s&31)*255//31 for s in [0,5,10]) for v in palette]


def revised(frame):
    changes = decorate(frame, 9)
    frame = copy.deepcopy(frame)
    for part in frame["parts"]:
        for ref in part["refs"]:
            if ref["field"] in changes:
                edited = changes[ref["field"]]
                assert all((a==0)==(b==0) for a,b in zip(ref["pixels"], edited))
                ref["pixels"] = edited
    return frame


def crop(frame, palette, box):
    points, _ = raster(frame)
    l,t,r,b = box
    image = Image.new("RGB", (r-l+1,b-t+1), "#23232b")
    for (x,y),value in points.items():
        if l<=x<=r and t<=y<=b:
            image.putpixel((x-l,y-t), palette[value])
    return image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rom", type=Path)
    parser.add_argument("wram", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rom = args.rom.read_bytes()
    frames = catalog(rom, args.wram.read_bytes(), 9)
    args.output.mkdir(parents=True, exist_ok=True)
    from syxx_head_art import face_landmarks
    registered=face_landmarks()
    checked=0
    for frame in frames:
        before,_=raster(frame)
        after,_=raster(revised(frame))
        assert before.keys()==after.keys(), frame['index']
        if frame['kind']!='primary' or str(frame['index'])not in registered['heads']:
            continue
        entry=registered['heads'][str(frame['index'])]
        sx,sy,dx,dy=entry['transform']
        landmarks=registered['templates'][str(entry['template'])]['landmarks']
        for key in ('eyes','nose','mouth'):
            anchors=[landmarks[key]] if key=='nose' else landmarks[key]
            for x,y in anchors:
                q=(sx*x+dx,sy*y+dy)
                assert before[q]==after[q], (frame['index'],key,q)
        checked+=1
    (args.output/'landmark-verification.json').write_text(json.dumps({
        'original_rom_sha256': hashlib.sha256(rom).hexdigest(),
        'scope': 'Decoded draft art only; emulator/editor release verification pending.',
        'silhouette_frame_pieces_checked': len(frames),
        'silhouettes_unchanged': True,
        'registered_faces_checked': checked,
        'marked_eyes_nose_mouth_preserved': True,
        'exact_original_texture_pixels_per_registration': 49,
    },indent=2)+'\n')
    original = crop(frames[1], colors(rom), [-8,-44,8,-24])
    corrected = crop(revised(frames[1]), colors(rom, True), [-8,-44,8,-24])
    comparison = Image.new("RGB", (640,470), "#23232b")
    draw = ImageDraw.Draw(comparison)
    for x, label, image in [(25,"Original native face",original),
                             (345,"Corrected beard draft",corrected)]:
        draw.text((x,10),label,fill="white")
        comparison.paste(image.resize((272,336),Image.Resampling.NEAREST),(x,40))
    draw.text((25,395),"Eyes: row 9 | Nose: row 11 | Mouth: rows 13-14",fill="white")
    draw.text((25,420),"Moustache: row 12 | Beard sides: 13-14 | Jaw: 15",fill="white")
    draw.text((25,445),"Decoded sprite art study. No smoothing. Not a gameplay capture.",fill="white")
    comparison.save(args.output/"corrected-landmarks.png")
    grid = Image.new("RGB", (460,575), "#23232b")
    draw = ImageDraw.Draw(grid)
    draw.text((8,8),"Corrected draft: same coordinates as your marked original",fill="white")
    for column in range(17):
        draw.text((54+column*24,28),str(column),fill="white")
    for row in range(21):
        draw.text((8,61+row*24),str(row),fill="white")
        for column in range(17):
            x,y=50+column*24,55+row*24
            draw.rectangle((x,y,x+23,y+23), fill=corrected.getpixel((column,row)), outline="#494b58")
    grid.save(args.output/"corrected-head-grid.png")
    from native_gear_art import head_region
    ids=[1,2,3,4,5,6,7,8]
    poses=Image.new("RGB",(960,230),"#23232b")
    draw=ImageDraw.Draw(poses)
    for column,idx in enumerate(ids):
        frame=frames[idx]
        head,_=head_region(frame,raster(frame)[0])
        box=[min(x for x,y in head),min(y for x,y in head),max(x for x,y in head),max(y for x,y in head)]
        image=crop(revised(frame),colors(rom,True),box)
        poses.paste(image.resize((image.width*5,image.height*5),Image.Resampling.NEAREST),(column*120+12,38))
        draw.text((column*120+12,10),"Primary "+str(idx),fill="white")
    draw.text((12,180),"Eight native poses: the same exact eye/nose texture carries the landmarks.",fill="white")
    draw.text((12,205),"Other head drawings still require separate mapping. This is not an editor release.",fill="white")
    poses.save(args.output/"corrected-eight-poses.png")
    print("Wrote landmark comparison, pixel grid and eight native pose drafts")


if __name__=="__main__":
    main()
