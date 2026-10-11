# Thirteenth roster-slot probe

A temporary thirteenth profile is selectable and enters a native match.
[Selection capture](selection-slot13.png) shows a duplicated Bret profile at
menu index **12**; the stock menu's indices are 0–11.
[Match capture](match-slot13.png) shows its placeholder **?? MYSTERY ??** label.
The actor has directory value 24 (selector 12), and movement reads the directory
that aliases Shawn's selector 8. This demonstrates an additional selectable slot,
not a completed independent wrestler. The probe is not enabled in the editor.

| Dependency | Observed structure / result |
| --- | --- |
| Menu cursor bounds | CPU `99D43E` compares with 12; reverse wrap loads 11 |
| Profile records | 12 × 45 bytes at ROM `2EFAF5` |
| Profile addressing | CPU `AAFDDB` multiplies index by 45 and selects bank AE |
| Attribute initialization | CPU `AAFEBC`, 12 iterations; 13-entry WRAM arrays reserve a fallback |
| Primary graphics directory | 13 entries at `2DD513` / `2DD52D`; selector 12 aliases 8 |
| Secondary graphics directory | 13 entries at `2DD547` / `2DD561`; must be assigned deliberately |
| Health-bar name | A thirteenth placeholder list already exists |
| Small monitor directories | Twelve entries; the probe reads past their ends |
| Moves, finishers, Mega Moves, AI and match variants | Not verified for the extra slot |

The probe moves the profile table to `3B8000`, copies the twelve records, appends
a duplicate Bret record, redirects profile addressing and the four stock attribute
read addresses, and changes the two manual cursor bounds. It leaves the stock
attribute-loop count and reserved fallback untouched. [Verification](verification.json)
confirms the menu index, match actor ID and native movement directory reads.

The initial 950-frame observation was still loading; later captures at 1,200
and 1,800 frames prove the match starts. There is no demonstrated match-start
crash. Extending the menu without redirecting the twelve-entry small-monitor
arrays makes the announcer screen fetch unrelated ROM data as an image. That
needs fixing before treating the slot as usable.

A complete first added wrestler needs an independent primary/secondary frame
source and palette, profile and monitor references, health-bar name, move and
special assignments, initialized attributes, and validation of random selection,
AI, tag matches and Royal Rumble participant lists. The stock fallback must remain
available. Further slots require growing or relocating the dependent tables and
WRAM arrays rather than overwriting adjacent data.

This is a SNES ROM experiment. If the full expansion succeeds within the SNES
engine and memory limits, it will continue to run in SNES emulators. Cross-game
sprite imports still require verified conversion and complete animation coverage.

Reproduce locally:

```sh
python3 tools/build_roster_expansion_probe.py "$WWF_RAW_ROM" --output outputs/slot13
WWF_TRACE_DIR="$PWD/outputs/slot13-selection" python3 tools/run_headless.py "$WWF_CORE" outputs/slot13/13-slot-menu-probe.sfc --output outputs/slot13-selection --load-state "$WWF_CAPTURE_ROOT/roster-menu-cycle-settled/frame-003000.state" --frames 350 --interval 350 --press 1:7
```

For a match, start from that same stock Owen selection state, press Right at 1,
A at 100, Start at 300, A at 500, Start at 700 and 830, then pause at 1150 and
capture at 1200. Check WRAM `0B74` equals 24 and primary part events select table
byte offset 24. The optional `WWF_LIMIT_PROBE=1` logs comparisons with 11/12/22/24.
Only screenshots, addresses, scripts and verification metadata are published;
ROMs, save states and memory dumps stay local.
