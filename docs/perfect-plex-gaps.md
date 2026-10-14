# Perfect-Plex: prioritized gap list

Status as of this branch: **audit, provisional diagnosis and a first native
measurement.** These are not fixes, and no ROM hook has been changed. Native
results for the WIP build with Undertaker receiving, in one facing, are in
[perfect-plex-native-trace.md](perfect-plex-native-trace.md). Statements marked
**native** below come from it. Everything else stays provisional. Every "probable cause" below is a
hypothesis from code reading and ROM-free modelling. It stays provisional until
a native trace (OAM/VRAM/WRAM capture from an exported ROM) confirms it.
This revision applies Codex's review in
[`docs/CLAUDE-PR1-REVIEW.md` on `codex/perfect-receivers-wip`](https://github.com/yourpalbones/WWF-Raw-Mod/blob/codex/perfect-receivers-wip/docs/CLAUDE-PR1-REVIEW.md).

The user's report of **visible gaps between sprite pieces** stays open. Nothing
here establishes its cause.

Inputs reviewed:

- `evidence/perfect-plex-receivers/royal-native-reference.gif`: Royal native, 12 frames.
- `evidence/perfect-plex-receivers/raw-undertaker-prototype.gif`: older Undertaker-only private
  prototype (`tools/build_perfect_receiver_prototype.py`), 27 frames. The exact ROM/build of this
  GIF is not recorded in the repository.
- `evidence/mr-perfect-import/perfect-plex.gif` and `verification.json`: released v0.16 with Luna.
- `tools/import_perfect_plex.py`, `tools/build_perfect_receiver_prototype.py`, `data/perfect-receivers.json`.
- `codex/perfect-receivers-wip` @ `2955d5c`: `tools/build_perfect_receivers.py` and the browser core.

Commands (all ROM-free):

- `python3 tools/review_perfect_plex_gifs.py`: labeled review sheets.
- `python3 tools/check_perfect_receivers.py`: static record checks.
- `python3 tools/derive_perfect_pair_coordinates.py`: paired coordinate model; see
  [perfect-plex-pair-coordinates.md](perfect-plex-pair-coordinates.md).

## Static record checks (scope-limited)

These examine only the stored recipe records in `data/perfect-receivers.json`:
all 12 Royal workers × 12 frames. They say nothing about runtime upload,
scanline limits, descriptor routing, VRAM staleness or OAM order.

| Check | What was examined | Result |
| --- | --- | --- |
| S1 budget | Chunk counts plus the 2-object/4-tile shadow | Worst record 17/17 objects and 52/64 tiles. Within the per-actor recipe limit, with zero object headroom. Does not rule out runtime/scanline defects. |
| S2 order | Chunk size order | 16×16 chunks precede 8×8 chunks in every record, consistent with the header count. Does not rule out routing defects. |
| S3 bounds | Union of chunk extents vs the opaque bbox, with the +9 px canvas shift | Chunk extents reach every bbox edge (bounds only). |
| S3 exact (Royal ROM) | Every opaque pixel of all 144 decoded drawings vs the descriptor chunks (`tools/check_perfect_receiver_pixels.py`) | **0 uncovered pixels**; all decoded bboxes equal the recipe bboxes; 145 chunk tiles are empty. Builder canvas only. [`pixel-coverage.json`](../evidence/perfect-plex-receivers/pixel-coverage.json) |

## Paired coordinates (ROM-free model)

[perfect-plex-pair-coordinates.md](perfect-plex-pair-coordinates.md) derives
both actors' screen columns from the actor origins, profile offsets, descriptor
transforms and facing. It uses the actor positions recorded in the v0.16 Luna
replay (attacker x=314, receiver x=354, both y=232). Results:

- The two bodies form a rigid copy of Royal only when exactly one actor is
  mirrored. In that case the required receiver − attacker spacing is ±41/±42 px,
  depending on the reflection rule, or −22/−23 if the profile dx is not mirrored.
- The recorded spacing is +40. That is within 1–2 px of the required spacing
  only if all three of these hold:
  - the attacker is **unflipped** while the receiver stands on its right;
  - the profile dx is negated with facing;
  - the scene renders as a **mirror** of Royal.

  Every other assumption set predicts horizontal errors of 62–82 px.
- Under the 1–2 px assumption set, the model predicts the receiver body is drawn
  44–46 px left of its own actor origin on the first frames. The shadow (profile
  entry `0x8024` at (0, −1)) stays at the origin. Both the entry side swap (PP-1)
  and the detached shadow (PP-3) would then follow from one cause: mirrored
  artwork with unswapped actor origins.

**Native update:** the trace confirmed the attacker is unflipped, the profile dx
is negated, and the scene is mirrored. It showed the reflection rule is
`+8` (`c → −c + 7`), which none of the original assumption sets had. With that
rule the model predicts **+6 px**, which matches the measurement. The 1–2 px
prediction above is superseded. The model and the measurement are in
[perfect-plex-pair-coordinates.md](perfect-plex-pair-coordinates.md). No offsets
are proposed from it.

## PP-0: imports from the unmodified Raw ROM never reach a match (native, blocking)

Every matchup tried stalls on the pre-match announcer screen. The cause is
traced: the 8 MiB expansion leaves file `0x300000–0x3FFFFF` empty, while the
stock game reads an announcer graphic through the cartridge mirror at
`$FF:2F37`. Restoring the mirror in a scratch copy removes the stall. Details
are in [perfect-plex-native-trace.md](perfect-plex-native-trace.md). This sits in
the importer (Codex-owned).

## Observed symptoms and provisional causes

The *symptoms* are visible in committed gameplay GIFs. The *causes* are not
confirmed by native traces.

### PP-1: the scene plays mirrored after the tie-up

**Evidence:** [`frame-review/entry-side-swap.png`](../evidence/perfect-plex-receivers/frame-review/entry-side-swap.png).
Royal keeps Perfect on the receiver's left through the lift and bridge. Both
Raw captures (v0.16 Luna and the older Undertaker prototype) start with Perfect
on the left in the tie-up. From the first lift frame he is on the right, and the
move is a mirror image of Royal.

**Native (all scenarios):** the swap happens only with the attacker on the left.
Raw's converted Mr. Perfect art faces right when unflipped, but the imported
Perfect-Plex frames face **left** when unflipped: they are stored mirrored
relative to Raw's facing convention. With the attacker on the right (flipped),
the move faces the receiver and no swap occurs. See
[perfect-plex-native-trace.md](perfect-plex-native-trace.md).

### PP-2: visible overlap; the receiver is largely hidden behind the attacker on lift frames

**Evidence:** [`frame-review/lift-registration.png`](../evidence/perfect-plex-receivers/frame-review/lift-registration.png),
older Undertaker prototype frames #2–#5. This may relate to the user's
visible-gap report, but the link is not traced.

**Native (all ten scenarios):**
- The receiver is drawn **|spacing| − 34 px toward the attacker** relative to
  Royal registration: 6–7 px, in both facings, at both ropes, mid-ring, and for
  all five receivers.
- The attacker's objects precede the receiver's in OAM, so the attacker covers it.
- The renderer places flipped objects at `origin − dx − size + 8`.
- The coordinate model with that rule predicts the measured +6 px exactly.

Earlier status note, kept for history: cause **open**. An earlier version of this audit prescribed
per-frame profile offsets. That prescription is withdrawn: each Royal drawing's
descriptor already carries its source-relative position, so one constant profile
offset can reproduce changing body positions. Under the closest assumption set,
the coordinate model predicts only a 1–2 px horizontal error between the bodies.
If traces confirm that, the overlap needs another explanation. Candidates are
OAM draw order between the two actors, a different spacing for Undertaker than
for Luna, or a descriptor-routing or upload difference. Confirm with a trace
before choosing a fix.

### PP-3: the receiver shadow appears detached from the body

**Evidence:** [`frame-review/detached-shadow.png`](../evidence/perfect-plex-receivers/frame-review/detached-shadow.png).

**Native (WIP build):** the receiver's stock shadow stays at its actor origin
(screen x 148–179) while the body is drawn 38–63 px to its left.

**Historical prototype fact (S4):** the older prototype source writes the
receiver body at profile (+32, 0) and the shadow `0x8024` at (0, −1). By
source inspection, the WIP builder writes the same bytes. S4 parses a copy of
those bytes, not a built ROM, so it cannot detect a later implementation
change. A regression test must inspect a constructed or exported record. The
coordinate model offers a provisional explanation: the body lands 44–46 px
from the origin, the shadow does not move, and the shadow ends up up to 46 px
from the body.

### PP-4: standing overlap after the bridge (traced natively)

Both 20-step streams wrap to step 0 on the last move frame, both actors request
pose 0, and then the actions change (to 0 and 70) **without any further part
request**. Both actors stay frozen on Perfect-Plex pose 0, the Royal lift-start
drawing, indefinitely. The "standing" receiver is that drawing, not action-70
art. This happens in every scenario, and also for the attacker in the released
v0.16 build. When the receiver was at a rope, its x also shifts 14 px toward
the attacker.

Earlier text, kept for history:

**Evidence:** [`frame-review/exit.png`](../evidence/perfect-plex-receivers/frame-review/exit.png),
frames #21–#26 of the older Undertaker-only prototype GIF.

**Visual appearance and native action state are different things:**

- The committed v0.16 replay records the receiver in action **70 (downed)**
  after the move: health 58, x=340.
- Codex reports that its private seven-counterpart captures at frames 400–650
  show attacker action 0 and Undertaker receiver action 70 (downed), health 58.

The earlier claim that the implementation returns the receiver to standing is
withdrawn. The standing-overlap appearance in this one GIF still needs
inspection. First identify the exact ROM/build and frame it was captured from,
then diagnose. Do not diagnose an exit defect from the GIF alone.

### PP-7: stray fragment beside the receiver shadow (traced natively)

The WIP receiver hook stores the receiver's selector word in direct page `$90`.
The stock part loader it returns into uses `$90` as the actor's running object
total (`$80:EC97` `STZ $90`, `$80:ECE4` `ADC $90`). The emitter then draws that
many extra objects past the real lists (stale entries in the last part's
palette). Extras equal the selector word (Bret +2, Undertaker +4, Yokozuna +6;
capped near +8/+9 for Razor, Lex and Shawn). Some of them show body pixels: the
pink fragment. The older prototype hook and the attacker hook do not touch `$90`.
See [fragment.png](../evidence/perfect-plex-receivers/native-wip/fragment.png).

### PP-5: no bridge-to-pin

The Royal move holds the bridge as a pin. Raw repeats the bridge pose for
steps 12–19 and then releases. This is a behaviour difference, tracked
separately from the visual fixes.

### PP-6: palette remap is unreviewed

Both the older prototype and the WIP builder map each Royal colour to the
nearest Raw palette entry by RGB distance. That can merge outline and shade
colours. **Needs a native-pixel comparison of the inserted tiles per palette
index.**

## Identity and independence

- **Royal source sharing (S6):** Royal shares most receiving tiles across its
  workers. For example, Lex (selector 10) has 10 private source tiles out of 315.
- **Older tracked prototype** (`tools/build_perfect_receiver_prototype.py`,
  Undertaker only): de-duplicates by decoded bytes within one receiver. That
  creates no cross-slot sharing today.
- **WIP per-wrestler builder** (`codex/perfect-receivers-wip`
  `tools/build_perfect_receivers.py` and `editor/perfect-receiver-core.js`):
  - **By code inspection**, `private = {}` (JS: `privateTiles = new Map()`) is
    created inside the per-slot loop. The tile-ID counter and packet cursor
    advance globally.
  - The decoded **source** cache is shared. The inserted editable tile IDs and
    packets are **not** de-duplicated across slots.
  - This establishes allocation intent only. The editor isolation acceptance
    test (edit, export, reopen, compare all other workers) has **not** been run.
- **Direct counterparts** (Raw→Royal `1→3, 2→2, 3→9, 5→8, 6→10, 8→7, 12→1`)
  are built by the WIP builder privately. They are not released and have no
  committed gameplay evidence. Bret (1) and Scott Hall (5) need re-authored
  gear on the Royal bodies.
- **Missing, needing authored art:** Luna (0), Bam Bam (4), Sting (7), Syxx (9),
  Nash (10) and Owen (11). These must keep the approved edited heads and gear.

## Suggested order (for Codex; no hooks changed here)

1. **PP-0:** restore the `$F0–$FF` mirror (`0x300000–0x3FFFFF`) in imports from
   3 MiB ROMs.
2. **PP-7:** stop the WIP receiver hook from writing `$90`; keep the scratch on
   the stack or in an unused location.
3. **PP-1/PP-3:** store the attacker's Perfect-Plex frames in Raw's facing
   convention, and re-mirror the receiver recipes and profile offsets with it.
   Then re-measure registration (currently |spacing| − 34 px toward the attacker)
   and the shadow.
4. **PP-4:** end both streams on a native post-move pose, or force a part
   request on the action change, instead of wrapping to step 0.
5. PP-6 palette review; PP-5 pin.
6. Run the editor isolation test.

Every recipe in `evidence/perfect-plex-receivers/recipes/` can be re-run with
`tools/verify_perfect_receivers_native.py` after each change. Update each
recipe's `expected` with `--record` once a change is accepted.
