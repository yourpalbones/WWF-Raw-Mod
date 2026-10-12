"""Package the static editor into one HTML file, without embedding ROM assets."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
editor = root / 'editor'
html = (editor / 'index.html').read_text()
for filename in ('roster-layouts.js', 'scott-layouts.js', 'nwo-gear-patterns.js','nash-layouts.js','syxx-layouts.js', 'selection-layouts.js', 'editor.js', 'selection.js', 'profile-assets.js', 'match-names.js', 'custom-music.js', 'scott-sprites.js', 'app.js'):
    script = (editor / filename).read_text().replace('</script', '<\\/script')
    html = html.replace(f'<script src="{filename}"></script>', f'<script>\n{script}\n</script>')
html = html.replace('../docs/editor-roadmap.md', 'https://github.com/yourpalbones/WWF-Raw-Mod/blob/main/docs/editor-roadmap.md')
(editor / 'gear-workshop.html').write_text(html)
print('Wrote editor/gear-workshop.html; no ROM or tile bytes embedded')
