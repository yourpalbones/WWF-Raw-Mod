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

## Five renderer facts (first capture: attacker on the left)

All ten scenarios below confirm these, including both facings and both ropes.

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
- **Stray fragment (PP-7), traced; see the PP-7 section below.** From frame 25,
  extra palette-6 objects follow the receiver's shadow and show a pink fragment
  ([fragment.png](../evidence/perfect-plex-receivers/native-wip/fragment.png)).
- **Exit (PP-4), traced; see the PP-4 section below.** After the move, both actors
  stay on Perfect-Plex pose 0 ([after.png](../evidence/perfect-plex-receivers/native-wip/after.png)).
- **Damage.** 160 (health 220 → 60), once.

Gameplay GIF: [undertaker-wip-native.gif](../evidence/perfect-plex-receivers/native-wip/undertaker-wip-native.gif)
(capture frames 15–209, every second frame, 2× nearest-neighbour).

## All scenarios: both facings, both ropes, five receivers

Every scenario is a committed controller-only recipe in
[`recipes/`](../evidence/perfect-plex-receivers/recipes/), composed by
`tools/compose_perfect_recipes.py` from the v0.16 replay.
`tools/verify_perfect_receivers_native.py` replayed each one from a cold boot,
captured 400 frames around the move, and measured it. Each recipe stores its
results under `expected`. A second check-mode run reproduced them exactly
(see Reproduce).

| Scenario (frame sheet) | Receiver slot | Matched frames | Flip (attacker, receiver) | Spacing R−A | Registration error (px) | Receiver pixel match | Vertical offset | Trailing palette-6 objects | Frames with foreign palette-6 | Pose shown after move |
| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | --- | ---: | --- |
| [bret-attacker-left-right-rope](../evidence/perfect-plex-receivers/native-wip/scenarios/bret-attacker-left-right-rope.png) | 1 | 138/141 | (False, True) | 40 | 6 | 100% | 0 | 6–6 | 14 | 0 |
| [lex-attacker-left-right-rope](../evidence/perfect-plex-receivers/native-wip/scenarios/lex-attacker-left-right-rope.png) | 6 | 138/141 | (False, True) | 40 | 6 | 100% | 0 | 9–13 | 137 | 0 |
| [razor-attacker-left-right-rope](../evidence/perfect-plex-receivers/native-wip/scenarios/razor-attacker-left-right-rope.png) | 5 | 138/141 | (False, True) | 40 | 6 | 100% | 0 | 8–12 | 63 | 0 |
| [shawn-attacker-left-right-rope](../evidence/perfect-plex-receivers/native-wip/scenarios/shawn-attacker-left-right-rope.png) | 8 | 138/141 | (False, True) | 40 | 6 | 100% | 0 | 9–13 | 137 | 0 |
| [undertaker-attacker-left-left-rope](../evidence/perfect-plex-receivers/native-wip/scenarios/undertaker-attacker-left-left-rope.png) | 2 | 138/141 | (False, True) | 41 | 7 | 100% | 0 | 4–8 | 7 | 0 |
| [undertaker-attacker-left-mid-ring](../evidence/perfect-plex-receivers/native-wip/scenarios/undertaker-attacker-left-mid-ring.png) | 2 | 140/143 | (False, True) | 41 | 7 | 100% | 0 | 8–8 | 72 | 0 |
| [undertaker-attacker-left-right-rope](../evidence/perfect-plex-receivers/native-wip/scenarios/undertaker-attacker-left-right-rope.png) | 2 | 139/142 | (False, True) | 40 | 6 | 100% | 0 | 8–8 | 71 | 0 |
| [undertaker-attacker-right-left-rope](../evidence/perfect-plex-receivers/native-wip/scenarios/undertaker-attacker-right-left-rope.png) | 2 | 138/141 | (True, False) | -40 | -6 | 100% | 0 | 5–8 | 63 | 0 |
| [undertaker-attacker-right-right-rope](../evidence/perfect-plex-receivers/native-wip/scenarios/undertaker-attacker-right-right-rope.png) | 2 | 138/141 | (True, False) | -41 | -7 | 100% | 0 | 8–8 | 76 | 0 |
| [yokozuna-attacker-left-right-rope](../evidence/perfect-plex-receivers/native-wip/scenarios/yokozuna-attacker-left-right-rope.png) | 3 | 138/141 | (False, True) | 40 | 6 | 100% | 0 | 10–10 | 76 | 0 |

Read across the rows:
- **Registration:** in every case the receiver is drawn **|spacing| − 34 px toward
  the attacker**: +6/+7 with the attacker on the left, −6/−7 with the attacker
  on the right. That holds at either rope, mid-ring, and for all five receivers.
  The coordinate model with the measured flip rule predicts exactly this.
- **Rope clamp:** spacing is 40 or 41 depending on whether the pair was clamped
  at a rope.
- **Pixels, vertical, flip:** every rendered receiver pixel matches its builder
  drawing (100%). Vertical registration is exact. Flips follow facing, and the
  body term is ∓32 (profile dx negated with facing).
- **Side swap (PP-1) occurs only with the attacker on the left.** The stock
  converted Mr. Perfect art faces **right** when unflipped (tie-up OAM), but the
  imported Perfect-Plex frames face **left** when unflipped. They are stored
  mirrored relative to Raw's own facing convention. With the attacker on the
  right (flipped), the move faces the receiver and no swap occurs
  ([sheet](../evidence/perfect-plex-receivers/native-wip/scenarios/undertaker-attacker-right-left-rope.png)).
- **Receiver after the move:** its x shifts by ±14 toward the attacker when it
  was at a rope (348 → 334, 162 → 176). Mid-ring it does not move.
- **Mr. Perfect receiving (slot 12) is unreachable** in this mode: P2's cursor
  reaches Mr. Perfect, but the game blocks picking the wrestler P1 already chose.
  Other match modes are untested.

## PP-7 traced: the receiver hook overwrites the part loader's object total

- Stock part loader, `$80:EC97`: `STZ $90` starts a running object total for
  the actor.
- `$80:ECE4`: `LDA [$80] / CLC / ADC $90 / STA $90` adds each part descriptor's
  object count. The secondary path at `$80:ED39` does the same.
- The WIP receiver hook (`worker_hook` in `tools/build_perfect_receivers.py`)
  contains `85 90 4a 18 65 90 aa`. It **stores the receiver's selector word into
  `$90`** as scratch, then returns into the loader at `$80:ECE2`. The total
  therefore starts at the selector word instead of 0.
- The object emitter (`$AD:FD60`/`$AD:FD91`, palette from `$92` at `$AD:FD80`)
  then emits that many extra objects past the real part lists. They are stale
  entries, drawn in the last part's palette (palette 6 after the shadow).

Native evidence:
- Extra objects equal the selector word: Bret (word 2) +2, Undertaker (4) +4,
  Yokozuna (6) +6. Razor (10), Lex (12) and Shawn (16) reach +8/+9, which
  suggests a cap.
- The extras persist after the move, because no new part request resets the
  total (see PP-4).
- With the profile's shadow entry removed in a scratch copy, the extras still
  appear, now in palette 1.
- The attacker hook and the older Undertaker prototype use only `$80/$82`, and
  neither shows extras.
- In 7–137 of each scenario's move frames, 1–4 of those extra objects show
  non-shadow (body) pixels: the pink fragment. In other frames they duplicate
  the shadow.

## PP-4 traced: both 20-step streams wrap to step 0 and stay there

- Both the attacker and receiver streams have 20 entries plus an `FF`
  terminator.
- On the last move frame (163 in the first capture), the part trace shows both
  actors requesting **step 0 again** (`0xBB8`, `0xE10`).
- One frame later the actions become 0 (attacker) and 70 (receiver), and **no
  further part request occurs**.
- Both actors then keep showing Perfect-Plex pose 0, the Royal lift-start
  pose, indefinitely. It was still showing 900 frames later without input.
- The "standing" receiver is therefore Royal's being-lifted drawing, not
  action-70 art.
- The released v0.16 build (Luna receiving) shows the same frozen attacker
  pose 0 after the move.
- This held in all ten scenarios ("Pose shown after move" = 0).

## Reproduce

```sh
python3 -m pip install playwright            # editor export, as tools/verify_royal_import.py does
bash tools/build_snes9x_perfect_trace.sh BUILD_DIR
# 1. Export the Mr. Perfect ROM from editor/gear-workshop.html (Add Mr. Perfect), then
#    copy original 0x200000-0x2FFFFF to 0x300000-0x3FFFFF in a scratch copy (diagnostic).
# 2. On codex/perfect-receivers-wip: python3 tools/build_perfect_receivers.py SCRATCH.sfc ROYAL.sfc --output WIP.sfc
python3 tools/diagnostic_restore_hirom_mirror.py RAW.sfc EXPORT.sfc --output SCRATCH.sfc   # sha256 5e9cf870…4127
# WIP.sfc sha256 must be 4ca28569…8085
python3 tools/compose_perfect_recipes.py --check
python3 tools/verify_perfect_receivers_native.py CORE WIP.sfc ROYAL.sfc --output OUT    # all ten scenarios
python3 tools/run_controller_recipe.py CORE WIP.sfc \
  evidence/perfect-plex-receivers/native-wip/controller-replay-undertaker.json --output OUT
python3 tools/run_controller_recipe.py CORE WIP.sfc \
  evidence/perfect-plex-receivers/native-wip/controller-replay-undertaker.json \
  --output MOVE --from-state OUT/frame-019700.state --base 19700 --frames 260 --interval 1
python3 tools/measure_perfect_pair.py MOVE WIP.sfc ROYAL.sfc --receiver-slot 2 --output measurement.json
python3 tools/check_perfect_receiver_pixels.py ROYAL.sfc --output pixel-coverage.json
```

## Not covered

- Mr. Perfect receiving (unreachable in one-on-one two-player selection).
- Raw-only receivers (no art yet).
- Other match modes.
- The released v0.16 receiver path in the same detail.
- Editor isolation (edit, export, reopen).
- Where the emitter's cap on extra objects comes from.
