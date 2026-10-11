# Gear editor: all 12 wrestlers

![The editor running with original Shawn Michaels sprites](../evidence/roster-editor/workshop.png)

## Try it

1. Open [gear-workshop.html](gear-workshop.html) on GitHub and click **Download raw file**.
2. Open that downloaded file in Chrome, Edge or Firefox.
3. Click **Open your original USA ROM** and choose your unmodified WWF Raw ROM.
4. Choose a wrestler, then select a color and paint directly on their sprite.
   To recolor a palette slot, use **Change color**.
5. Use **Save project** to keep editable work, or **Export IPS patch** to apply
   your changes to an unheadered copy of the original ROM.

The ROM stays on your computer. This repository contains layout addresses and
original-game capture evidence, not a ROM or extracted tile library.

## Available previews

| Wrestler | Captured poses |
| --- | ---: |
| Bret Hart | 15 |
| Undertaker | 10 |
| Yokozuna | 7 |
| Bam Bam Bigelow | 4 |
| Razor Ramon | 3 |
| Lex Luger | 11 |
| Doink | 8 |
| Shawn Michaels | 10 |
| 1-2-3 Kid | 10 |
| Diesel | 10 |
| Owen Hart | 8 |
| Luna Vachon | 6 |

These 102 sampled layouts use native positions, palettes and flips. Bret retains
his previous standing/walking set; the other characters use captured movement
sequences that may include opponent interactions. Counts describe sampled poses,
not every animation. **Play poses** cycles samples at a fixed preview speed,
rather than reproducing native animation timing.

## Editing behavior

- Paint with 15 visible palette slots, or select a slot and choose a new color.
  Colors snap to SNES 5-bit RGB. Transparency remains locked.
- The usage count reports visible pixels in the current pose. Palette changes
  recolor all uses of that slot, including skin or hair sharing it.
- Tile edits follow the same ROM source across loaded poses and wrestlers.
  The editor names other loaded wrestlers using an edited shared source.
  Shared users outside these captures remain unverified.
- Switching wrestlers retains your edits. Export includes all edited wrestlers.
- Undo covers tile and palette edits across the roster. **Reset all edits** clears
  the entire project. Save/load projects and native-resolution PNGs are supported.
- Version 3 projects store the full roster. Existing version 1/2 Bret projects
  remain supported; their palette edits always belong to Bret.
- Export validates the original USA ROM hash, accepts an optional copier header,
  uses native sparse compression and updates the HiROM checksum. Compressed
  edits exceeding their original allocations are refused.

Full action coverage, palette ownership outside the verified captures, tile
relocation, automatic shared-asset isolation and an embedded emulator remain
future work. Test edited patches through the rest of the moves in an emulator.
Original sprite work is retained, including Shawn's original look.

## Developer validation

The editor needs only a browser. Optional automated verification needs Python,
Pillow, Playwright and Chromium, a local original ROM, the earlier research
captures and the new movement captures:

```sh
python3 tools/verify_editor.py '/path/to/WWF Raw (USA).sfc' \
  --capture-root /path/to/raw-analysis \
  --movement-root outputs/editor-roster-live \
  --chromium /usr/bin/chromium --page gear-workshop.html
```

This compares all 102 browser previews against native OAM extraction, checks
2,174 source tiles re-encode byte for byte, exercises editing and export for all
12 wrestlers, validates roster/legacy projects and shared-source warnings, and
checks invalid palette and compression overflow refusal. Private test ROMs and
screenshots are written under ignored `outputs/`.

See [roster evidence and reproduction](../evidence/roster-editor/README.md).
Regenerate the address-only manifest using `tools/build_roster_editor.py`, then
rebuild the standalone download with `python3 tools/bundle_editor.py`.
