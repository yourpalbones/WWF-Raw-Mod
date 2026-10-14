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

Builds:
- **Stock import:** `15c1d9b5…`, the browser export of stock Raw with Mr. Perfect.
- **Gear reference mod:** `a870f3fe…`, with Scott, Syxx, Nash and Sting applied, then Mr. Perfect.

Every scenario below is a controller-only cold-boot replay (`tools/verify_perfect_receivers_native.py`).
Each passes every defect assertion:
- spacing ±40;
- no foreign objects;
- damage exactly once;
- no Perfect-Plex pose after the move.

Royal-drawn receivers also register within 1 px. Own-art receivers must equal the editor preview on every
step, and they do: 100% of actor pixels, rebuilt from OAM. Data:
[`verification-stock.json`](../evidence/complete-wrestler-art/verification-stock.json) and
[`verification-gear-mod.json`](../evidence/complete-wrestler-art/verification-gear-mod.json).

| Slot | Identity | Receiving drawings | Native scenarios (all pass) | Status |
|---|---|---|---|---|
| 0 | Luna Vachon | own native (re-timed) | `luna-attacker-left`, `luna-attacker-left-2` | own-art, native-verified ([GIF](../evidence/complete-wrestler-art/luna-attacker-left.gif)) |
| 1 | Bret Hart (stock; user gear unknown) | Royal Bret | `bret-attacker-left-right-rope` | royal, native-verified |
| 2 | Undertaker | Royal Undertaker | 5 scenarios: both facings, both ropes, mid-ring | royal, native-verified |
| 3 | Yokozuna | Royal Yokozuna | `yokozuna-attacker-left-right-rope` | royal, native-verified |
| 4 | Bam Bam Bigelow | own native (re-timed) | `bambam-attacker-left` | own-art, native-verified ([GIF](../evidence/complete-wrestler-art/bambam-attacker-left.gif)) |
| 5 | Razor Ramon (stock) / Scott Hall (gear) | Royal Razor on stock; own native with Scott's gear | `razor-attacker-left-right-rope` (stock), `scott-gear-attacker-left` (gear) | royal + own-art, native-verified ([GIF](../evidence/complete-wrestler-art/scott-gear-attacker-left.gif)) |
| 6 | Lex Luger | Royal Lex | `lex-attacker-left-right-rope` | royal, native-verified |
| 7 | Doink (stock) / Sting (gear) | own native (re-timed) | `doink-attacker-left` (stock), `sting-gear-attacker-left`, `sting-gear-attacker-left-2` (gear) | own-art, native-verified ([GIF](../evidence/complete-wrestler-art/sting-gear-attacker-left.gif)) |
| 8 | Shawn Michaels | Royal Shawn | `shawn-attacker-left-right-rope` | royal, native-verified |
| 9 | 1-2-3 Kid (stock) / Syxx (gear) | own native (re-timed) | `kid-attacker-right` (stock, opposite facing), `syxx-gear-attacker-left` (gear) | own-art, native-verified ([GIF](../evidence/complete-wrestler-art/syxx-gear-attacker-left.gif)) |
| 10 | Diesel (stock) / Kevin Nash (gear) | own native (re-timed) | `diesel-attacker-left` (stock), `nash-gear-attacker-left` (gear) | own-art, native-verified ([GIF](../evidence/complete-wrestler-art/nash-gear-attacker-left.gif)) |
| 11 | Owen Hart | own native (re-timed) | `owen-attacker-right` (opposite facing) | own-art, native-verified ([GIF](../evidence/complete-wrestler-art/owen-attacker-right.gif)) |
| 12 | Mr. Perfect (mirror match) | Royal Perfect (installed, previewable) | none: **unreachable in one-on-one** | royal, **not natively tested** |

Notes on the matrix:
- **Re-timing.** Raw's own receiving-suplex sequence lifts at its third drawing; the Perfect-Plex lifts
  at step 10. Played in order, the receiver lay at Perfect's feet during steps 5–9, which was caught in
  visual review. The held drawing now carries steps 2–9, the lift drawings steps 10–11 and the landed
  drawing the bridge (`OWN_NATIVE_STEPS`). This is still Raw's lift-and-fall art, not Royal's exact
  frames, and it needs your visual review.
- **Mirror match.**
  - Two-player selection skips the wrestler P1 chose.
  - One-player "player chooses opponents" does not accept the same wrestler (A has no effect).
  - A bot attempt never reached a match.
  - Other modes (tag team, Survivor Series, Royal Rumble, Bedlam, Raw Endurance) are untested.
- **Recipes.** `tools/recipe_bot.py` played the own-art recipes. It reads memory to choose controller
  presses and writes nothing, and the result is a fixed input list.
- **Private editing on RX3.**
  - A mouse stroke on Sting's receiving pose (gear mod) changed only Sting's tiles, including 40
    relocated packet bytes. The other 12 receivers decode identically.
  - Reopening and saving gives an identical file.
- **Editor.** Every slot lists its 12 "Receiving Perfect-Plex · n" composite poses. The paired preview
  plays any receiver in both facings ([screenshot](../evidence/complete-wrestler-art/editor-paired-preview-sting.png)).

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

- **Your visual review** of the own-art Perfect-Plex receivers (GIFs above). Royal-pose rebuilds from own
  parts (`tools/plan_receiving_art.py`, `editor/receiving-art.js` `render`) remain unshipped. Donor colour
  roles did not keep gear consistent across adjacent frames.
- **Mirror match** in other game modes.
- **Next family: Mr. Perfect's ordinary poses.**
  - 1,431 of his 1,720 pieces are Raw Bret drawings recoloured into Perfect's palette, so his body and
    hair are Bret's. That breaks the identity rule and is the next batch.
  - With a Royal WRAM dump, the Royal catalogue is reproduced exactly (144/144 receiving drawings).
  - 682 Raw Bret pieces match a Royal Bret frame at an IoU of at least 0.95 (289 are converted today).
    Royal Perfect's same frame can replace them once colour and semantics are checked.
- **All other action families** (see `docs/animation-coverage.md`).
