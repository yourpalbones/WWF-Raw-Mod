# Bret's first verified Mega Move

[Watch the actual Mega Move](bret-mega.gif): Bret starts perched on the upper-left
turnbuckle, somersaults across the ring, connects with a downed Undertaker, and
returns to his standing pose. This uses the original game and outfit.

[The comparison GIF](bret-mega-comparison.gif) replays the same directional and
B-button timing without shoulder modifiers on the left, and with modifiers on
the right. Without a modifier, Bret performs a regular diving attack and misses.
With a modifier, the distinct somersault sequence connects.

## Verified controls and timing

William Sigler, Jr.'s SNES FAQ supplied by the user gave the reported sequence:
Right, Right, Up with B, while holding L/R and with the opponent down.

The game's direction-history writer at CPU 80:E7DB–80:E825 records released
directions while either shoulder button is held. The matcher at 80:EB91 checks
the recorded masks and game-counter timestamps. The three-mask pattern at ROM
AD:D8B1 is Up, Right, Right in newest-first order. Consequently our successful
schedule releases Up before pressing B.

From the tested perched state, hold L, R, or both for frames 1–100, then:

| Start frame | Input | Duration |
| ---: | --- | ---: |
| 5 | Right, warm-up tap | 4 frames |
| 15 | Right | 4 frames |
| 25 | Right | 4 frames |
| 35 | Up | 4 frames |
| 41 | B | 8 frames |

The warm-up tap allows the saved setup's direction-history position to normalize
before the three actual command directions. We also triggered the move without
that tap in one replay; it is part of our reproducible recipe, not an established
universal requirement. The matcher accepts intersecting masks, so uncleared
history should not be treated as a reliable input sequence.

L alone, R alone and both produced identical sampled PNG, VRAM, OAM and CGRAM
across all 120 snapshots of their 360-frame replays. The otherwise identical
no-modifier replay did not trigger the Mega Move. At frame 120 the observed
Undertaker energy word (WRAM 0A7A) was 768 after the Mega Move and 928 in the
no-modifier comparison. This is an observed energy difference, not a general
damage formula.

## Animation and shared-frame discovery

The observed Mega Move action word at WRAM 06B4 was 0238; the perched starting
state was 0044. We map both participants in [the native report](bret-mega-mapping.json).
Five distinct replays passed 549 part-pointer checks, 7,800 tile-field checks and
5,929 compressed tile output/re-encoding checks. Attacker/defender views repeat
overall capture totals and must not be counted as independent replays.

Bret requested **15 shared primary parts at IDs 0750–077A, stepping by three**,
using directory selector 8. These are beyond the 062D cutoff of his original
527-entry primary inventory. Shared secondary requests included IDs 05FD–0624,
also beyond the 04FE secondary cutoff.

The trace additionally shows secondary IDs 0021 and 002A using selector 8 even
though those IDs are below 04FE. The code retains the selected X table offset
after a primary fallback; character identity and part ID alone therefore do not
always identify the secondary directory. The action mapper uses the actual
selected offset logged by the native core.

These findings extend the observed shared inventory, not its proven upper bound.
An editor needs these dependencies before changing shared tiles or relocating
frames. They also explain why Bret's original directory inventory could not
establish full animation coverage.

## Reproduce the perched state

Begin with the downed-opponent state at frame 600 of the
[verified attack setup](README.md). The following three replay stages were tested:

1. Run 360 frames: Left at frame 30 for 78 frames, Up at 130 for 45 frames,
   then Up at 240 for eight frames. Save frame 360.
2. Reload it and run 180 frames: Down at frame 1 for 16 frames, then Up at 80
   for eight frames. Save frame 180. Bret is near the corner, not yet perched.
3. Reload it and run 180 frames: Up at frame 1 for eight frames and Up at 60
   for eight frames. Save frame 180. Bret is now visibly perched (state 0044).

From that final state, capture the Mega Move:

```sh
WWF_TRACE_DIR="$PWD/outputs/actions-bret-mega-released-lr" \
python3 tools/run_headless.py /path/to/snes9x_libretro.so "$WWF_RAW_ROM" \
  --load-state /path/to/perched-state \
  --output outputs/actions-bret-mega-released-lr --frames 360 --interval 3 \
  --press 1:10:100 --press 1:11:100 \
  --press 5:7:4 --press 15:7:4 --press 25:7:4 \
  --press 35:4:4 --press 41:0:8
```

No ROM or game-memory value was changed to reach these states. Raw captures and
save states remain local. Mirrored corners, other receivers, broader timing
variants and the edited outfit remain unverified. The other eleven wrestlers'
Mega Moves still need their own captures.
