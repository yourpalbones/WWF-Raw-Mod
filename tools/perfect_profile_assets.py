"""Mr. Perfect's native-source portrait, monitor and Raw-font name graphics."""
from pathlib import Path
from PIL import Image
from decode_graphics import decode_block
from inspect_rom import tile


def packet(data):
    out=bytearray(len(data).to_bytes(2,'little')+b'\x01')
    end=len(data)
    while end:
        start=max(0,end-64);out.append(63+end-start);out+=data[start:end];end=start
    return out+b'\x00'


def planar_image(pixels,width,height,bpp):
    out=bytearray(width*height*bpp//8)
    for i,value in enumerate(pixels):
        x,y=i%width,i//width;base=((y//8)*(width//8)+x//8)*bpp*8
        for plane in range(bpp):out[base+(plane//2)*16+(y%8)*2+plane%2]|=((value>>plane)&1)<<(7-x%8)
    return out


def quantize(image,count,offset=0):
    im=image.convert('RGB').quantize(count,method=Image.Quantize.MEDIANCUT,dither=Image.Dither.NONE)
    pal=im.getpalette();colors=[]
    for i in range(count):
        channels=[round(pal[i*3+c]*31/255)for c in range(3)]
        colors.append(channels[0]|channels[1]<<5|channels[2]<<10)
    return [v+offset for v in im.getdata()],colors


def configure(out,original,portrait_path):
    portrait=(portrait_path if isinstance(portrait_path,Image.Image)else Image.open(portrait_path)).convert('RGB')
    if portrait.size==(256,224):portrait=portrait.crop((24,39,152,159))
    if portrait.size!=(128,120):raise ValueError('Expected native Royal selection capture or 128x120 portrait')
    record=0x708000+12*45
    def pointer(at,address):out[at:at+3]=address.to_bytes(3,'little')
    def put(at,data):
        if any(v!=255 for v in out[at:at+len(data)]):raise ValueError(f'Profile allocation occupied: {at:06x}')
        out[at:at+len(data)]=data
    pixels,colors=quantize(portrait,64,64)
    put(0x708800,packet(planar_image(pixels,128,120,8)))
    stock_palette=int.from_bytes(original[0x2efaf5+45+4:0x2efaf5+45+7],'little')&0x3fffff
    put(0x708700,original[stock_palette:stock_palette+64]+b''.join(v.to_bytes(2,'little')for v in colors))
    pointer(record,0x708800);pointer(record+4,0x708700)
    monitor=portrait.crop((4,0,124,120)).resize((48,48),Image.Resampling.LANCZOS)
    pixels,colors=quantize(monitor,31,1)
    put(0x70c800,packet(planar_image(pixels,48,48,8)))
    put(0x70d200,b'\x00\x00'+b''.join(v.to_bytes(2,'little')for v in colors))
    pointer(record+20,0x70c800);pointer(record+24,0x70d200)
    # Append new strings into unused editor text space, preserving all twelve
    # current profile strings and their original shared pointers.
    def text(value):
        packet=value.encode('ascii')+b'\x00'
        start=out.find(bytes([255])*len(packet),0x2eff49,0x2f0000)
        if start<0:raise ValueError('No room for imported bio; preserve existing bios')
        out[start:start+len(packet)]=packet
        return (start&65535).to_bytes(2,'little')
    for offset,value in [(28,'MR PERFECT'),(30,'MINNESOTA'),(36,'6\'4"'),(38,'PERFECT-\rPLEX')]:
        out[record+offset:record+offset+2]=text(value)
    out[record+32:record+36]=b'257\x00'
    # Render the same 16x16 lettering used by the editor's name-logo feature.
    font,_=decode_block(original,2808803)
    logo=[0]*(256*224);name='MR PERFECT';left=(256-len(name)*16)//2
    for n,letter in enumerate(name):
        if letter==' ':continue
        start=(ord(letter)-65)*4
        for y in range(16):
            for x in range(16):
                at=(start+(y//8)*2+x//8)*16+(y%8)*2
                value=((font[at]>>(7-x%8))&1)|(((font[at+1]>>(7-x%8))&1)<<1)
                logo[(24+y)*256+left+n*16+x]=value
    raw=planar_image(logo,256,224,4);chunks=[bytes(32)];lookup={chunks[0]:0};mapdata=bytearray(2048)
    for i in range(896):
        chunk=bytes(raw[i*32:i*32+32])
        if chunk not in lookup:lookup[chunk]=len(chunks);chunks.append(chunk)
        mapdata[i*2:i*2+2]=lookup[chunk].to_bytes(2,'little')
    put(0x70d400,packet(b''.join(chunks)));put(0x70d800,packet(mapdata))
    put(0x70e200,b''.join(v.to_bytes(2,'little')for v in [0,32767,0,16912]+[0]*12))
    for delta,address in [(8,0x70d400),(12,0x70d800),(16,0x70e200)]:pointer(record+delta,address)
    # Announcer tables index the logical roster directly. Relocate every table
    # with its existing twelve entries unchanged and append this worker's assets.
    for old,new,stride,address in [(0x2ee90f,0x70e400,2,0x70c800),(0x2ee927,0x70e420,1,0x70c800),
                                   (0x2ee93f,0x70e440,2,0x70d200),(0x2ee957,0x70e460,1,0x70d200)]:
        data=bytes(out[old:old+12*stride])+(address&65535).to_bytes(2,'little') if stride==2 else bytes(out[old:old+12])+bytes([address>>16])
        put(new,data)
        pattern=(old|0x800000).to_bytes(3,'little');cursor=0;refs=0
        while True:
            cursor=out.find(pattern,cursor,0x300000)
            if cursor<0:break
            if out[cursor-1]==0xbf:
                out[cursor:cursor+3]=new.to_bytes(3,'little');refs+=1
            cursor+=1
        if refs!=2:raise ValueError(f'Unexpected announcer references: {old:06x} {refs}')
    # Preserve all twelve current HUD labels; replace the dedicated mystery
    # tiles (135..142) with the thirteenth name using the existing Raw font.
    stock,_=decode_block(original,0x2ace03)
    names=['BAMBAMBIGELOW','BRETHART','UNDERTAKER','LEXLUGER','YOKOZUNA','RAZORRAMON',
           'OWENHART','DOINK','SHAWNMICHAELS','123KID','DIESEL','LUNAVACHON']
    glyphs={}
    stock_ids=[[64,65,66,67,68,69,70,71],[0,72,73,74,75,76,77,0],[78,79,80,81,82,83,81,84],[0,85,86,87,88,89,90,0],[91,92,91,92,93,94,95,96],[98,99,100,101,102,103,104,105],[0,106,107,108,109,110,101,0],[0,0,111,112,97,113,0,0],[114,115,116,117,118,119,120,121],[0,122,123,124,125,126,127,0],[0,0,128,129,130,131,0,0],[0,132,133,134,75,76,77,0]]
    for i,text in enumerate(names):
        ids=stock_ids[i]
        pts=[[tile(stock,t*32,4)[y*8+x%8]==9 for x,t in enumerate([ids[x//8] for x in range(64)])]for y in range(8)]
        spans=[];x=0
        while x<64:
            if not any(row[x]for row in pts):x+=1;continue
            start=x
            while x<64 and any(row[x]for row in pts):x+=1
            spans.append((start,x))
        if len(spans)!=len(text):continue
        for letter,(l,r)in zip(text,spans):glyphs.setdefault(letter,(r-l,[row[l:r]for row in pts]))
    for letter,rows in {'P':['###.','#..#','###.','#...','#...'],'F':['####','#...','###.','#...','#...'],'C':['.###','#...','#...','#...','.###']}.items():
        glyphs[letter]=(4,[[False]*4]+[[v=='#'for v in row]for row in rows]+[[False]*4]*2)
    label=[0]*512;left=(64-sum(3 if c==' 'else glyphs[c][0]+1 for c in name)+1)//2
    for letter in name:
        if letter==' ':left+=3;continue
        width,rows=glyphs[letter]
        for y,row in enumerate(rows):
            for x,value in enumerate(row):
                if value:label[y*64+left+x]=9
        left+=width+1
    source=((out[0x19ee49]<<16)|int.from_bytes(out[0x19ee4c:0x19ee4e],'little'))&0x3fffff
    graphics,_=decode_block(out,source);graphics=bytearray(graphics)
    encoded=planar_image(label,64,8,4)
    graphics[135*32:143*32]=encoded
    put(0x738000,packet(graphics))
    out[0x19ee49]=0x73;out[0x19ee4c:0x19ee4e]=bytes.fromhex('00 80')
    out[0x1a4451+12*8:0x1a4459+12*8]=bytes(range(135,143))
    return {'portrait':0x708800,'monitor':0x70c800,'name':'MR PERFECT','hud':0x738000,
            'all_existing_hud_names_preserved':True,'all_existing_announcer_entries_preserved':True}
