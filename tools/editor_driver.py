"""Drive the real browser editor (editor/gear-workshop.html) headlessly with Playwright.

Subcommands:
  import RAW ROYAL --output OUT       Add Mr. Perfect exactly as a user would (Add Mr. Perfect button).
  resave ROM --output OUT             Open an edited ROM and use "Save playable ROM".

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


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)
    a = sub.add_parser('import'); a.add_argument('raw', type=Path); a.add_argument('royal', type=Path)
    a.add_argument('--output', type=Path, required=True)
    b = sub.add_parser('resave'); b.add_argument('rom', type=Path); b.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = run_import(args.raw, args.royal, args.output) if args.command == 'import' else run_resave(args.rom, args.output)
    print(result)
    if result['errors']:
        raise SystemExit('Page errors: ' + '; '.join(result['errors']))
