"""Small native-mode 65816 interpreter for WWF Raw's decoder only.

Not a SNES emulator: no PPU, DMA, interrupts, timing or general game execution.
It executes the original ROM routine at AB:F5AE using synthetic zeroed WRAM.
"""


class DecoderCPU:
    def __init__(self, rom, source, destination=0x7F0000):
        self.rom = rom
        self.ram = bytearray(0x20000)
        self.a = self.x = self.y = 0
        self.pc = 0xF5AE
        self.pb = 0xAB
        self.db = 0
        self.m = 16
        self.c = self.z = self.n = False
        self.stack = []
        self.steps = 0
        self.writes = set()
        self.store(0x7C, source, 3)
        self.store(0x80, destination, 3)
        self.store(0x90, 0, 2)

    def read8(self, addr):
        addr &= 0xFFFFFF
        bank = addr >> 16
        off = addr & 0xFFFF
        if bank in (0x7E, 0x7F):
            return self.ram[addr - 0x7E0000]
        if (bank & 0x7F) < 0x40 and off < 0x2000:
            return self.ram[off]
        if bank >= 0xC0 or (0x80 <= bank <= 0xBF and off >= 0x8000):
            index = ((bank & 0x3F) << 16) | off
            if index >= len(self.rom):
                raise ValueError(f"ROM read out of bounds {addr:06x}")
            return self.rom[index]
        raise ValueError(f"Unsupported read {addr:06x}")

    def read(self, addr, width):
        return sum(self.read8(addr + i) << (8 * i) for i in range(width))

    def store(self, addr, value, width):
        for i in range(width):
            p = (addr + i) & 0xFFFFFF
            bank = p >> 16
            off = p & 0xFFFF
            if bank in (0x7E, 0x7F):
                index = p - 0x7E0000
                self.writes.add(p)
            elif (bank & 0x7F) < 0x40 and off < 0x2000:
                index = off
            else:
                raise ValueError(f"Unsupported write {p:06x}")
            self.ram[index] = (value >> (8 * i)) & 255

    def fetch(self, n=1):
        v = self.read((self.pb << 16) | self.pc, n)
        self.pc = (self.pc + n) & 0xFFFF
        return v

    def flags(self, v, bits):
        v &= (1 << bits) - 1
        self.z = v == 0
        self.n = bool(v & (1 << (bits - 1)))
        return v

    def set_a(self, v):
        v = self.flags(v, self.m)
        self.a = v if self.m == 16 else ((self.a & 0xFF00) | v)

    def branch(self, condition):
        displacement = self.fetch()
        displacement -= 256 if displacement & 128 else 0
        if condition:
            self.pc = (self.pc + displacement) & 0xFFFF

    def run(self, limit=2000000):
        while self.steps < limit:
            at = self.pc
            op = self.fetch()
            self.steps += 1
            w = self.m // 8
            mask = (1 << self.m) - 1
            if op == 0x6B:
                return self.a & mask
            if op == 0x8B:
                self.stack.append(self.db)
            elif op == 0xD4:
                v = self.read(self.fetch(), 2)
                self.stack.extend([v >> 8, v & 255])
            elif op == 0xAB:
                self.db = self.stack.pop()
                self.flags(self.db, 8)
            elif op in (0xC2, 0xE2):
                bits = self.fetch()
                if bits & 0x20:
                    self.m = 16 if op == 0xC2 else 8
                if bits & 0x10:
                    raise ValueError("8-bit index mode not implemented")
            elif op in (0xA9, 0xA5, 0xA7, 0xB7, 0xBD, 0xBF):
                if op == 0xA9:
                    v = self.fetch(w)
                elif op == 0xA5:
                    v = self.read(self.fetch(), w)
                elif op == 0xA7:
                    v = self.read(self.read(self.fetch(), 3), w)
                elif op == 0xB7:
                    v = self.read(self.read(self.fetch(), 3) + self.y, w)
                elif op == 0xBD:
                    v = self.read(
                        (self.db << 16) | ((self.fetch(2) + self.x) & 0xFFFF), w
                    )
                else:
                    v = self.read(self.fetch(3) + self.x, w)
                self.set_a(v)
            elif op in (0x85, 0x99, 0x9D):
                addr = (
                    self.fetch()
                    if op == 0x85
                    else (
                        (self.db << 16)
                        | (
                            (self.fetch(2) + (self.y if op == 0x99 else self.x))
                            & 0xFFFF
                        )
                    )
                )
                self.store(addr, self.a, w)
            elif op == 0x84:
                self.store(self.fetch(), self.y, 2)
            elif op == 0x64:
                self.store(self.fetch(), 0, w)
            elif op == 0xE6:
                p = self.fetch()
                v = self.flags(self.read(p, w) + 1, self.m)
                self.store(p, v, w)
            elif op in (0xA4,):
                self.y = self.flags(self.read(self.fetch(), 2), 16)
            elif op in (0xA8, 0xAA):
                if op == 0xA8:
                    self.y = self.flags(self.a, 16)
                else:
                    self.x = self.flags(self.a, 16)
            elif op in (0x98, 0x8A):
                self.set_a(self.y if op == 0x98 else self.x)
            elif op == 0xBB:
                self.x = self.flags(self.y, 16)
            elif op == 0x9B:
                self.y = self.flags(self.x, 16)
            elif op in (0x88, 0xC8, 0xCA):
                if op == 0xCA:
                    self.x = self.flags(self.x - 1, 16)
                else:
                    self.y = self.flags(self.y + (1 if op == 0xC8 else -1), 16)
            elif op in (0x1A, 0x3A):
                self.set_a(self.a + (1 if op == 0x1A else -1))
            elif op == 0xEB:
                self.a = ((self.a & 255) << 8) | (self.a >> 8)
                self.flags(self.a & 255, 8)
            elif op in (0x29, 0x49):
                v = self.fetch(w)
                self.set_a((self.a & v) if op == 0x29 else (self.a ^ v))
            elif op == 0x89:
                self.z = ((self.a & mask) & self.fetch(w)) == 0
            elif op == 0x04:
                p = self.fetch()
                v = self.read(p, w)
                self.z = ((self.a & mask) & v) == 0
                self.store(p, v | self.a, w)
            elif op in (0x18, 0x38):
                self.c = op == 0x38
            elif op in (0x0A, 0x4A, 0x2A):
                v = self.a & mask
                old = self.c
                self.c = bool(v & (1 << (self.m - 1))) if op != 0x4A else bool(v & 1)
                self.set_a(
                    v >> 1
                    if op == 0x4A
                    else ((v << 1) | (int(old) if op == 0x2A else 0))
                )
            elif op in (0x65, 0x69, 0xE5, 0xE9):
                v = self.read(self.fetch(), w) if op in (0x65, 0xE5) else self.fetch(w)
                total = (
                    (self.a & mask)
                    + (v if op in (0x65, 0x69) else (v ^ mask))
                    + int(self.c)
                )
                self.c = total > mask
                self.set_a(total)
            elif op in (0xC9, 0xC5, 0xC4, 0xC0):
                bits = 16 if op in (0xC4, 0xC0) else self.m
                v = (
                    self.fetch(bits // 8)
                    if op in (0xC9, 0xC0)
                    else self.read(self.fetch(), bits // 8)
                )
                left = self.y if op in (0xC4, 0xC0) else self.a & mask
                self.c = left >= v
                self.flags(left - v, bits)
            elif op in (0xD0, 0xF0, 0x90, 0xB0, 0x30, 0x10, 0x80):
                self.branch(
                    {
                        0xD0: not self.z,
                        0xF0: self.z,
                        0x90: not self.c,
                        0xB0: self.c,
                        0x30: self.n,
                        0x10: not self.n,
                        0x80: True,
                    }[op]
                )
            elif op == 0x4C:
                self.pc = self.fetch(2)
            elif op == 0x6C:
                self.pc = self.read(self.fetch(2), 2)
            else:
                raise ValueError(
                    f"Unsupported opcode {op:02x} at {self.pb:02x}:{at:04x}"
                )
        raise ValueError("Decoder instruction limit exceeded")


def reference_decode(rom, offset):
    source = 0xC00000 | offset
    cpu = DecoderCPU(rom, source)
    length = cpu.run()
    if cpu.c:
        raise ValueError("Original decoder returned carry set (partial output)")
    if cpu.stack:
        raise ValueError("Unbalanced decoder stack")
    expected = set(range(0x7F0000, 0x7F0000 + length))
    if cpu.writes != expected:
        raise ValueError(
            f"Output write coverage differs: {len(cpu.writes)} writes, {length} expected"
        )
    return bytes(cpu.ram[0x10000 : 0x10000 + length]), cpu


if __name__ == "__main__":
    from pathlib import Path
    import argparse
    import hashlib

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rom", type=Path)
    parser.add_argument(
        "--offset", type=lambda value: int(value, 0), action="append", required=True
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    rom = args.rom.read_bytes()
    if len(rom) % 1024 == 512:
        rom = rom[512:]
    if args.output:
        args.output.mkdir(parents=True, exist_ok=True)
    for offset in args.offset:
        data, cpu = reference_decode(rom, offset)
        print(
            f"{offset:06X}: {len(data)} bytes, {cpu.steps} instructions, SHA256 {hashlib.sha256(data).hexdigest()}"
        )
        if args.output:
            (args.output / f"{offset:06x}-reference.bin").write_bytes(data)
