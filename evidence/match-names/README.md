# In-match wrestler names

The edited test ROM says Scott Hall in its bio but still says Razor Ramon above
its health bar. [Before/after captures](game-comparison.png) show the same native
match setup. [Scott Hall in live gameplay](scott-hall-in-game.png) shows the fixed
label without a pause overlay. These are Snes9x game captures, not editor mockups.

The original health-bar labels are pre-rendered 64 × 8 strips in a shared 4bpp
HUD block at file offset `2ACE03`. Twelve eight-byte tile lists start at `1A4451`;
their pointer directory starts at `1A44B9`. CPU `AFE5CE` selects the label list;
`AFEC24` copies the selected tiles into the HUD buffer. There is also a thirteenth
placeholder list, which is preserved.

The editor generates labels from the bio name, or lets a user enter a shorter
**In-match name**. Stock labels are reproduced exactly. Most new lettering is
extracted from the user's ROM; F, J, P, Q and unused digits use matching five-row
forms. New labels must fit 64 pixels. Undo, reset, project files and direct edited
ROM loading preserve the label state.

The HUD block moves to `3A0000`; load operands at `19EE49` and `19EE4C` select it.
Name tiles are deduplicated into slots 64–134 and 237–255. Health bars, digits,
other HUD graphics and the placeholder label retain their original decoded bytes.
The original compressed atlas remains available for native lettering and restore.
No game pixel data is bundled in the editor.

`verify_match_names.py` checks all 12 labels, stock name preservation, width
refusal, undo, projects, direct edited-ROM reopening and this user's Scott Hall
bio synchronization. `verify_native_match_names.py` enters each stock selection
and checks the 256-byte drawing buffer against the exported label. All twelve
passed; see [verification](verification.json).

Reproduce with local files:

```sh
python3 tools/verify_match_names.py "$WWF_RAW_ROM" --edited-rom "$WWF_EDITED_ROM" --output outputs/name-check
python3 tools/verify_native_match_names.py "$WWF_CORE" outputs/name-check/all-12-names.sfc "$WWF_CAPTURE_ROOT" --output outputs/native-name-check
```

The native captures use existing settled selection save states, followed by A at
100, Start at 300 and A at 500. Raw ROMs, save states and memory stay local.
