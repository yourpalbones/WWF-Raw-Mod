# Perfect-Plex: prioritized gap list

Status as of this branch: **audit and diagnosis only.** These are not fixes.
No ROM, Snes9x core or Codex's untracked receiver builder was available to
this session. Each finding is backed either by the committed gameplay GIFs or
by static analysis of committed code and data. Anything that needs a ROM to
confirm is marked **needs native capture**.

Inputs reviewed:

- `evidence/perfect-plex-receivers/royal-native-reference.gif`: Royal native, 12 frames.
- `evidence/perfect-plex-receivers/raw-undertaker-prototype.gif`: private Raw prototype, 27 frames.
- `evidence/mr-perfect-import/perfect-plex.gif`: released v0.16 with Luna, 27 frames.
- `tools/import_perfect_plex.py`, `tools/build_perfect_receiver_prototype.py`, `data/perfect-receivers.json`.

Regenerate the labeled review sheets with `python3 tools/review_perfect_plex_gifs.py`
(crops at native resolution, nearest-neighbour 2×). Static checks:
`python3 tools/check_perfect_receivers.py`.

## Ruled out (static, all 12 Royal workers × 12 frames)

| Check | Result |
| --- | --- |
| S1 object/tile budget | Worst pose 17/17 objects, 52/64 tiles including shadow. Legal, but **zero object headroom** on the worst frame. |
| S2 descriptor chunk order | Every pose lists 16×16 before 8×8, consistent with the header's large-object count. |
| S3 chunk coverage | The prototype paints at x+73 and samples at x+64. With that 9 px shift, chunks span every pose's opaque bbox, so pieces are not clipped at the canvas edges. |

So the visible problems are **not** caused by budget overflow, mis-sized
objects or canvas clipping in the stored recipes.

## Confirmed defects, in fix order

### PP-1: the scene plays mirrored after the tie-up (performer and receiver)

**Evidence:** [`frame-review/entry-side-swap.png`](../evidence/perfect-plex-receivers/frame-review/entry-side-swap.png).
In Royal, Perfect stays on the left of the receiver from the tie-up through the
lift, and bridges with his head to the left. In both the released v0.16 (Luna)
and the Undertaker prototype, Perfect starts on the left in Raw's tie-up. On
the very next frame he is on the receiver's right, and the whole move, bridge
included, is a mirror image of Royal.

**Cause (code):** `import_perfect_plex.build` mirrors the attacker capture about
Royal x=145 (`px = 145 - x + 56`) to fit Raw's canonical facing. The receiver
recipe in `map_perfect_receivers.py` keeps Royal orientation (`x - 145`, Royal
`hflip` retained). Neither is reconciled with the actor positions that the init
hook (`70:F300`) sets after the tie-up. The attacker is therefore drawn on the
far side of its own actor origin.

**Fix direction:** choose one canonical facing for both streams. Then either
(a) mirror both the attacker and receiver recipes and negate the pair spacing,
or (b) keep both in Royal orientation and swap the sign the init hook uses for
the attacker/receiver x offset. Verify both facings and both rope sides.
**Needs native capture.**

### PP-2: receiver registration is wrong; the receiver is hidden behind the attacker on lift frames

**Evidence:** [`frame-review/lift-registration.png`](../evidence/perfect-plex-receivers/frame-review/lift-registration.png).
In Royal, the receiver stands clear of Perfect, about 25 native px apart. In
the prototype, Undertaker's body sits almost entirely behind Perfect on raw
frames #2–#5; only a hand or shoulder shows. This matches the user's report of
missing pieces between the wrestlers.

**Cause:** the prototype uses one constant receiver offset, `(+32, 0)` plus the
+9 canvas shift, for all 20 steps (static check S5). It also inherits PP-1's
mirroring. The released layout needed per-frame translates of 55–61 px. Royal's
pair spacing changes across the lift, drop and bridge, while the anchors in
`data/perfect-receivers.json` already encode it relative to the attacker
(x=145, y=162).

**Fix direction:** after fixing PP-1, write a per-frame receiver offset:
Royal anchor delta, plus the Raw actor spacing that the init hook establishes,
negated under flip. Do not use a constant. **Needs native capture.**

### PP-3: the receiver shadow is detached from the body

**Evidence:** [`frame-review/detached-shadow.png`](../evidence/perfect-plex-receivers/frame-review/detached-shadow.png).
A grey dithered shadow stays at Undertaker's tie-up position through the
whole lift and bridge, well to the right of both wrestlers.

**Cause (code, static check S4 fails):**
`build_perfect_receiver_prototype.py` writes each receiver profile as body
`(dx=32, dy=0)` followed by the Raw shadow part `0x8024` at `(0, -1)`. The
body moves and the shadow does not. The released layout translates every part,
shadow included.

**Fix direction:** offset the shadow entry with the body, or drop it during
airborne frames to match Royal. This is a one-line profile change, but it is
in a Codex-owned file (see [agent-coordination.md](agent-coordination.md)).

### PP-4: no exit transition; the receiver snaps to standing inside the attacker

**Evidence:** [`frame-review/exit.png`](../evidence/perfect-plex-receivers/frame-review/exit.png).
After the bridge (raw #18–#19), raw #21 onward shows Undertaker standing,
overlapping Perfect, with no get-up. The receiver stream ends after 20 entries
(`0x735000 + 20*7 = FF`) and returns to the receiver's native standing action
at its actor position. That position is now under the attacker.

**Fix direction:** end the receiver stream on a native downed/knockdown action
for that slot, not standing. Reposition the actor to where the body lies
(the bridge pose's Royal anchor). Then hand over to Raw's normal get-up or pin
logic.

### PP-5: no bridge-to-pin

The Royal move holds the bridge as a pin. Raw repeats the bridge pose for
steps 12–19 and then releases both wrestlers. This is a behaviour difference,
not an art defect. It needs Raw's pin-state entry from the sequence hook and
is tracked separately from the visual fixes.

### PP-6: palette remap is unreviewed (Undertaker prototype)

The prototype maps each Royal colour to the nearest Raw palette entry by RGB
distance. That can merge outline and shade colours, or map gear onto skin. In
[`frame-review/bridge.png`](../evidence/perfect-plex-receivers/frame-review/bridge.png),
the receiver's lower body reads as a black mass, with a separate raised leg
and light patches where Royal shows grey boots. **Needs a native-pixel
comparison of the inserted tiles against the Royal source per palette index.**

## Identity and independence gaps (all receivers)

- **Aliasing (static check S6):** Royal shares most receiving tiles across
  workers. For example, Lex (selector 10) has 10 private tiles out of 315, and
  Razor (8) has 26 out of 316. The prototype de-duplicates inserted tiles by
  decoded bytes. Extended to several receivers, that would make two Raw slots
  point at one private tile, which breaks acceptance check 3. De-duplication
  must stay **per slot**.
- **Direct counterparts** (Raw→Royal `1→3, 2→2, 3→9, 5→8, 6→10, 8→7, 12→1`):
  recipes are decoded only. Bret (1) and Scott Hall (5) carry user-edited gear
  that the Royal drawings lack, so they need re-authored gear on the Royal
  bodies.
- **Mr. Perfect receiving the Perfect-Plex** (mirror match) needs slot-12
  receiver art routed through the receiver stream, not the attacker stream.
- **Missing, needing authored art:** Luna (0), Bam Bam (4), Sting (7), Syxx (9),
  Nash (10) and Owen (11). Sting, Syxx and Nash must keep the approved edited
  heads and gear (`evidence/sting-native-heads`, `evidence/syxx-head-revision`,
  `evidence/nwo-art-revision`).

## Suggested order

1. PP-3 (shadow) and PP-1 (canonical facing): small, mechanical, prerequisites for judging anything else.
2. PP-2 per-frame registration, proven on Undertaker in both facings and near both ropes.
3. PP-4 exit transition, then PP-6 palette review.
4. Extend to the other direct counterparts with per-slot private tiles, then authored art for Raw-only slots.
5. PP-5 pin behaviour.

Every step needs a native capture from an exported ROM. The status in
`data/animation-coverage.json` changes only when that capture is committed.
