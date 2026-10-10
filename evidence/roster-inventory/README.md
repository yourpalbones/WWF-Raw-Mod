# Primary roster directory inventory

This is a structural inventory of the verified original WWF Raw USA ROM, not a completed animation map. Thirteen selectors resolve to twelve distinct directories; selectors 8 and 12 alias the same directory. Only selector 1 is assigned a confirmed wrestler name here (Bret Hart). Selector 8 is the observed common fallback. Other identities require gameplay tracing.

Every directory parsed across the 527-entry range established for Bret. The range is provisional for other selectors; successful parsing does not prove their runtime limits, character identity or full animation coverage. Lower-body directories remain unexamined. Shared counts below compare exact frame pointers, not all shared graphics.

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

Next: trace character selection to directory selectors, then inventory lower/common parts and connect frame references to actual actions.
