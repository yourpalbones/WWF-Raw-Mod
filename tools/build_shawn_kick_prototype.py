"""Build an experimental R-button kick finisher; no new sprite artwork yet."""

import argparse
import hashlib
import json
from pathlib import Path

from build_bret_gear import ORIGINAL_HASH


class Program:
    def __init__(self):
        self.code = bytearray()
        self.labels = {}
        self.branches = []

    def emit(self, instruction):
        self.code.extend(bytes.fromhex(instruction))

    def label(self, name):
        self.labels[name] = len(self.code)

    def branch(self, opcode, target):
        self.emit(opcode + " 00")
        self.branches.append((len(self.code) - 1, target))

    def finish(self):
        for address, target in self.branches:
            displacement = self.labels[target] - address - 1
            if not -128 <= displacement <= 127:
                raise ValueError("Branch outside relative range")
            self.code[address] = displacement & 255
        return bytes(self.code)


def build(rom):
    if hashlib.sha256(rom).hexdigest() != ORIGINAL_HASH:
        raise ValueError("Requires the verified unmodified USA ROM")
    # $0BEC,X is the existing actor special-hold counter. The experimental
    # marker is checked only during Shawn's kick and consumed on impact.
    # A normal A-button kick clears it before entering the original routine.
    p = Program()
    p.emit("a6 5a e0 10 00")  # Character directory selector: Shawn = $10.
    p.branch("f0", "shawn")
    p.emit("22 11 ed ac 5c c2 ec ac")  # Replay original finisher entry.
    p.label("shawn")
    p.emit("a6 36 9e ec 0b a6 56")
    p.branch("30", "fail")
    p.emit("bd c0 06 c9 be 00")  # Opponent dizzy subtype.
    p.branch("d0", "fail")
    p.emit("bd 78 0a c9 40 01")  # Red health, matching stock threshold.
    p.branch("b0", "fail")
    p.emit("bd e4 06 45 4c 89 00 40")
    p.branch("f0", "fail")
    p.emit("a9 20 00 22 06 f2 af c9 00 00")  # Native facing/range/Y check.
    p.branch("f0", "fail")
    p.emit("22 2b d1 ac c9 7e 00")  # Native standing kick setup.
    p.branch("d0", "return")
    p.emit("a6 36 a9 43 53 9d ec 0b a9 7e 00")
    p.label("return")
    p.emit("6b")
    p.label("fail")
    p.emit("a9 00 00 6b")

    damage = Program()
    damage.emit("85 90 da a6 36 bd 74 0b c9 10 00")
    damage.branch("d0", "original")
    damage.emit("bd ec 0b c9 43 53")
    damage.branch("d0", "original")
    damage.emit("bd b4 06 c9 7e 00")
    damage.branch("d0", "original")
    damage.emit("9e ec 0b fa bd 78 0a 38 e9 7e 00")
    damage.branch("b0", "store")
    damage.emit("a9 00 00")
    damage.label("store")
    damage.emit("9d 78 0a a9 84 03 85 90 bd e4 06 5c 27 cd 80")
    # The stock kick deducts 18 health before this contact callback; add 126.
    # $0A90 is a recovery delay, not a damage accumulator.
    damage.label("original")
    damage.emit("fa bd e4 06 5c 27 cd 80")

    ordinary = Program()
    ordinary.emit("da a6 36 bd 74 0b c9 10 00")
    ordinary.branch("d0", "original")
    ordinary.emit("9e ec 0b")
    ordinary.label("original")
    ordinary.emit("fa 22 9d fa ac 5c 1b d1 ac")

    hooks = [
        (0x2CECBE, "22 11 ed ac", "5c 00 00 f0"),
        (0x00CD22, "85 90 bd e4 06", "5c 00 01 f0 ea"),
        (0x2CD117, "22 9d fa ac", "5c 00 02 f0"),
    ]
    edits = []
    for address, expected, replacement in hooks:
        expected = bytes.fromhex(expected)
        if rom[address : address + len(expected)] != expected:
            raise ValueError(f"Unexpected hook bytes at {address:06x}")
        edits.append((address, bytes.fromhex(replacement)))
    edits.extend(
        [
            (0x300000, p.finish()),
            (0x300100, damage.finish()),
            (0x300200, ordinary.finish()),
        ]
    )
    result = bytearray(rom) + bytearray(b"\xff" * (0x400000 - len(rom)))
    for address, code in edits:
        result[address : address + len(code)] = code
    result[0xFFDC:0xFFE0] = bytes.fromhex("ff ff 00 00")
    checksum = sum(result) & 65535
    header = (checksum ^ 65535).to_bytes(2, "little") + checksum.to_bytes(2, "little")
    result[0xFFDC:0xFFE0] = header
    edits.append((0xFFDC, header))
    patch = bytearray(b"PATCH")
    for address in range(0x300000, 0x400000, 65535):
        length = min(65535, 0x400000 - address)
        patch += (
            address.to_bytes(3, "big") + b"\0\0" + length.to_bytes(2, "big") + b"\xff"
        )
    for address, code in edits:
        patch += address.to_bytes(3, "big") + len(code).to_bytes(2, "big") + code
    patch += b"EOF"
    report = {
        "original_sha256": ORIGINAL_HASH,
        "patched_sha256": hashlib.sha256(result).hexdigest(),
        "ips_sha256": hashlib.sha256(patch).hexdigest(),
        "experimental": True,
        "new_sprite_artwork": False,
        "additional_health_loss_on_contact": 126,
        "observed_total_health_loss": 144,
        "hooks": [f"0x{a:06X}" for a, _, _ in hooks],
        "limitations": [
            "Uses the stock ordinary kick pose; not a finished Sweet Chin Music animation.",
            "Existing special-hold counter carries a temporary contact marker.",
            "Full match, interruption, AI and multi-opponent behavior require further testing.",
        ],
    }
    return bytes(result), bytes(patch), report


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("rom", type=Path)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()
    rom, patch, report = build(args.rom.read_bytes())
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "shawn-kick-prototype.sfc").write_bytes(rom)
    (args.output / "shawn-kick-prototype.ips").write_bytes(patch)
    (args.output / "patch-report.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
