"""Forward Royal graphics commands, including the interleaved wrap boundary."""
import sys
import os
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from royal_graphics import decode_block, portrait


def block(length, mode, stream):
    return bytes(2) + (length - 1).to_bytes(2, 'little') + bytes([mode]) + bytes(stream)


class RoyalGraphicsTests(unittest.TestCase):
    def test_literal_and_terminator(self):
        data = block(4, 0, [15, 10, 20, 30, 40, 0, 0])
        output, report = decode_block(data, 0)
        self.assertEqual(output, bytes([10, 20, 30, 40]))
        self.assertEqual(report['compressed_size'], len(data))

    def test_constant_and_incrementing_runs(self):
        data = block(8, 1, [0, 7, 131, 254, 195, 0, 0])
        self.assertEqual(decode_block(data, 0)[0], bytes([7]*4 + [254, 255, 0, 1]))

    def test_overlapping_backreference(self):
        data = block(8, 0, [3, 10, 20, 2, 3, 0, 0])
        self.assertEqual(decode_block(data, 0)[0], bytes([10, 20]*4))

    def test_interleaved_backreference_wraps_to_odd_lane(self):
        # Four literal even bytes; a distance-one copy crosses into the odd lane.
        data = block(8, 2, [15, 1, 2, 3, 4, 1, 1, 0, 0])
        self.assertEqual(decode_block(data, 0)[0], bytes([1, 4, 2, 4, 3, 4, 4, 4]))

    def test_incomplete_and_uninitialized_output_are_rejected(self):
        for stream in ([0, 0, 0], [0, 1, 0, 0, 0]):
            with self.subTest(stream=stream), self.assertRaises(ValueError):
                decode_block(block(4, 0, stream), 0)


    def test_truncation_and_overflow_are_rejected(self):
        for stream in ([1], [0, 9, 132, 0, 0]):
            with self.subTest(stream=stream), self.assertRaises(ValueError):
                decode_block(block(4, 0, stream), 0)


@unittest.skipUnless(os.environ.get('WWF_ROYAL_ROM') and os.environ.get('WWF_ROYAL_PHOTO'),
                     'Set WWF_ROYAL_ROM and WWF_ROYAL_PHOTO to validate native photo snapshots')
class NativeRoyalPhotoTests(unittest.TestCase):
    def test_forward_stream_and_photo_match_native_memory_and_video(self):
        from PIL import Image
        rom = Path(os.environ['WWF_ROYAL_ROM']).read_bytes()
        prefix = os.environ['WWF_ROYAL_PHOTO']
        graphics, _ = decode_block(rom, 0x32e08)
        vram = Path(prefix+'-vram.bin').read_bytes()
        wram = Path(prefix+'-wram.bin').read_bytes()
        self.assertEqual(graphics, vram[0x4000:0x4000+len(graphics)])
        self.assertEqual(graphics, wram[0x2000:0x2000+len(graphics)])
        native = Image.open(prefix+'.png').convert('RGB').crop((24,39,152,159))
        self.assertEqual(portrait(rom, 1, dim=True, native_rgb565=True).tobytes(), native.tobytes())



if __name__ == '__main__':
    unittest.main()
