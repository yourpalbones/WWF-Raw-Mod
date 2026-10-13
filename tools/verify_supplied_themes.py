"""Import prepared Sting/Luger files through the current packaged app offline.

Native expectations and ROMs remain private. The public report contains only
the import/export results; use verify_native_custom_music for playback checks.
"""
import argparse,hashlib,json,threading,zipfile
from pathlib import Path
from functools import partial
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from playwright.sync_api import sync_playwright

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    repo=Path(__file__).resolve().parents[1];out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(repo/'downloads/WrestleEdit.zip')as z:
        assert z.testzip()is None;z.extractall(out/'package')
    server=ThreadingHTTPServer(('127.0.0.1',0),partial(SimpleHTTPRequestHandler,directory=str(out/'package')))
    threading.Thread(target=server.serve_forever,daemon=True).start();errors=[];results=[];expectations=[]
    with sync_playwright()as pw:
        browser=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox']);page=browser.new_page(viewport={'width':1280,'height':1050})
        page.on('pageerror',lambda e:errors.append(str(e)));page.goto(f'http://127.0.0.1:{server.server_port}/WrestleEdit/WrestleEdit.html');page.context.set_offline(True)
        page.locator('#rom').set_input_files(str(a.rom));page.wait_for_function('rom!==null');page.locator('#tab-profile').click()
        for name,id in [('sting','7'),('luger','6')]:
            page.locator('#wrestler').select_option(id);page.locator('#song-instrument').select_option('113');page.locator('#song-transpose').fill('0');page.locator('#song-loop').check()
            path=repo/f'downloads/{name}-snes-ready.mid';page.locator('#song-import').set_input_files(str(path))
            page.wait_for_function("$('song-import').value===''");assert page.evaluate('id=>Boolean(selectionEdits[id]?.song)',id),page.locator('#song-status').inner_text()
            value=page.evaluate('id=>({song:selectionEdits[id].song,compiled:compileSong(selectionEdits[id].song),theme:S.characters[id].theme})',id)
            assert value['song']['instrument']==113 and value['song']['loop'];assert page.locator('#song-status').get_attribute('data-error')is None
            expectations.append({'id':id,'theme':value['theme'],'compiled':value['compiled'],'song':value['song']})
            results.append({'file':path.name,'wrestler_id':int(id),'duration_seconds':value['song']['duration']/50,'native_voices':value['compiled']['voices'],'imported_notes':len(value['song']['notes']),'native_sequence_bytes':value['compiled']['bytes'],'instrument':113,'transpose':0,'loop':True,'import_success':True})
            page.locator('#song-status').scroll_into_view_if_needed();page.screenshot(path=str(out/(name+'-import.png')))
        saved=page.evaluate('JSON.stringify(selectionEdits)')
        with page.expect_download()as d:page.locator('#save').click()
        project=Path(d.value.path()).read_bytes();(out/'themes-project.json').write_bytes(project)
        page.locator('#reset').click();page.locator('#project').set_input_files({'name':'themes.json','mimeType':'application/json','buffer':project})
        page.wait_for_function('selectionEdits["6"]?.song&&selectionEdits["7"]?.song');assert page.evaluate('JSON.stringify(selectionEdits)')==saved
        records=page.evaluate('customMusicRecords().records.map(([o,data])=>[o,data.length])');meta=page.evaluate('Object.entries(S.characters).filter(([id])=>["6","7"].includes(id)).map(([id,c])=>c)')
        page.locator('#tab-export').click()
        with page.expect_download()as d:page.locator('#rom-export').click()
        exported=Path(d.value.path()).read_bytes();base=a.rom.read_bytes();allowed=bytearray(len(base))
        for offset,length in records:allowed[offset:offset+length]=b'\1'*length
        for c in meta:allowed[c['theme_offset']]=1
        for offset in [0xffdc,0x40ffdc]:allowed[offset:offset+4]=b'\1'*4
        assert len(exported)==len(base)==0x800000
        assert all(x==y or allowed[i]for i,(x,y)in enumerate(zip(base,exported))),'An unrelated mod asset changed'
        assert sum(exported)&65535==int.from_bytes(exported[0xffde:0xffe0],'little')
        path=out/'both-themes.sfc';path.write_bytes(exported)
        page.locator('#rom').set_input_files(str(path));page.wait_for_function('rom!==null');assert bytes(page.evaluate('Array.from(playableROM())'))==exported
        assert not errors,errors;browser.close()
    server.shutdown();(out/'native-expectations.json').write_text(json.dumps(expectations,indent=2)+'\n')
    report={'themes':results,'offline_packaged_app':True,'both_songs_project_roundtrip':True,'edited_rom_reopen_byte_exact':True,'existing_graphics_profiles_other_themes_and_samples_preserved':True,'checksum_valid':True,'rom_sha256':hashlib.sha256(exported).hexdigest()}
    (out/'editor-verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
