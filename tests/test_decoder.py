"""Codec checks using original ROM code locally, plus ROM-free safety tests."""

import os
from pathlib import Path
import random
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from decode_graphics import DecodeError, decode_mode1, decode_mode2
from decoder_reference import reference_decode

ROM_PATH = os.environ.get("WWF_RAW_ROM")


def block(length, commands):
    return length.to_bytes(2, "little") + b"\x02" + commands + b"\x00"


class SafetyTests(unittest.TestCase):
    def test_literal_and_descending_run(self):
        stream = block(12, bytes([0x45, 1, 2, 3, 4, 5, 6, 0x23, 0x25]))
        decoded, stats = decode_mode2(stream, 0)
        expected = bytes(
            v for pair in zip(range(0x20, 0x26), range(1, 7)) for v in pair
        )
        self.assertEqual(decoded, expected)
        self.assertEqual(stats["compressed_size"], len(stream))

    def test_overlapping_backreference(self):
        stream = block(12, bytes([0x41, 0xAA, 0xBB, 0x88, 0, 0x45, 1, 2, 3, 4, 5, 6]))
        decoded, _ = decode_mode2(stream, 0)
        self.assertEqual(
            decoded, bytes([1, 0xAA, 2, 0xAA, 3, 0xAA, 4, 0xAA, 5, 0xAA, 6, 0xBB])
        )

    def test_rejects_incomplete_output(self):
        with self.assertRaises(DecodeError):
            decode_mode2(block(12, b""), 0)

    def test_rejects_truncated_literal(self):
        with self.assertRaises(DecodeError):
            decode_mode2(b"\x0c\x00\x02\x45", 0)

    def test_rejects_uninitialized_backreference(self):
        with self.assertRaises(DecodeError):
            decode_mode2(block(12, bytes([0x88, 0])), 0)

    def test_mode1_single_byte_reference(self):
        stream = b"\x0c\x00\x01" + bytes([0x45, 1, 2, 3, 4, 5, 6, 0x23, 3, 9, 0])
        self.assertEqual(
            decode_mode1(stream, 0)[0], bytes([9] * 5 + [4, 1, 2, 3, 4, 5, 6])
        )

    def test_mode1_overlapping_reference(self):
        stream = b"\x0c\x00\x01" + bytes([0x41, 0xAA, 0xBB, 0x88, 1, 4, 7, 0])
        self.assertEqual(decode_mode1(stream, 0)[0], bytes([7] * 6 + [0xAA, 0xBB] * 3))

    def test_rejects_unsupported_mode(self):
        with self.assertRaises(DecodeError):
            decode_mode2(b"\x0c\x00\x01", 0)


@unittest.skipUnless(
    ROM_PATH, "Set WWF_RAW_ROM to compare against original decoder instructions"
)
class OriginalCodeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rom = Path(ROM_PATH).read_bytes()
        if len(cls.rom) % 1024 == 512:
            cls.rom = cls.rom[512:]

    def compare(self, rom, offset):
        decoded, _ = decode_mode2(rom, offset)
        original, _ = reference_decode(rom, offset)
        self.assertEqual(decoded, original)
        return decoded

    def synthetic(self, stream):
        # Replace data in an in-memory copy only, preserving the decoder code.
        image = bytearray(self.rom)
        image[0x10000 : 0x10000 + len(stream)] = stream
        return self.compare(image, 0x10000)

    def test_real_graphics_blocks(self):
        for offset in (
            0x1A0000,
            0x1D7D4C,
            0x1D7DD0,
            0x1DA774,
            0x2E9FDD,
            0x2F0000,
            0x2F2399,
        ):
            with self.subTest(offset=hex(offset)):
                self.compare(self.rom, offset)

    def test_mode1_real_blocks(self):
        for offset in (0x19AC80, 0x2ADBE3):
            decoded, _ = decode_mode1(self.rom, offset)
            original, _ = reference_decode(self.rom, offset)
            self.assertEqual(decoded, original)

    def test_all_command_classes(self):
        cases = [
            block(12, bytes([0x45, 1, 2, 3, 4, 5, 6, 0x23, 0x25])),
            block(12, bytes([4, 0x12, 4, 0x34])),
            block(12, bytes([0x41, 0xAA, 0xBB, 0x88, 0, 0x45, 1, 2, 3, 4, 5, 6])),
            # Second-plane backreference wraps into the already decoded first lane.
            block(12, bytes([0x45, 1, 2, 3, 4, 5, 6, 0x98, 5])),
        ]
        for stream in cases:
            with self.subTest(stream=stream.hex()):
                self.synthetic(stream)

    def test_random_literals_and_runs_even_and_odd_lengths(self):
        randomizer = random.Random(65816)
        for case in range(100):
            length = randomizer.randrange(16, 600)
            commands = bytearray()
            for remaining in (length // 2, (length + 1) // 2):
                while remaining:
                    kind = randomizer.randrange(3) if remaining >= 3 else 0
                    count = randomizer.randint(
                        1 if kind == 0 else 3,
                        min(remaining, 64 if kind == 0 else (33 if kind == 1 else 34)),
                    )
                    if kind == 0:
                        commands.append(0x40 | (count - 1))
                        commands.extend(randomizer.randrange(256) for _ in range(count))
                    elif kind == 1:
                        commands.extend([count - 2, randomizer.randrange(256)])
                    else:
                        commands.extend([0x20 | (count - 3), randomizer.randrange(256)])
                    remaining -= count
            with self.subTest(case=case, length=length):
                self.synthetic(block(length, commands))


if __name__ == "__main__":
    unittest.main()
