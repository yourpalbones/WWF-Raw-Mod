# Perfect-Plex native trace: WIP build, Undertaker receiving

First native measurement of the paired animation in this repository. It is
**observation only**:
- no ROM hooks, builders or editor files were changed;
- no emulator memory was written;
- every input is a controller press.

The user supplied the ROMs for this session. Their hashes match the verified
originals: Raw `0af7b0d3…388c` and Royal `51c53e36…0df0ca`. ROMs, save states and
memory dumps stay local. Only numbers, labeled screenshots and a GIF are
committed.

## Build under test

1. **Mr. Perfect slot.** `editor/gear-workshop.html` (current `main` editor)
   imports Royal into the unmodified 3 MiB Raw ROM. Export SHA-256 `f09ead54…0582`.
2. **Diagnostic mirror restore (scratch only, not a fix).** The exported ROM stalls
   before every match (see the next section). To reach gameplay, a scratch copy
   puts original bytes `0x200000–0x2FFFFF` into the empty `0x300000–0x3FFFFF`.
   This recreates the cartridge mirror that the stock game reads through banks
   `$F0–$FF`. Nothing else changes.
3. **Receivers.** Codex's WIP builder runs unmodified:
   `codex/perfect-receivers-wip` @ `2955d5c`, `tools/build_perfect_receivers.py`.
   Built ROM SHA-256 `4ca28569…8085`.
   - The builder reports 7 receivers, 2,554 private tile IDs, and 363–365 tiles per slot.

Core: pinned Snes9x `fae2fea0…` with `tools/build_snes9x_perfect_trace.sh`.
Recipe: [`native-wip/controller-replay-undertaker.json`](../evidence/perfect-plex-receivers/native-wip/controller-replay-undertaker.json).
It is the committed v0.16 replay with three more P2 Right presses (Undertaker),
and three extra copies of its own damage cycle so that Undertaker is in the red.
A cold-boot rerun through `tools/run_controller_recipe.py` reproduced WRAM and
OAM byte for byte at frame 19700.

## Blocking importer defect (confirmed natively)

**An editor import made from the unmodified 3 MiB Raw ROM never starts a match.**
This happens for every matchup tried: Perfect vs Luna, Owen vs Perfect, and
Diesel vs Owen. The pre-match announcer screen keeps its monitors blank
indefinitely. The unmodified ROM with the same inputs shows both photos for
about 200 frames and then starts the match.

Cause, traced:
- A PC sampler on the stalled screen shows the CPU inside the interface
  decompressor at `$AB:F5AE`–`$AB:F8F0` (see [compression.md](compression.md)).
- Its source pointer (`$7C–$7E`) is `$FF:2F37`.
- On the original 3 MiB HiROM cartridge, bank `$FF` mirrors file `0x2F0000`, so
  the stock game legitimately reads this announcer graphic through the mirror.
- The 8 MiB ExHiROM expansion maps `$F0–$FF` to file `0x300000–0x3FFFFF`. That
  range is left as `0xFF`, so the decompressor runs on garbage forever.
- Restoring that 1 MiB mirror (step 2 above) lets the screen complete and the
  match start.

The committed v0.16 replay (`deea58c0…`) was presumably made on a base that
already had this mirror. Fixing it belongs to the importer (Codex-owned).
Imports into an 8 MiB base that already carries the mirror would not show the
stall; that is untested here.

A pre-`569240b` export stalls identically, so the referee/announcer palette
repair did not cause this.

## Five renderer facts (one facing: attacker on the left)

| Fact | Measured | Evidence |
| --- | --- | --- |
| 1. Runtime flip | Attacker objects unflipped, receiver objects h-flipped, in all 139 matched frames | `measurement.json` `flip_pairs` |
| 2. Reflection rule | Flipped object: `oam_x = origin − dx − size + 8`. Pixel column `c → −c + 7`, not `−c−1` or `−c`. The receiver's stock shadow (profile dx 0) shows the same +8. | `receiver_body_terms` = −24 for every frame |
| 3. Profile dx with facing | Negated: body term −24 = −32 + 8 | same |
| 4. Actor spacing | Receiver − attacker = **+40** (x 348 / 308) throughout the move; WRAM y equal (210) | per-frame WRAM in `measurement.json` |
| 5. OAM order | Attacker objects precede the receiver's (attacker drawn on top) in 139/142 frames. The 3 exceptions are entry frames 22–24 (held tie-up pose). | `attacker_oam_first` |

Fact 2 is relative to the unflipped attacker, whose origin defines the camera
here. The other facing (attacker on the right) and rope positions are
**untested**.

## Measured vs predicted

[perfect-plex-pair-coordinates.md](perfect-plex-pair-coordinates.md) now
includes the measured rule. With spacing +40 it predicts a receiver
registration error of **+6 px**. Measured: **+6 px in all 139 matched frames**.
The receiver is drawn 6 px toward the attacker relative to Royal. Vertical
registration is exact (both origins y=137).

So the earlier prediction (−1/−2 px) was wrong in its reflection assumption.
The corrected model now reproduces the measurement. Interpretation, not a
proposal:
- With this renderer, registration at spacing +40 would need the receiver body
  6 px further from the attacker.
- Spacing differs between runs (+41 with Luna), so any constant would be off by
  about 1 px for other tie-ups.
- No offsets are changed here.

## Other native observations

- **Pixel integrity.** Frames 25–163 cover every pose 0–11, in lockstep with the
  attacker (pose changes at frames 25, 33, 40, 46, 53, 60, 68, 75, 82, 89, 96 and
  102). Every rendered receiver pixel's colour index equals the builder's
  expected index after the 6 px shift: **100% in all 139 frames**. That means no
  stale or partially uploaded tiles in the receiver's body objects.
- **Entry (PP-1 confirmed).** Frames 22–24 hold the stock tie-up OAM unchanged.
  At frame 25 the attacker draws the mirrored Royal lift, and the receiver body
  moves about 40 px left, past the attacker, in one frame
  ([entry.png](../evidence/perfect-plex-receivers/native-wip/entry.png)).
- **Shadow (PP-3 confirmed).** The receiver's stock shadow stays at its actor
  origin (screen x 148–179) while the body is drawn about 38–63 px to the left.
- **Lift overlap (PP-2).** This is the combination of the mirrored scene, the
  +6 px registration error toward the attacker, and the attacker drawn on top.
- **Stray fragment (new, PP-7).** From frame 25, four palette-6 8×8 objects at
  screen (145–160, 129–144) reuse receiver VRAM tiles 98–101 and show a pink
  fragment beside the shadow. They are not present before the move. They remain
  through frame 260, by which point their tiles read grey
  ([fragment.png](../evidence/perfect-plex-receivers/native-wip/fragment.png)).
  Source not yet traced.
- **Exit (PP-4).** At frame 164 the receiver changes from action 540 to 70 and
  its x from 348 to 334. From frame 166 to at least 260 it is drawn **standing**,
  overlapping the attacker ([after.png](../evidence/perfect-plex-receivers/native-wip/after.png)),
  while WRAM reports action 70. So action 70 is not a lying-down pose in this
  build. Earlier documents called action 70 "downed"; the drawn pose is
  standing/dazed.
- **Damage.** 160 (health 220 → 60), once.

Gameplay GIF: [undertaker-wip-native.gif](../evidence/perfect-plex-receivers/native-wip/undertaker-wip-native.gif)
(capture frames 15–209, every second frame, 2× nearest-neighbour).

## Reproduce

```sh
python3 -m pip install playwright            # editor export, as tools/verify_royal_import.py does
bash tools/build_snes9x_perfect_trace.sh BUILD_DIR
# 1. Export the Mr. Perfect ROM from editor/gear-workshop.html (Add Mr. Perfect), then
#    copy original 0x200000-0x2FFFFF to 0x300000-0x3FFFFF in a scratch copy (diagnostic).
# 2. On codex/perfect-receivers-wip: python3 tools/build_perfect_receivers.py SCRATCH.sfc ROYAL.sfc --output WIP.sfc
python3 tools/run_controller_recipe.py CORE WIP.sfc \
  evidence/perfect-plex-receivers/native-wip/controller-replay-undertaker.json --output OUT
python3 tools/run_controller_recipe.py CORE WIP.sfc \
  evidence/perfect-plex-receivers/native-wip/controller-replay-undertaker.json \
  --output MOVE --from-state OUT/frame-019700.state --base 19700 --frames 260 --interval 1
python3 tools/measure_perfect_pair.py MOVE WIP.sfc ROYAL.sfc --receiver-slot 2 --output measurement.json
python3 tools/check_perfect_receiver_pixels.py ROYAL.sfc --output pixel-coverage.json
```

## Not covered

- The other facing and rope positions.
- The other six direct counterparts.
- The released v0.16 receiver path in the same detail.
- Editor isolation (edit, export, reopen).
- The source of the PP-7 fragment.
