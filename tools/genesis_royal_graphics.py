"""Genesis Royal Rumble native sprite tile decoder, derived from $008996.

Tiles use shared packed-nibble art and a per-actor byte lookup for gear colors.
Four families: raw tiles, masked repeated bytes, masked repeated rows and solid.
This module decodes source packets; it does not establish Raw move compatibility.
"""
import argparse
import hashlib
import json
from pathlib import Path

SOURCE_SHA256 = 'fa8d80b0646fe463bea669c14590ddbfe0a55142ae924098503185b864cc66a4'


def u16(data, at):
    return int.from_bytes(data[at:at+2], 'big')


def u32(data, at):
    return int.from_bytes(data[at:at+4], 'big')


def decode_tile(rom, ident, lookup=bytes(range(256))):
    if not 0 <= ident <= 0xd9fa or len(lookup) != 256:
        raise ValueError('Invalid source tile or byte translation lookup')
    if ident < 0x17d6:
        at, length = 0xbe436+ident*32, 32
        raw = rom[at:at+32]
        family = 'raw'
    elif ident < 0xc73f:
        upper = 0xbe372
        while ident >= u16(rom,upper):
            upper += 2
        delta = upper-0xbe372
        length = 31-delta//2
        at = 0xbe370+u32(rom,0xbe3b2+delta*2)+(ident-u16(rom,upper-2))*length
        mask, fill = u32(rom,at), rom[at+4]
        cursor, out = at+5, bytearray()
        for i in range(32):
            if mask & (1 << (31-i)):
                out.append(fill)
            else:
                out.append(rom[cursor]);cursor += 1
        if cursor != at+length:
            raise ValueError('Byte-mask packet does not consume its fixed size')
        raw, family = bytes(out), 'byte-mask'
    elif ident < 0xd9f7:
        upper = 0xbe3a4
        while ident >= u16(rom,upper):
            upper += 2
        delta = upper-0xbe3a4
        length = u16(rom,0x2336+delta)
        at = 0xbe370+u32(rom,0xbe416+delta*2)+(ident-u16(rom,upper-2))*length
        fill, mask, cursor, out = rom[at], rom[at+1], at+2, bytearray()
        for bit in range(7, -1, -1):
            if mask & (1 << bit):
                out.extend(rom[cursor:cursor+4]);cursor += 4
            else:
                out.extend([fill]*4)
        if cursor != at+length:
            raise ValueError('Row-mask packet does not consume its fixed size')
        raw, family = bytes(out), 'row-mask'
    else:
        at, length = 0x1fff8a+(ident-0xd9f7)*2, 2
        raw, family = bytes([rom[at]])*32, 'solid'
    if len(raw) != 32 or not 0 <= at <= len(rom)-length:
        raise ValueError('Source tile is truncated')
    return bytes(lookup[b] for b in raw), dict(source=at,length=length,family=family)


def verify_trace(rom, trace):
    pending, checked, families = None, 0, {}
    for line in trace.read_text().splitlines():
        event = json.loads(line)
        if event['pc'] == 0x8996:
            source = event['a'][6] & 0xffffff
            ident = u16(rom,source)
            pending = decode_tile(rom,ident,bytes.fromhex(event['lookup']))
        elif event['pc'] == 0x8bc4 and pending:
            actual = bytes.fromhex(event['last_tile'])
            if actual != pending[0]:
                raise ValueError(f'Native tile mismatch after request {checked}: {pending[1]}')
            family = pending[1]['family']
            families[family] = families.get(family,0)+1
            checked += 1
            pending = None
    if not checked:
        raise ValueError('No completed native tile objects in trace')
    return dict(native_last_tiles_checked=checked,families=families,native_bytes_match=True)


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('rom',type=Path);p.add_argument('--trace',type=Path,required=True)
    p.add_argument('--output',type=Path)
    a=p.parse_args();rom=a.rom.read_bytes()
    if hashlib.sha256(rom).hexdigest()!=SOURCE_SHA256:
        raise ValueError('Requires the verified Genesis Royal Rumble World ROM')
    report=verify_trace(rom,a.trace)
    if a.output:a.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
