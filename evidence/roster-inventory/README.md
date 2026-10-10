# Primary roster directory inventory

This is a structural inventory of the verified original WWF Raw USA ROM, not a completed animation map. Thirteen selectors resolve to twelve distinct directories; selectors 8 and 12 alias the same directory. All twelve selectable wrestler identities are now confirmed by selection-screen names, match names, actor directory values and native primary frame references. Selector 12 aliases selector 8; no separate selectable character is assigned to it. Selector 8 (Shawn Michaels) also supplies the observed common fallback.

Every directory parsed across the 527-entry range established for Bret. The range is provisional for other selectors; successful parsing does not prove their runtime limits, full animation coverage. Lower-body directories remain unexamined. Shared counts below compare exact frame pointers, not all shared graphics.

| Selectors | File offset | Examined entries | Distinct frames | Frames shared with other directories |
| --- | --- | ---: | ---: | ---: |
| 0 | 2CB946 | 527 | 523 | 88 |
| 1 | 2D6FE4 | 527 | 526 | 124 |
| 2 | 008745 | 527 | 524 | 66 |
| 3 | 1D953E | 527 | 521 | 77 |
| 4 | 006BBB | 527 | 521 | 58 |
| 5 | 19BDA9 | 527 | 521 | 82 |
| 6 | 2F6FCD | 527 | 524 | 73 |
| 7 | 196BAE | 527 | 520 | 64 |
| 8, 12 | 2FABBF | 527 | 524 | 102 |
| 9 | 03EC1E | 527 | 526 | 112 |
| 10 | 2B6FD9 | 527 | 526 | 115 |
| 11 | 2C6FB9 | 527 | 526 | 106 |

Bret reproduces the existing inventory: 527 entries, 526 distinct descriptions and 5,470 distinct tile IDs. No ROM bytes or extracted frame descriptions are published; the detailed inventory stays in ignored local outputs.

Reproduce with your original ROM:

```sh
python3 tools/inventory_roster.py "$WWF_RAW_ROM" --output outputs/roster-primary-inventory.json --summary outputs/roster-summary.json
```

Next: inventory lower/common parts and connect frame references to actual actions.

## Verified character identities

| Wrestler | Selector | Native primary tile references checked |
| --- | ---: | ---: |
| Bret Hart | 1 | 122 |
| Undertaker | 2 | 116 |
| Yokozuna | 3 | 205 |
| Bam Bam Bigelow | 4 | 123 |
| Razor Ramon | 5 | 136 |
| Lex Luger | 6 | 108 |
| Doink | 7 | 186 |
| Shawn Michaels | 8 | 89 |
| 1-2-3 Kid | 9 | 107 |
| Diesel | 10 | 191 |
| Owen Hart | 11 | 104 |
| Luna Vachon | 0 | 74 |

[Selection screens](selection-screens.png) and [match screenshots](match-screens.png) show the original game. The match captures are paused to hold the final scene; they do not demonstrate complete move coverage.

The lookup code at CPU 80:EC80–80:ECD0 loads the per-actor word from WRAM 0B74 + actor offset, then indexes the base and bank tables at AD:D513 and AD:D52D. Values are twice the selector. Part IDs at or above 062D use table offset 0010 (selector 8).

Reproduction: cold boot through the documented match menus, stop at the wrestler selector without choosing, and wait for the portrait to settle. From Bret, press Right for eight frames every 300 frames to cycle all twelve choices. Save each settled selection state. Reload each and press A at frame 100, Start at 300, A at 500, Start at 700 and Start at 830; capture frame 1200 with native tracing enabled. The last Start pauses the match. Check the left-side match name against the selected portrait. Run `tools/verify_roster_identities.py ROM TRACE_ROOT --output outputs/roster-identities.json` to check the recorded actor values and all primary descriptor field/tile-ID pairs against the inventory. Raw memory and save states remain local.
