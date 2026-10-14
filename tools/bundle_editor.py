"""Package the static editor into one HTML file, without embedding ROM assets."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
editor = root / 'editor'
html = (editor / 'index.html').read_text()
import re
# Inline every local script referenced by index.html, in page order.
for filename in re.findall(r'<script src="([^"/]+\.js)"></script>', html):
    script = (editor / filename).read_text().replace('</script', '<\\/script')
    html = html.replace(f'<script src="{filename}"></script>', f'<script>\n{script}\n</script>')
html = html.replace('../docs/editor-roadmap.md', 'https://github.com/yourpalbones/WWF-Raw-Mod/blob/main/docs/editor-roadmap.md')
(editor / 'gear-workshop.html').write_text(html)
print('Wrote editor/gear-workshop.html; no ROM or tile bytes embedded')
