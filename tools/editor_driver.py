"""Drive the real browser editor (editor/gear-workshop.html) headlessly with Playwright.

Subcommands:
  import RAW ROYAL --output OUT       Add Mr. Perfect exactly as a user would (Add Mr. Perfect button).
  resave ROM --output OUT             Open an edited ROM and use "Save playable ROM".
  update ROM ROYAL --output OUT       Open an earlier import and use "Update Perfect-Plex".
  edit-receiver ROM --slot N --pose I --output OUT
                                      Paint a stroke on one worker's "Receiving Perfect-Plex" pose with the
                                      mouse, save, and report the edited tile sources (for isolation checks).

Every result is the file the editor downloads. ROMs stay local.

    python3 -m pip install playwright
    python3 tools/editor_driver.py import RAW.sfc ROYAL.sfc --output OUT.sfc
"""
import argparse
import threading
from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


@contextmanager
def editor(page_path='editor/gear-workshop.html'):
    from playwright.sync_api import sync_playwright
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(Quiet, directory=str(ROOT)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch(headless=True, args=['--no-sandbox'])
        except Exception:
            # Cloud containers ship a fixed Chromium (PLAYWRIGHT_BROWSERS_PATH); use it directly.
            browser = playwright.chromium.launch(executable_path='/opt/pw-browsers/chromium', headless=True,
                                                 args=['--no-sandbox'])
        page = browser.new_page(viewport={'width': 1440, 'height': 1000})
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(f'http://127.0.0.1:{server.server_port}/{page_path}')
        try:
            yield page, errors
        finally:
            browser.close()
            server.shutdown()


def load_rom(page, path):
    page.locator('#rom').set_input_files(str(path))
    page.wait_for_function('rom!==null')


def download(page, button, output):
    with page.expect_download() as info:
        page.locator(button).click()
    info.value.save_as(output)


def run_import(raw, royal, output):
    with editor() as (page, errors):
        load_rom(page, raw)
        page.locator('#royal-rom').set_input_files(str(royal))
        page.wait_for_function('royalSource!==null')
        download(page, '#royal-add', output)
        page.wait_for_function("C.characters.length===13")
        return {'status': page.locator('#royal-status').text_content(), 'errors': errors}


def run_resave(rom, output):
    with editor() as (page, errors):
        load_rom(page, rom)
        status = page.locator('#royal-status').text_content()
        page.locator('#tab-export').click()
        download(page, '#rom-export', output)
        return {'status_before_save': status, 'errors': errors}


def run_update(rom, royal, output):
    with editor() as (page, errors):
        load_rom(page, rom)
        page.locator('#royal-rom').set_input_files(str(royal))
        page.wait_for_function('royalSource!==null')
        before = page.locator('#royal-status').text_content()
        download(page, '#royal-update', output)
        page.wait_for_function("!document.querySelector('#royal-status').textContent.startsWith('Updating')", timeout=60000)
        return {'status_before': before, 'status': page.locator('#royal-status').text_content(), 'errors': errors}


def run_edit_receiver(rom, slot, pose, output, length=6):
    with editor() as (page, errors):
        load_rom(page, rom)
        page.locator('#wrestler').select_option(str(slot))
        index = page.evaluate("label=>M.poses.findIndex(p=>p.label===label)", f'Receiving Perfect-Plex · {pose}')
        if index < 0:
            raise SystemExit('No receiving pose in this ROM for that slot')
        page.locator('#pose').select_option(str(index))
        # Choose an opaque row and a colour unlike the pixels it covers, then draw it with the mouse.
        target = page.evaluate("""n=>{const w=canvas.width;for(let y=Math.floor(canvas.height/3);y<canvas.height;y++)
            for(let x=0;x+n<=w;x++){const run=cells.slice(y*w+x,y*w+x+n);if(run.length===n&&run.every(Boolean))return {x,y,w,h:canvas.height};}
            return null;}""", length)
        colour = page.evaluate("""t=>{const used=new Set();for(let i=0;i<%d;i++){const c=cells[t.y*t.w+t.x+i];used.add(pixels(c.key)[c.index]);}
            for(let v=15;v>0;v--)if(!used.has(v))return v;return 1;}""" % length, target)
        page.evaluate('v=>{selected=v;}', colour)
        box = page.locator('#sprite').bounding_box()
        sx, sy = box['width'] / target['w'], box['height'] / target['h']
        page.mouse.move(box['x'] + (target['x'] + .5) * sx, box['y'] + (target['y'] + .5) * sy)
        page.mouse.down()
        for i in range(length):
            page.mouse.move(box['x'] + (target['x'] + i + .5) * sx, box['y'] + (target['y'] + .5) * sy)
        page.mouse.up()
        edited = page.evaluate("Object.keys(edits).map(k=>({key:k,...C.sources[k]}))")
        page.locator('#tab-export').click()
        download(page, '#rom-export', output)
        return {'pose_index': index, 'colour': colour, 'edited': edited, 'errors': errors}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)
    a = sub.add_parser('import'); a.add_argument('raw', type=Path); a.add_argument('royal', type=Path)
    a.add_argument('--output', type=Path, required=True)
    b = sub.add_parser('resave'); b.add_argument('rom', type=Path); b.add_argument('--output', type=Path, required=True)
    c = sub.add_parser('update'); c.add_argument('rom', type=Path); c.add_argument('royal', type=Path)
    c.add_argument('--output', type=Path, required=True)
    e = sub.add_parser('edit-receiver'); e.add_argument('rom', type=Path); e.add_argument('--slot', type=int, required=True)
    e.add_argument('--pose', type=int, required=True); e.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'import':
        result = run_import(args.raw, args.royal, args.output)
    elif args.command == 'resave':
        result = run_resave(args.rom, args.output)
    elif args.command == 'update':
        result = run_update(args.rom, args.royal, args.output)
    else:
        result = run_edit_receiver(args.rom, args.slot, args.pose, args.output)
    print(result)
    if result['errors']:
        raise SystemExit('Page errors: ' + '; '.join(result['errors']))
