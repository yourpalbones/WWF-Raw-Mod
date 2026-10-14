"""Minimal 65816 disassembler for reading WWF Raw hook sites (HiROM/ExHiROM file offsets).

Tracks REP/SEP to size immediates; start state defaults to 16-bit A and X (m=0, x=0).

    python3 tools/disasm65816.py ROM CPU_ADDRESS [COUNT] [--m8] [--x8]
"""
import argparse
from pathlib import Path

MODES = {
    'imp': 0, 'acc': 0, 'imm_m': -1, 'imm_x': -2, 'imm8': 1, 'dp': 1, 'dpx': 1, 'dpy': 1, 'idp': 1, 'idpx': 1,
    'idpy': 1, 'ildp': 1, 'ildpy': 1, 'sr': 1, 'isry': 1, 'abs': 2, 'absx': 2, 'absy': 2, 'iabs': 2, 'iabsx': 2,
    'ilabs': 2, 'long': 3, 'longx': 3, 'rel': 1, 'rell': 2, 'bm': 2,
}
OPS = {}
def op(code, name, mode):
    OPS[code] = (name, mode)

for base, name in [(0x00, 'ora'), (0x20, 'and'), (0x40, 'eor'), (0x60, 'adc'), (0x80, 'sta'), (0xa0, 'lda'), (0xc0, 'cmp'), (0xe0, 'sbc')]:
    for off, mode in [(0x01, 'idpx'), (0x03, 'sr'), (0x05, 'dp'), (0x07, 'ildp'), (0x09, 'imm_m'), (0x0d, 'abs'), (0x0f, 'long'),
                      (0x11, 'idpy'), (0x12, 'idp'), (0x13, 'isry'), (0x15, 'dpx'), (0x17, 'ildpy'), (0x19, 'absy'),
                      (0x1d, 'absx'), (0x1f, 'longx')]:
        if name == 'sta' and off == 0x09:
            continue
        op(base + off, name, mode)
table = {
    0x00: ('brk', 'imm8'), 0x02: ('cop', 'imm8'), 0x04: ('tsb', 'dp'), 0x06: ('asl', 'dp'), 0x08: ('php', 'imp'),
    0x0a: ('asl', 'acc'), 0x0b: ('phd', 'imp'), 0x0c: ('tsb', 'abs'), 0x0e: ('asl', 'abs'), 0x10: ('bpl', 'rel'),
    0x14: ('trb', 'dp'), 0x16: ('asl', 'dpx'), 0x18: ('clc', 'imp'), 0x1a: ('inc', 'acc'), 0x1b: ('tcs', 'imp'),
    0x1c: ('trb', 'abs'), 0x1e: ('asl', 'absx'), 0x20: ('jsr', 'abs'), 0x22: ('jsl', 'long'), 0x24: ('bit', 'dp'),
    0x26: ('rol', 'dp'), 0x28: ('plp', 'imp'), 0x2a: ('rol', 'acc'), 0x2b: ('pld', 'imp'), 0x2c: ('bit', 'abs'),
    0x2e: ('rol', 'abs'), 0x30: ('bmi', 'rel'), 0x34: ('bit', 'dpx'), 0x36: ('rol', 'dpx'), 0x38: ('sec', 'imp'),
    0x3a: ('dec', 'acc'), 0x3b: ('tsc', 'imp'), 0x3c: ('bit', 'absx'), 0x3e: ('rol', 'absx'), 0x40: ('rti', 'imp'),
    0x42: ('wdm', 'imm8'), 0x44: ('mvp', 'bm'), 0x46: ('lsr', 'dp'), 0x48: ('pha', 'imp'), 0x4a: ('lsr', 'acc'),
    0x4b: ('phk', 'imp'), 0x4c: ('jmp', 'abs'), 0x4e: ('lsr', 'abs'), 0x50: ('bvc', 'rel'), 0x54: ('mvn', 'bm'),
    0x56: ('lsr', 'dpx'), 0x58: ('cli', 'imp'), 0x5a: ('phy', 'imp'), 0x5b: ('tcd', 'imp'), 0x5c: ('jml', 'long'),
    0x5e: ('lsr', 'absx'), 0x60: ('rts', 'imp'), 0x62: ('per', 'rell'), 0x64: ('stz', 'dp'), 0x66: ('ror', 'dp'),
    0x68: ('pla', 'imp'), 0x6a: ('ror', 'acc'), 0x6b: ('rtl', 'imp'), 0x6c: ('jmp', 'iabs'), 0x6e: ('ror', 'abs'),
    0x70: ('bvs', 'rel'), 0x74: ('stz', 'dpx'), 0x76: ('ror', 'dpx'), 0x78: ('sei', 'imp'), 0x7a: ('ply', 'imp'),
    0x7b: ('tdc', 'imp'), 0x7c: ('jmp', 'iabsx'), 0x7e: ('ror', 'absx'), 0x80: ('bra', 'rel'), 0x82: ('brl', 'rell'),
    0x84: ('sty', 'dp'), 0x86: ('stx', 'dp'), 0x88: ('dey', 'imp'), 0x89: ('bit', 'imm_m'), 0x8a: ('txa', 'imp'),
    0x8b: ('phb', 'imp'), 0x8c: ('sty', 'abs'), 0x8e: ('stx', 'abs'), 0x90: ('bcc', 'rel'), 0x94: ('sty', 'dpx'),
    0x96: ('stx', 'dpy'), 0x98: ('tya', 'imp'), 0x9a: ('txs', 'imp'), 0x9b: ('txy', 'imp'), 0x9c: ('stz', 'abs'),
    0x9e: ('stz', 'absx'), 0xa0: ('ldy', 'imm_x'), 0xa2: ('ldx', 'imm_x'), 0xa4: ('ldy', 'dp'), 0xa6: ('ldx', 'dp'),
    0xa8: ('tay', 'imp'), 0xaa: ('tax', 'imp'), 0xab: ('plb', 'imp'), 0xac: ('ldy', 'abs'), 0xae: ('ldx', 'abs'),
    0xb0: ('bcs', 'rel'), 0xb4: ('ldy', 'dpx'), 0xb6: ('ldx', 'dpy'), 0xb8: ('clv', 'imp'), 0xba: ('tsx', 'imp'),
    0xbb: ('tyx', 'imp'), 0xbc: ('ldy', 'absx'), 0xbe: ('ldx', 'absy'), 0xc0: ('cpy', 'imm_x'), 0xc2: ('rep', 'imm8'),
    0xc4: ('cpy', 'dp'), 0xc6: ('dec', 'dp'), 0xc8: ('iny', 'imp'), 0xca: ('dex', 'imp'), 0xcb: ('wai', 'imp'),
    0xcc: ('cpy', 'abs'), 0xce: ('dec', 'abs'), 0xd0: ('bne', 'rel'), 0xd4: ('pei', 'dp'), 0xd6: ('dec', 'dpx'),
    0xd8: ('cld', 'imp'), 0xda: ('phx', 'imp'), 0xdb: ('stp', 'imp'), 0xdc: ('jml', 'ilabs'), 0xde: ('dec', 'absx'),
    0xe0: ('cpx', 'imm_x'), 0xe2: ('sep', 'imm8'), 0xe4: ('cpx', 'dp'), 0xe6: ('inc', 'dp'), 0xe8: ('inx', 'imp'),
    0xea: ('nop', 'imp'), 0xeb: ('xba', 'imp'), 0xec: ('cpx', 'abs'), 0xee: ('inc', 'abs'), 0xf0: ('beq', 'rel'),
    0xf4: ('pea', 'abs'), 0xf6: ('inc', 'dpx'), 0xf8: ('sed', 'imp'), 0xfa: ('plx', 'imp'), 0xfb: ('xce', 'imp'),
    0xfc: ('jsr', 'iabsx'), 0xfe: ('inc', 'absx'),
}
OPS.update(table)
FORMAT = {'imp': '', 'acc': 'a', 'imm8': '#${:02x}', 'dp': '${:02x}', 'dpx': '${:02x},x', 'dpy': '${:02x},y',
          'idp': '(${:02x})', 'idpx': '(${:02x},x)', 'idpy': '(${:02x}),y', 'ildp': '[${:02x}]', 'ildpy': '[${:02x}],y',
          'sr': '${:02x},s', 'isry': '(${:02x},s),y', 'abs': '${:04x}', 'absx': '${:04x},x', 'absy': '${:04x},y',
          'iabs': '(${:04x})', 'iabsx': '(${:04x},x)', 'ilabs': '[${:04x}]', 'long': '${:06x}', 'longx': '${:06x},x'}


def offset(address, size):
    bank = address >> 16
    if size >= 0x600000 and 0x40 <= bank <= 0x7d:
        return address & 0x7fffff
    return address & 0x3fffff


def disassemble(rom, address, count=40, m8=False, x8=False):
    out = []
    for _ in range(count):
        at = offset(address, len(rom))
        code = rom[at]
        name, mode = OPS.get(code, ('???', 'imp'))
        size = MODES[mode]
        if size == -1:
            size = 1 if m8 else 2
        elif size == -2:
            size = 1 if x8 else 2
        operand = int.from_bytes(rom[at + 1:at + 1 + size], 'little')
        if mode in ('imm_m', 'imm_x'):
            text = f'#${operand:0{size * 2}x}'
        elif mode == 'rel':
            text = f'${(address + 2 + (operand - 256 if operand & 128 else operand)) & 0xffff | address & 0xff0000:06x}'
        elif mode == 'rell':
            text = f'${(address + 3 + (operand - 65536 if operand & 32768 else operand)) & 0xffff | address & 0xff0000:06x}'
        elif mode == 'bm':
            text = f'${operand & 255:02x},${operand >> 8:02x}'
        else:
            text = FORMAT[mode].format(operand) if FORMAT[mode] else ''
        out.append((address, rom[at:at + 1 + size].hex(' '), f'{name} {text}'.strip()))
        if name == 'rep':
            m8 = m8 and not operand & 0x20; x8 = x8 and not operand & 0x10
        if name == 'sep':
            m8 = m8 or bool(operand & 0x20); x8 = x8 or bool(operand & 0x10)
        address = (address & 0xff0000) | ((address + 1 + size) & 0xffff)
    return out


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('rom', type=Path); p.add_argument('address', type=lambda s: int(s, 16))
    p.add_argument('count', type=int, nargs='?', default=40)
    p.add_argument('--m8', action='store_true'); p.add_argument('--x8', action='store_true')
    a = p.parse_args()
    for address, raw, text in disassemble(a.rom.read_bytes(), a.address, a.count, a.m8, a.x8):
        print(f'{address:06x}  {raw:<12} {text}')
