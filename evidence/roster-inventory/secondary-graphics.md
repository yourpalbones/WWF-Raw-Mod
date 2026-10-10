# Secondary graphics directory inventory

The game has a second per-character frame-directory table, selected at CPU 80:ED10–80:ED39 from tables AD:D547 (base) and AD:D561 (bank). The code masks part IDs with 7FFF, uses the character selector below 04FE, and switches to selector 8 at or above 04FE. The same actor selector identifies the primary and secondary directories.

We inventoried the 426 three-byte entries below 04FE for all twelve distinct secondary directories. Selector 12 aliases selector 8 here too. The parser records frame descriptors and tile references, then resolves and decodes their raw/sparse sources using the secondary dictionary: raw threshold 1FFF, bank DD, base A880, packed-directory base 027C.

**1,991 observed player secondary frame references** across twelve original-game matches matched both the selected directory fields and the native source lookup. No references were missing in this captured set. This does not establish complete animation coverage, anatomical labels for every piece, or the size/contents of the fallback range above 04FE.

| Wrestler | Selector | Distinct frame descriptions | Distinct tile sources | Sources also referenced by other secondary directories | Native references checked |
| --- | ---: | ---: | ---: | ---: | ---: |
| Luna Vachon | 0 | 425 | 4538 | 785 | 110 |
| Bret Hart | 1 | 425 | 4798 | 4674 | 153 |
| Undertaker | 2 | 425 | 4713 | 2882 | 149 |
| Yokozuna | 3 | 425 | 5035 | 792 | 249 |
| Bam Bam Bigelow | 4 | 424 | 4774 | 1889 | 163 |
| Razor Ramon | 5 | 425 | 4879 | 4075 | 172 |
| Lex Luger | 6 | 425 | 4893 | 4020 | 143 |
| Doink | 7 | 426 | 4909 | 720 | 211 |
| Shawn Michaels | 8 | 424 | 4745 | 4561 | 106 |
| 1-2-3 Kid | 9 | 424 | 4882 | 1928 | 149 |
| Diesel | 10 | 426 | 4881 | 3549 | 234 |
| Owen Hart | 11 | 425 | 4882 | 3574 | 152 |

## Shared assets and editor implications

Sharing is counted by exact ROM source address across distinct secondary directories, rather than equal-looking pixels. Exact frame-pointer sharing is recorded separately in [the summary](secondary-summary.json). An editor must trace all affected references before treating a source as exclusive to one wrestler. Identical decoded hashes are available in the private inventory for later comparison, but are not counted as shared addresses here.

The twelve capture sets also passed existing decoder validation: **10,479 sparse tile events** matched native output and re-encoded byte for byte; **192 complete interface blocks** matched native output. These totals include both wrestlers and the referee, and both sprite dictionaries; they are not secondary-only counts. Partial interface blocks are separately skipped in [the codec report](codec-verification.json). Unobserved static inventory tiles were decoded but have no native-output comparison.

## Reproduction

Use the twelve original match traces described in [the roster identity evidence](README.md), with their final WRAM snapshots and tile_calls.jsonl files.

```sh
python3 tools/inventory_secondary_frames.py "$WWF_RAW_ROM" /path/to/trace-root --output outputs/roster-secondary-inventory.json --summary outputs/secondary-summary.json
```

The detailed frame descriptors, source lists and decoded hashes remain in ignored local outputs. Only counts, addresses, verification reports and authored tools are published. The original ROM is unchanged.

Next: record action/part requests during controlled gameplay, inventory the actual fallback ranges, and build action-to-frame coverage for every character. Directory discovery alone does not give an editor complete animations.
