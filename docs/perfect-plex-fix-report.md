# Perfect-Plex fixes: report

Task: [`docs/CLAUDE-PERFECT-PLEX-FIX-TASK.md`](CLAUDE-PERFECT-PLEX-FIX-TASK.md) (Codex, `396896a`).
Branch `claude/charming-allen-njttcx`, draft PR #1, for Codex review. Not merged and not released.

How the evidence was gathered:
- Every native result comes from controller input only, starting from a cold boot. No emulator
  memory is written.
- The "fixed export" is the file that the real browser editor downloads after it adds Mr. Perfect
  to the unmodified 3 MiB Raw ROM (`tools/editor_driver.py import`). It needs no mirror restore and
  no other post-processing.
- The "before" build is the one measured earlier: the Codex WIP build `4ca2856…`, which includes
  the diagnostic mirror restore.
- ROMs, states, memory dumps and extracted pixels stay local.

## Causes (confirmed) and fixes

### PP-0

**Cause.** Imports from the stock ROM stalled on the announcer screen.
- Raw's announcer reads four tables, each holding one 16-bit entry per slot. Two of them hold
  address words and two hold banks (bank in the low byte).
- The importer copied the bank tables (`0x2EE927`, `0x2EE957`) as 12 single bytes, and wrote
  Mr. Perfect's bank at +12.
- So slots 6–12 read bank `$FF` from erased space.
- The earlier "missing `$F0–$FF` mirror" explanation was wrong. Restoring the mirror only made
  those bad reads land on a copy of the right data.

**Fix.**
- `editor/royal-import.js` rebuilds all four tables (13 entries, word stride) from the profile
  records, so user monitor edits are kept.
- Older imports are repaired by "Save playable ROM", and the editor says so when such a ROM is
  opened.
- `tools/perfect_profile_assets.py` gets the same fix.

### PP-1/2/3: facing, registration, shadow

**Cause.**
- Raw's art faces right when unflipped. The imported Perfect-Plex attacker frames faced left.
- So the whole scene was mirrored, and the receiver was registered |spacing| − 34 px toward the
  attacker.

**Fix.**
- The attacker frames are now used as captured, and the receiver drawings are mirrored
  (`tools/canonical_perfect_geometry.py`).
- Offsets come from the measured flip rule: flipped x = origin − dx − size + 8.
- The init hook fixes the pair spacing at 40 px on the receiver's existing side.
- The receiver body offset is 45, and the shadow offset is computed per pose.
- Builds carry the markers `ROYAL-RX2` and `PLEX-CANON1`.

### PP-4: exit art

**Cause.** Both sequence hooks tested `$06B4,X`, the current action, instead of the action being
dispatched. So the next action's dispatch was sent back to step 0 of the Perfect-Plex stream, and
both actors froze in a Perfect-Plex pose after the move.

**Fix.**
- The hooks test the dispatched action (`lda 3,s` at `$80:F073`).
- On the receiver-only exit path, the receiver hook restores the stock sequence bank (`$C4`) from
  its own bank (`$71`).
- Non-special actors keep their exact original code paths, so the recipes stay frame-synchronous.

### PP-7: extra objects and pink fragments

**Cause.** The WIP receiver hook used `$90` as scratch. That is the stock part loader's running
object total (`$80:EC97`/`$80:ECE4`), so the loader emitted extra stale objects.

**Fix.** The hooks compute slot×3 on the stack and keep the stream base in `$7C`. `$90` and `$92`
are untouched. The Python builder and the browser core generate the same bytes.

## Verification

### Native scenarios

Fixed export SHA-256 `f2a81a91…70c6`. The committed recipes are replayed from a cold boot by
`tools/verify_perfect_receivers_native.py`, which now checks these defect assertions:

| Defect | Assertion |
|---|---|
| PP-0 | Announcer tables are consistent, and the move is reached |
| PP-1/2 | Registration error is at most 1 px, and spacing is ±40 |
| PP-3 | Shadow centre is within 12 px of the body centre |
| PP-7 | No foreign palette-6 objects, and no more than 4 trailing the receiver |
| PP-4 | No Perfect-Plex pose after the move beyond 2 frames of the final pose, and damage exactly once |

Expected values were recorded only after every assertion passed (`expected_build`). A second cold-boot run in check mode reproduced all ten exactly. The old
expected values are kept as `defect_baseline`. Full data: [`fixed/verification.json`](../evidence/perfect-plex-receivers/fixed/verification.json).

| Scenario | Matched frames | Flips (att, rcv) | Spacing | Reg. error | Trailing pal-6 / foreign | Shadow offset | Damage | After move (receiver) |
|---|---|---|---|---|---|---|---|---|
| Undertaker, attacker left, right rope | 139/142 | (F, T) | 40 | 0 | 4 / 0 | 1…10 | 220→60 | action 70, native art |
| Undertaker, attacker right, right rope | 138/141 | (T, F) | −40 | 0 | 4 / 0 | −2…−1 | 220→60 | action 70, native art |
| Undertaker, attacker left, left rope | 138/141 | (F, T) | 40 | 0 | 4 / 0 | 1…10 | 220→60 | action 70, native art |
| Undertaker, attacker right, left rope | 138/141 | (T, F) | −40 | 0 | 4 / 0 | −10…−1 | 220→60 | action 70, native art |
| Undertaker, attacker left, mid-ring | 140/143 | (F, T) | 40 | 0 | 4 / 0 | 1…10 | 236→76 | action 70, native art |
| Bret Hart | 138/141 | (F, T) | 40 | 0 | 4 / 0 | 1…10 | 156→0 | action 70, native art |
| Yokozuna | 138/141 | (F, T) | 40 | 0 | 4 / 0 | 1…10 | 154→0 | action 70, native art |
| Razor Ramon | 138/141 | (F, T) | 40 | 0 | 4 / 0 | 1…10 | 250→90 | action 70, native art |
| Lex Luger | 138/141 | (F, T) | 40 | 0 | 4 / 0 | 1…10 | 298→138 | action 70, native art |
| Shawn Michaels | 138/141 | (F, T) | 40 | 0 | 4 / 0 | 1…10 | 312→152 | action 70, native art |

Notes on the table:
- **Matched frames.** The 3 unmatched frames per scenario are the entry and exit transitions, where
  one actor has already changed pose. OAM lags by one frame there, and only 2 shadow objects trail.
- **Receiver pixels** match the builder's drawing in 100% of the matched frames, with a vertical
  offset of 0.
- **Shadow offset** is the receiver's shadow centre minus its body's opaque centre, in px. The
  shadow is centred per pose on the drawing's bounding box, so poses with a reaching limb measure up
  to 10 px off the opaque centre.
- **Before the fix,** on the old build, the base scenario and its opposite facing each fail five assertions: PP-0, PP-1/2, PP-3,
  PP-7 and PP-4 exit art. The PP-4 damage-count assertion passes on the old build too, because the
  old build also applied the move's damage once. Old values for every scenario are in each recipe's
  `defect_baseline`. For the base scenario they were: registration 6 px, 8 trailing objects, 71
  frames with foreign objects, and the lift pose shown for 107 frames after the move.

### Recovery after the move (PP-4)

[`undertaker-attacker-left-right-rope-recovery.json`](../evidence/perfect-plex-receivers/recipes/undertaker-attacker-left-right-rope-recovery.json)
extends the base recipe. Its inputs are identical up to the move. After the move, P2 mashes buttons
and P1 walks and attacks. `tools/trace_actor_state.py` on the fixed export shows:
- Undertaker is down (action 70), gets up (76), walks and attacks (142 and 130). Perfect's health
  drops 928 → 864 → 830.
- Perfect walks (2/4/6/8), throws, climbs the turnbuckle (118) and attacks again.
- The receiver's health changes once during the move (220 → 60), and again only when it is hit
  later.

The game state is identical on the old build. The defect there was visual only: both actors stayed
drawn in a Perfect-Plex pose until their next action.

### Generic receiving path

The committed v0.16 replay has Luna receiving. Luna has no Royal art, so she uses the generic
stock-part path. The replay runs frame-identically on both builds. In the old build the scene is
mirrored and both workers freeze in the lift pose afterwards. In the fixed export the facing is
correct and Luna shows her own downed art. This was checked visually, without the pair measurement,
which needs Royal receiver art.

### GIFs

All GIFs are native, nearest-neighbour enlargements, labelled with the build and recipe frame:
- [`undertaker-left-right-rope-before-after.gif`](../evidence/perfect-plex-receivers/fixed/undertaker-left-right-rope-before-after.gif): the move, attacker on the left.
- [`undertaker-right-right-rope-before-after.gif`](../evidence/perfect-plex-receivers/fixed/undertaker-right-right-rope-before-after.gif): the opposite facing.
- [`undertaker-recovery-before-after.gif`](../evidence/perfect-plex-receivers/fixed/undertaker-recovery-before-after.gif): getting up, walking and attacks.
- [`luna-generic-before-after.gif`](../evidence/perfect-plex-receivers/fixed/luna-generic-before-after.gif): the generic receiving path.

### Editor

| Check | Result |
|---|---|
| Browser import vs Python receiver build | Byte-identical, apart from the checksum and the `PLEX-CANON1` marker |
| `verify_royal_import.py` | Passes. Original twelve unchanged (names, palettes, HUD, themes, portraits). 13 slots and 1,744 poses (12 receiving drawings each for slots 1, 2, 3, 5, 6, 8, 12). Wrong donor rejected. Project round trip, tile relocation, portrait, monitor and theme all work. |
| `verify_referee_repair.py` (pre-`569240b` import) | Passes. NPC palettes and announcer tables repaired; all 13 profiles and assets preserved; repeat export is stable. |
| Private editing (`editor_driver.py edit-receiver` + `check_receiver_isolation.py`) | A mouse stroke on Shawn's "Receiving Perfect-Plex · 5" changes 27 bytes, all in that worker's tile. Every pose of the other six receivers decodes identically. Reopening and saving gives an identical file. |
| Update Perfect-Plex (`editor_driver.py update`) on a v0.16 import | Produces a `ROYAL-RX2` / `PLEX-CANON1` build with no page errors. The base native scenario on that output passes every defect assertion. |
| Unit tests | `python3 -m unittest discover -s tests`: 40 run, 6 skipped, 0 failed. |

## Not done or not verified

- **Bridge-to-pin (PP-5): not implemented.** After the move, the actors return to the stock
  downed/standing flow. There is no pin transition.
- **Raw-only workers have no receiving art:** Luna (0), Bam Bam (4), Sting (7), Syxx (9), Nash (10)
  and Owen (11). They use the generic stock-part path. Only Luna was checked natively. No slot was
  filled with another wrestler's art.
- **Mirror match (Perfect receiving, slot 12): untested.** P2 cannot pick slot 12 against P1's
  Perfect.
- **Natively measured receivers:** Undertaker, Bret Hart, Yokozuna, Razor Ramon, Lex Luger and Shawn
  Michaels. This is not complete roster coverage.
- **Green shadow.** Perfect's own shadow is drawn green in every capture inspected, on both builds
  and outside the Perfect-Plex too. This is likely a palette entry of the imported worker, and it is
  not changed here.
- **Bundle size.** `editor/gear-workshop.html` is about 56 MB, above GitHub's 50 MB recommendation.
  This predates the fix.
