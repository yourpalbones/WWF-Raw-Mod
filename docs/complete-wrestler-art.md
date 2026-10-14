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

## Mr. Perfect's ordinary poses (batch 2)

Mr. Perfect's slot reuses Raw Bret's 1,720 frame pieces. In v0.16, 289 of them used Royal Perfect art and
1,431 were Raw Bret drawings recoloured into Perfect's palette, with Bret's dark hair and build. This batch
replaces every adapted piece that Royal Rumble draws for Perfect.

| | v0.16 | now |
|---|---|---|
| Royal Perfect art (exact silhouette match, earlier) | 289 | 289 |
| Royal Perfect art (pose match, this batch) | — | **329** |
| Adapted Raw Bret art (identity not preserved) | 1,431 | **1,102** |

**How a piece qualifies** (`tools/match_perfect_poses.py`, table `data/perfect-pose-matches.json`; indices
and metrics only, no pixels):
- Royal draws Bret and Perfect on the same frame indices and coordinates (812 of 828 frames share their
  origin). So a Raw Bret piece that matches a Royal Bret frame takes Royal Perfect's frame at the same index,
  placed by the measured transform (flip, dx, dy). Every placement is re-checked against the measured IoU.
- Accepted: IoU ≥ 0.95, or IoU ≥ 0.88 with colour-role agreement ≥ 0.6.
- Excluded:
  - Royal indices below 16 (shadows).
  - Royal frames drawn **only** from tiles that Bret's frame also uses (227 generic frames). Royal recolours
    these by palette, which gave Perfect brown hair in review (`p801`, `p802`, `p805`); `s617` and `s681`
    were wrong in shape or gear.
- Visual review: all 329 replacements, before and after, in Perfect's palette, ordered riskiest first. All
  show the same pose with Perfect's blond hair, singlet, kneepads and boots. (The sheets contain game art and
  stay private.)

**Older imports, edits and space**
- `RAW_ROYAL_IMPORT_CORE.upgradePoses` (the editor's **Update Perfect-Plex**) repacks slot 12.
  - A piece is replaced only while its pixels still hash to the adapted art it supersedes (`replaces`).
  - Every other piece is decoded and stored again pixel for pixel, including your edits and the Perfect-Plex
    frames.
  - It refuses to run if another identity's edited tile was relocated into Perfect's space.
- Results:
  - A synthetic one-byte edit in a shared tile kept both affected pieces and replaced the other 327.
  - Repack with nothing to replace: 1,732/1,732 pieces identical.
  - The repacked slot uses fewer tiles (12,110 primary / 7,853 secondary, against 12,655 / 8,667).
- Browser and Node agree:
  - Browser update of the RX3 stock build equals Node (uninstall, upgrade, reinstall) byte for byte
    (`1fa0424c…`).
  - Fresh browser import and upgrade carry the same 1,732 pieces.
  - v0.16 and pre-`569240b` imports update. All 13 receivers reinstall afterwards. Reopen and resave are
    byte-identical.

**Native gameplay** (`tools/check_perfect_poses_native.py`)
- Cold boot, controller only. Every second frame after character select, each 8×8 tile of Perfect's
  objects is looked up in his slot's pieces.

| Recipe on new build | Frames inspected | Perfect's tiles | Foreign tiles | Replaced Bret tiles | Replaced pieces seen |
|---|---|---|---|---|---|
| `luna-attacker-left` | 1,443 | 49,301 | 0 | 0 | 10 |
| `owen-attacker-right` | 2,903 | 95,094 | 0 | 0 | 5 |

"Pieces seen" counts only pieces with a tile no other piece uses, so it undercounts.

**Timing changes with the art.** The same inputs replay a different match on the new build: game state first
differs at frame 6,618, and Owen's recipe no longer reaches the Perfect-Plex. Tile decode time feeds the game's
timing, so controller recipes are build-specific. The Perfect-Plex receiver scenarios are being re-recorded
and re-verified on the new builds (stock `349d462e…`, gear mod `51bdfdb7…`). Until that finishes, the matrix
above reflects the previous builds.

**Still open for Perfect**
- 1,102 adapted pieces have no Royal counterpart (Raw-only actions or generic frames). They need **authored**
  Perfect art.
- 24 of the 289 earlier exact matches use generic Royal frames and need the same review.
- Per-action mapping of pieces (which moves show which pieces) is not built yet. That is part of the
  action-family matrix.

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
