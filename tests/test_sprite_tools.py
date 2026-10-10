import json
import os
from pathlib import Path
import random
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from decode_sprite_tile import decode_sprite_tile, encode_sprite_tile
from extract_oam import assemble, objects


class SpriteCodecTests(unittest.TestCase):
    def test_mask_order_and_output_byte_order(self):
        packet = bytes.fromhex("42 18 84 21 01 02 03 04 05 06 07 08")
        expected = bytes(
            [
                0,
                1,
                0,
                0,
                0,
                0,
                2,
                0,
                0,
                0,
                0,
                3,
                4,
                0,
                0,
                0,
                5,
                0,
                0,
                0,
                0,
                6,
                0,
                0,
                0,
                0,
                7,
                0,
                0,
                0,
                0,
                8,
            ]
        )
        result, consumed = decode_sprite_tile(packet, 0)
        self.assertEqual(result, expected)
        self.assertEqual(consumed, 12)
        self.assertEqual(encode_sprite_tile(expected), packet)

    def test_blank_and_full_tiles(self):
        self.assertEqual(decode_sprite_tile(bytes(4), 0), (bytes(32), 4))
        pixels = bytes(range(1, 33))
        self.assertEqual(encode_sprite_tile(pixels), bytes([255] * 4) + pixels)
        self.assertEqual(decode_sprite_tile(bytes([255] * 4) + pixels, 0), (pixels, 36))

    def test_roundtrip_sparse_tiles(self):
        rng = random.Random(65816)
        for case in range(100):
            tile = bytes(
                0 if rng.random() < 0.6 else rng.randrange(1, 256) for _ in range(32)
            )
            encoded = encode_sprite_tile(tile)
            with self.subTest(case=case):
                self.assertEqual(decode_sprite_tile(encoded, 0), (tile, len(encoded)))

    def test_rejects_invalid_input(self):
        for packet in (b"", b"\xff\xff\xff\xff", b"\x10\x00\x00\x00"):
            with self.subTest(packet=packet), self.assertRaises(ValueError):
                decode_sprite_tile(packet, 0)
        with self.assertRaises(ValueError):
            encode_sprite_tile(bytes(31))


class OAMTests(unittest.TestCase):
    def inputs(self):
        vram = bytearray(65536)
        oam = bytearray(544)
        palette = bytearray(512)
        for index, color in enumerate([0x001F, 0x03E0, 0x7C00, 0x7FFF], 1):
            palette[(128 + index) * 2 : (128 + index) * 2 + 2] = color.to_bytes(
                2, "little"
            )
        # Four constant-color 4bpp tiles in a 16x16 object: red, green, blue, white.
        for number, color in [(0, 1), (1, 2), (16, 3), (17, 4)]:
            for plane in range(4):
                for row in range(8):
                    vram[number * 32 + (plane // 2) * 16 + row * 2 + plane % 2] = (
                        255 if color & (1 << plane) else 0
                    )
        oam[:4] = bytes([4, 5, 0, 0])
        oam[512] = 2
        return vram, oam, palette

    def test_multitile_object_placement_and_palette(self):
        data = self.inputs()
        result, box = assemble(objects(*data, 0), [0])
        self.assertEqual(box, (4, 5, 20, 21))
        self.assertEqual(result.getpixel((0, 0)), (255, 0, 0, 255))
        self.assertEqual(result.getpixel((15, 0)), (0, 255, 0, 255))
        self.assertEqual(result.getpixel((0, 15)), (0, 0, 255, 255))
        self.assertEqual(result.getpixel((15, 15)), (255, 255, 255, 255))

    def test_flips_apply_to_entire_object(self):
        vram, oam, palette = self.inputs()
        oam[3] = 0xC0
        result, _ = assemble(objects(vram, oam, palette, 0), [0])
        self.assertEqual(result.getpixel((0, 0)), (255, 255, 255, 255))
        self.assertEqual(result.getpixel((15, 15)), (255, 0, 0, 255))

    def test_object_name_bit_selects_second_tile_page(self):
        vram, oam, palette = self.inputs()
        vram[8192 : 8192 + 32] = vram[:32]
        vram[:32] = bytes(32)
        oam[3] = 1
        oam[512] = 0
        result, _ = assemble(objects(vram, oam, palette, 0), [0])
        self.assertEqual(result.size, (8, 8))
        self.assertEqual(result.getpixel((0, 0)), (255, 0, 0, 255))

    def test_rejects_bad_snapshot_sizes(self):
        with self.assertRaises(ValueError):
            objects(bytes(1), bytes(544), bytes(512), 0)


@unittest.skipUnless(
    os.environ.get("WWF_RAW_ROM") and os.environ.get("WWF_RAW_TRACE"),
    "Set WWF_RAW_ROM and WWF_RAW_TRACE to validate live tile snapshots",
)
class LiveTileTests(unittest.TestCase):
    def test_matches_live_game_memory_and_original_encoding(self):
        rom = Path(os.environ["WWF_RAW_ROM"]).read_bytes()
        if len(rom) % 1024 == 512:
            rom = rom[512:]
        root = Path(os.environ["WWF_RAW_TRACE"])
        entries = [
            json.loads(line) for line in (root / "tiles.jsonl").read_text().splitlines()
        ]
        self.assertGreater(len(entries), 0)
        for entry in entries:
            with self.subTest(event=entry["event"]):
                source = entry["source"]
                offset = source & 0x3FFFFF
                decoded, size = decode_sprite_tile(rom, offset)
                original_output = (
                    root / "assets" / f"tile-{entry['event']:06d}-{source:06x}.bin"
                ).read_bytes()
                self.assertEqual(decoded, original_output)
                self.assertEqual(
                    encode_sprite_tile(decoded), rom[offset : offset + size]
                )


if __name__ == "__main__":
    unittest.main()
