# WrestleEdit — Roster 16 preview

A separate Windows editor for the expanded roster. Claude's editor and Perfect-Plex source files are unchanged; `source.json` pins the reviewed source snapshot used by this application.

- Open original, edited, or prepared sixteen-slot Raw ROMs.
- Browse and paint the imported Hogan, Boss Man and Flair poses; edit their palettes.
- Edit portraits, small monitor photos, bios, selection logos, match names and themes.
- Save projects and playable ROMs, then reopen the exported sixteen-slot ROM.
- Added wrestlers have separate tile directories and protected editing/music pools.

This is an editor preview, not a completed v0.1 game release. The Figure Four, Boss Man's finisher, complete imported animation coverage and expanded match-mode verification remain unfinished. It opens the prepared sixteen-slot build; it does not automatically import all three new workers into an arbitrary ROM. Reference-gear rebuilds are disabled on sixteen-slot ROMs to protect the new allocations. Manual sprite/PNG editing is supported.

Build the standalone, ROM-free HTML:

```sh
# Fetch the source.json commit if it is absent from a fresh clone.
python tools/bundle_roster16_editor.py
```

Windows packaging uses the existing checksum-verified official Electron runtime:

```sh
python tools/package_roster16_desktop.py
```

Relevant functional checks (all ROMs/fixtures stay private):

```sh
python tools/check_roster16_editor.py private-16-slot.sfc --output /tmp/editor-check --midi private.mid
python tools/check_roster16_native_preview.py private-edited.sfc /tmp/native-capture --output /tmp/pixel-report.json
```

The first check uses Chromium/Playwright and exercises real controls and downloads. The second compares the actual editor canvas with native OBJ/VRAM/CGRAM snapshots. It checks observed body pixels and colors, not every move or the background.
