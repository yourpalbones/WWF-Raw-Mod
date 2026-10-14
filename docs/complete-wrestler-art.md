# Complete wrestler artwork and animation coverage

Task: [`docs/CLAUDE-COMPLETE-WRESTLER-ART-TASK.md`](CLAUDE-COMPLETE-WRESTLER-ART-TASK.md) (`bd31a0b`).
Branch `claude/charming-allen-njttcx`, draft PR #1. This page is the working checklist. Every status
names its evidence. **Nothing here is complete until native gameplay and a visual review confirm it.**

## Prerequisites and references

- **Latest user ROM: not supplied.** Only the stock Raw and Royal Rumble ROMs are available in this
  session. The current identities are rebuilt with the editor's own reference-gear buttons
  (`tools/editor_driver.py apply-gear`, slots 5, 9, 10 and 7):
  - Scott Hall `SCOTT-HALL-GEAR3`
  - Syxx `SYXX-NATIVE-GEAR3`
  - Kevin Nash `NASH-NATIVE-GEAR2`
  - Sting `STING-NATIVE-GEAR4`

  Mr. Perfect is then imported. **Other user edits cannot be checked** until that ROM is supplied. This
  includes Bret's black-gear prototype, which was never part of the editor.
- Receiving art never uses stock Royal art for a changed identity. For example, Royal Razor is
  skipped when Scott Hall's gear is present (`stock_identity_only`).

## Status vocabulary

| Status | Meaning |
|---|---|
| `missing` | No drawing exists for this role. |
| `generic` | Drawn from stock receiving parts in the slot's own art, but the poses are not Perfect-Plex poses. |
| `royal` | Royal Rumble's drawing of the same person, privately stored for this slot. |
| `own-art` | Rebuilt from this slot's own Raw parts (identity, gear and user edits carry over); donor colour roles fill the gaps. |
| `authored` | New pixels drawn for this slot. |
| `native-verified` | Measured in cold-boot gameplay with the defect assertions. |
| `reviewed` | Visually reviewed and accepted by the user. |

## Foundations built in this batch

- **Part resolver** (`tools/raw_parts.py`, `editor/raw-parts.js`). It resolves any slot's frame part
  as the game does:
  - frame part to descriptor, then tile IDs, then packets;
  - stock directory (`data/raw-tile-directory.json`, addresses only);
  - gear tables, chosen by descriptor bank (`$42/43` Scott, `$4C/4D` Nash, `$56/57` Syxx, `$60/61`
    Sting);
  - slot-12 tables, including the Perfect-Plex frames 1000–1011.

  Checks:
  - 4,128 stock parts match the WRAM-based catalog exactly.
  - Python and JS agree on 3,211 parts across all 13 slots.
  - Profile part IDs are directory byte offsets (frame index × 3).
- **Receiving storage RX3.**
  - RX1/RX2 stored drawings inside the Syxx and Sting gear reservations.
  - RX3 uses only space that the Perfect import owns or that nobody reserves: banks `$70`/`$71`,
    `$7D:A000+`, and `7E8000`/`7F8000` (reached as `$3E`/`$3F:8000`).
  - These regions are free in fresh, v0.16, pre-`569240b` and gear-modded imports.
  - Uninstall restores the base byte for byte and never clears an active gear range.
  - The browser core is the only installer; `tools/receivers_cli.js` runs the same code in Node.
    Browser export equals the Node build byte for byte.
- **Paired preview** (`editor/animation-preview.js`).
  - Shows Perfect and any receiver as the game composes them, in both facings, with play/pause and
    frame step.
  - Timing comes from native captures (7 frames per step; the final pose is held 64).
  - Against native screenshots it matches 99.6–100% of pixels on every step in three unoccluded
    scenarios (`tools/check_preview_native.py`). The referee in front of the pair lowers one
    scenario to 83–99%.
  - Entry (tie-up) and exit (downed) drawings come from other actions and are not yet in the preview.

## Perfect-Plex receiving matrix (all 13 current slots)

Source plans: `data/receiving-art.json` (part IDs and offsets only).

| Slot | Identity (reference mod) | Receiving source | Status | Evidence |
|---|---|---|---|---|
| 0 | Luna Vachon | own-art plan, donor Shawn (in progress) | generic | v0.16 replay, `luna-generic-before-after.gif` |
| 1 | Bret Hart (stock; user gear unknown) | royal (Bret) | royal, native-verified | `fixed/verification.json` |
| 2 | Undertaker | royal | royal, native-verified (both facings, both ropes, mid-ring) | `fixed/verification.json` |
| 3 | Yokozuna | royal | royal, native-verified | `fixed/verification.json` |
| 4 | Bam Bam Bigelow | own-art plan, donor Lex (in progress) | generic | — |
| 5 | Scott Hall (Razor in a stock ROM) | stock: royal (Razor). Scott gear: own-art plan, donor Razor (in progress) | royal on stock, native-verified; generic with Scott gear | `fixed/verification.json` |
| 6 | Lex Luger | royal | royal, native-verified | `fixed/verification.json` |
| 7 | Sting | own-art plan, donor Undertaker (in progress) | generic | — |
| 8 | Shawn Michaels | royal | royal, native-verified | `fixed/verification.json` |
| 9 | Syxx | own-art plan, donor Bret (in progress) | generic | — |
| 10 | Kevin Nash | own-art plan, donor Undertaker (in progress) | generic | — |
| 11 | Owen Hart | own-art plan, donor Bret (in progress) | generic | — |
| 12 | Mr. Perfect (mirror match) | royal (Perfect) | royal; **mirror match untested**: P2 cannot pick slot 12 against P1's Perfect | — |

## Findings that shape the art

- Raw draws every worker on one shared base body. The same part index shows the same body position in
  every slot: silhouette agreement is 0.94–0.98 between stock slots, 0.88 for Luna and 0.91 for
  Yokozuna. Palette indices also have the same colour role in every slot.
- So a Royal pose can be rebuilt from the target's **own** Raw parts wherever Raw has a matching
  drawing. The tie-up poses (Royal 1–3) match Raw parts almost exactly, and the target's own head,
  hair, face paint and gear appear (Luna, Bam Bam, Scott, Sting, Syxx, Nash, Owen).
- Royal draws no receiver head in poses 4–9 (it is under the attacker's arm). Royal poses 9–12 (lift
  over, inverted, fall, landing) have no matching Raw drawing. There, only the donor's body with the
  target's colour roles is available; gear shapes such as Bam Bam's flames or nWo lettering must be
  **authored**.
- Luna's art uses colour roles differently (0.88 agreement), and no Royal donor is female. Her drawings
  need separate treatment.

## Open items

- Visual review of own-art plans for each slot (contact sheets to be published), then native runs for
  every slot on the reference mod.
- Authored gear detail for poses with no own-art coverage.
- Mirror match route (another game mode, or an unreachable case documented as such).
- All other action families (see the main coverage matrix, `docs/animation-coverage.md`).
