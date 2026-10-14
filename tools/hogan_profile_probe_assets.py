"""Private slot-probe assets using source portrait and Raw's native lettering."""
from PIL import Image
from perfect_profile_assets import packet,planar_image
from decode_graphics import decode_block
from inspect_rom import tile


def quantize(image,count,offset=0):
    indexed=image.convert('RGB').quantize(count,method=Image.Quantize.MEDIANCUT,dither=Image.Dither.NONE)
    palette=indexed.getpalette()+[0]*768
    colors=[]
    for i in range(count):
        r,g,b=[round(palette[i*3+c]*31/255)for c in range(3)]
        colors.append(r|g<<5|b<<10)
    return [p+offset for p in indexed.getdata()],colors


def configure(out,stock,portrait,*,slot=13,asset_bank=0x4a,hud_bank=0x55,
              name='HULK HOGAN',hometown='VENICE BEACH',height='6\'8"',
              weight='275',special='LEG DROP',previous_rows=None):
    record=0x708000+slot*45
    def asset(address):return asset_bank*65536+(address&65535)
    hud_address=hud_bank*65536+0x8000
    def put(at,data):
        if any(v!=255 for v in out[at:at+len(data)]):raise ValueError(f'Occupied asset region {at:06x}')
        out[at:at+len(data)]=data
    def pointer(at,value):out[at:at+3]=value.to_bytes(3,'little')
    def text(value):
        data=value.encode('ascii')+b'\0';at=out.find(b'\xff'*len(data),0x2eff49,0x2f0000)
        if at<0:raise ValueError('No free bio string storage')
        out[at:at+len(data)]=data
        return (at&65535).to_bytes(2,'little')
    for field,value in ((28,name),(30,hometown),(36,height),(38,special)):
        out[record+field:record+field+2]=text(value)
    out[record+32:record+36]=weight.encode('ascii')[:3].ljust(4,b'\0')
    portrait=portrait.convert('RGB')
    if portrait.size!=(128,120):raise ValueError('Expected private 128x120 source portrait')
    pixels,colors=quantize(portrait,64,64)
    put(asset(0x4a0000),packet(planar_image(pixels,128,120,8)))
    stockpal=int.from_bytes(stock[0x2efaf5+45+4:0x2efaf5+45+7],'little')&0x3fffff
    put(asset(0x4a4200),stock[stockpal:stockpal+64]+b''.join(c.to_bytes(2,'little')for c in colors))
    pointer(record,asset(0x4a0000));pointer(record+4,asset(0x4a4200))
    monitor=portrait.crop((4,0,124,120)).resize((48,48),Image.Resampling.LANCZOS)
    pixels,colors=quantize(monitor,31,1)
    put(asset(0x4a4400),packet(planar_image(pixels,48,48,8)))
    put(asset(0x4a4f00),b'\0\0'+b''.join(c.to_bytes(2,'little')for c in colors))
    pointer(record+20,asset(0x4a4400));pointer(record+24,asset(0x4a4f00))
    font,_=decode_block(stock,2808803);logo=[0]*(256*224);left=(256-len(name)*16)//2
    for n,letter in enumerate(name):
        if letter==' ':continue
        start=(ord(letter)-65)*4
        for y in range(16):
            for x in range(16):
                at=(start+(y//8)*2+x//8)*16+y%8*2
                logo[(24+y)*256+left+n*16+x]=((font[at]>>(7-x%8))&1)|(((font[at+1]>>(7-x%8))&1)<<1)
    encoded=planar_image(logo,256,224,4);tiles=[bytes(32)];lookup={tiles[0]:0};mapping=bytearray(2048)
    for i in range(896):
        chunk=bytes(encoded[i*32:i*32+32])
        if chunk not in lookup:lookup[chunk]=len(tiles);tiles.append(chunk)
        mapping[i*2:i*2+2]=lookup[chunk].to_bytes(2,'little')
    put(asset(0x4a5000),packet(b''.join(tiles)));put(asset(0x4a6000),packet(mapping))
    put(asset(0x4a6900),b''.join(c.to_bytes(2,'little')for c in [0,32767,0,16912]+[0]*12))
    for delta,address in ((8,asset(0x4a5000)),(12,asset(0x4a6000)),(16,asset(0x4a6900))):pointer(record+delta,address)
    # The four corrected announcer arrays have 16-word capacity.
    for at,field,bank in ((0x70e400,20,False),(0x70e420,20,True),(0x70e440,24,False),(0x70e460,24,True)):
        value=int.from_bytes(out[record+field:record+field+3],'little')
        out[at+slot*2:at+slot*2+2]=(value>>16 if bank else value&65535).to_bytes(2,'little')
    # Derive small lettering from the immutable stock atlas.
    graphics,_=decode_block(stock,0x2ace03);glyphs={}
    labels=[('LUNAVACHON',range(64,72)),('BRETHART',[0,72,73,74,75,76,77,0]),
            ('UNDERTAKER',[78,79,80,81,82,83,81,84]),('YOKOZUNA',[0,85,86,87,88,89,90,0]),
            ('BAMBAMBIGELOW',[91,92,91,92,93,94,95,96]),('RAZORRAMON',range(98,106)),
            ('LEXLUGER',[0,106,107,108,109,110,101,0]),
            ('SHAWNMICHAELS',range(114,122)),('DIESEL',[0,0,128,129,130,131,0,0])]
    for label,ids in labels:
        ids=list(ids);pixels=[[tile(graphics,ids[x//8]*32,4)[y*8+x%8]==9 for x in range(64)]for y in range(8)]
        spans=[];x=0
        while x<64:
            if not any(row[x]for row in pixels):x+=1;continue
            start=x
            while x<64 and any(row[x]for row in pixels):x+=1
            spans.append((start,x))
        if len(spans)==len(label):
            for letter,(l,r)in zip(label,spans):glyphs.setdefault(letter,[row[l:r]for row in pixels])
    glyphs.setdefault('S',[[False]*5,*[[c=='1' for c in row]for row in ('01111','11000','11000','01110','00011','11110')],[False]*5])
    glyphs.setdefault('I',[[False]*3,[True]*3,[False,True,False],[False,True,False],[False,True,False],[False,True,False],[True]*3,[False]*3])
    pixels=[0]*512;left=(64-sum(3 if c==' 'else len(glyphs[c][0])+1 for c in name)+1)//2
    for letter in name:
        if letter==' ':left+=3;continue
        rows=glyphs[letter]
        for y,row in enumerate(rows):
            for x,value in enumerate(row):
                if value:pixels[y*64+left+x]=9
        left+=len(rows[0])+1
    current=int.from_bytes(out[0x19ee4c:0x19ee4e],'little')|out[0x19ee49]<<16
    atlas=bytearray(decode_block(out,current)[0]);old_rows=bytes(previous_rows) if previous_rows is not None else bytes(out[0x1a4451:0x1a4451+slot*8]);used=set(old_rows)
    free=[i for i in range(237,256)if i not in used]
    if len(free)<8:raise ValueError('No independent HUD tiles for new worker')
    label=planar_image(pixels,64,8,4)
    for i,ident in enumerate(free[:8]):atlas[ident*32:ident*32+32]=label[i*32:i*32+32]
    put(hud_address,packet(atlas));out[0x19ee49]=hud_bank;out[0x19ee4c:0x19ee4e]=(0x8000).to_bytes(2,'little')
    rows=old_rows+bytes(free[:8]);put(asset(0x4a9000),rows)
    put(asset(0x4a9080),b''.join((0x9000+i*8).to_bytes(2,'little')for i in range(slot+1)))
    if out[0x2fe5de:0x2fe5e1] not in (bytes.fromhex('b9 44 da'),bytes.fromhex('80 90 4a')):raise ValueError('Unsupported HUD lookup')
    out[0x2fe5de:0x2fe5e1]=(asset(0x4a9080)).to_bytes(3,'little');out[0x2fe5e4]=asset_bank
