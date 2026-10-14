"""Independent packed-tile fixtures and optional native Sega decoder comparison."""
import os
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from genesis_royal_graphics import decode_tile,verify_trace
from genesis_sprite_capture import packed_tile,object_pixels


class GenesisGraphicsTests(unittest.TestCase):
    def test_raw_tile_and_byte_translation(self):
        rom=bytearray(0x200000);rom[0xbe456:0xbe476]=bytes(range(32))
        raw,meta=decode_tile(rom,1,bytes(255-i for i in range(256)))
        self.assertEqual(raw,bytes(255-i for i in range(32)))
        self.assertEqual(meta['family'],'raw')

    def test_byte_mask_family_boundary(self):
        rom=bytearray(0x200000)
        rom[0xbe370:0xbe374]=bytes.fromhex('17d6260b')
        rom[0xbe3b2:0xbe3b6]=(0x120000-0xbe370).to_bytes(4,'big')
        rom[0x120000:0x12001f]=bytes.fromhex('fc000000ab')+bytes(range(26))
        self.assertEqual(decode_tile(rom,0x17d6)[0],b'\xab'*6+bytes(range(26)))

    def test_row_mask_and_solid_boundaries(self):
        rom=bytearray(0x200000)
        rom[0xbe3a2:0xbe3a6]=bytes.fromhex('c73fc9ef')
        rom[0xbe416:0xbe41a]=(0x120000-0xbe370).to_bytes(4,'big')
        rom[0x2336:0x2338]=(30).to_bytes(2,'big')
        rom[0x120000:0x12001e]=b'\xaa\xfe'+bytes(range(28))
        self.assertEqual(decode_tile(rom,0xc73f)[0],bytes(range(28))+b'\xaa'*4)
        rom[0x1fff8a]=0x33
        self.assertEqual(decode_tile(rom,0xd9f7)[0],b'\x33'*32)

    def test_column_major_objects_and_whole_object_flip(self):
        vram=bytearray(65536)
        for i in range(4):vram[i*32:(i+1)*32]=bytes([(i+1)*17])*32
        obj=dict(width=16,height=16,tile=0,hflip=False,vflip=False)
        pixels=object_pixels(vram,obj)
        self.assertEqual([pixels[y*16+x]for x,y in ((0,0),(0,8),(8,0),(8,8))],[1,2,3,4])
        obj['hflip']=obj['vflip']=True
        pixels=object_pixels(vram,obj)
        self.assertEqual([pixels[y*16+x]for x,y in ((0,0),(0,8),(8,0),(8,8))],[4,3,2,1])


@unittest.skipUnless(os.environ.get('WWF_GENESIS_ROM') and os.environ.get('WWF_GENESIS_TRACE'),
                     'Set WWF_GENESIS_ROM and WWF_GENESIS_TRACE for native Sega comparison')
class NativeGenesisTests(unittest.TestCase):
    def test_decoder_matches_observed_native_tiles(self):
        report=verify_trace(Path(os.environ['WWF_GENESIS_ROM']).read_bytes(),Path(os.environ['WWF_GENESIS_TRACE']))
        self.assertTrue(report['native_bytes_match'])
        self.assertEqual(set(report['families']),{'raw','byte-mask','row-mask','solid'})


if __name__=='__main__':unittest.main()
