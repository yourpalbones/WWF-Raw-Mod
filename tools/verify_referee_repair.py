"""Verify that exporting an existing v0.16 mod repairs NPC palettes only."""
import argparse
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('rom',type=Path)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
root=Path(__file__).resolve().parents[1]
args.output.mkdir(parents=True,exist_ok=True)
original=args.rom.read_bytes()
assert original[0x2cf212:0x2cf214]==bytes.fromhex('00 84')
server=ThreadingHTTPServer(('127.0.0.1',0),partial(SimpleHTTPRequestHandler,directory=str(root)))
threading.Thread(target=server.serve_forever,daemon=True).start()
with sync_playwright()as playwright:
    browser=playwright.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
    page=browser.new_page()
    page.goto(f'http://127.0.0.1:{server.server_port}/editor/gear-workshop.html')
    page.locator('#rom').set_input_files(str(args.rom.resolve()))
    page.wait_for_function('rom!==null&&C.characters.length===13')
    snapshot='Object.fromEntries(C.characters.map(c=>[c.id,{profile:selectionState(c.id),assets:profileState(c.id),palette:Array.from(rom.slice(c.palette_offset,c.palette_offset+32))}]))'
    before=page.evaluate(snapshot)
    page.locator('#tab-export').click()
    with page.expect_download()as download:page.locator('#rom-export').click()
    repaired=args.output/'referee-repaired.sfc'
    download.value.save_as(repaired)
    data=repaired.read_bytes()
    assert data[0x2cf212:0x2cf214]==bytes.fromhex('00 e8')
    assert data[0x70e800:0x70e9e0]==original[0x708400:0x7085e0]
    assert data[0x70e9e0:0x70ea60]==original[0x2cc67a:0x2cc6fa]
    # Older imports also copied the announcer bank tables with a one-byte stride (matches stalled on the
    # announcer screen); export rebuilds all four tables from the profile records.
    for target,field,bank in [(0x70e400,20,False),(0x70e420,20,True),(0x70e440,24,False),(0x70e460,24,True)]:
        for i in range(13):
            pointer=int.from_bytes(data[0x708000+i*45+field:0x708000+i*45+field+3],'little')
            assert int.from_bytes(data[target+i*2:target+i*2+2],'little')==(pointer>>16 if bank else pointer&65535),(hex(target),i)
    allowed=[(0x2cf212,0x2cf214),(0x70e800,0x70ea60),(0x70e400,0x70e480),(0xffdc,0xffe0),(0x40ffdc,0x40ffe0)]
    for offset,(a,b)in enumerate(zip(original,data)):
        if a!=b:assert any(start<=offset<end for start,end in allowed),hex(offset)
    page.locator('#rom').set_input_files(str(repaired.resolve()))
    page.wait_for_function('rom!==null&&C.characters.length===13')
    assert page.evaluate(snapshot)==before
    with page.expect_download()as download:page.locator('#rom-export').click()
    assert Path(download.value.path()).read_bytes()==data
    browser.close()
server.shutdown()
print('Legacy NPC palettes and announcer tables repaired; all 13 profiles, palettes and assets preserved; reopen and repeat export stable.')
