# Finishers and Mega Move coverage

[Coverage tracker](../../data/wrestler-move-coverage.json) records a finisher and
Mega Move research entry for each of the twelve selectable wrestlers. Finisher
names come from the original character-selection screens. Mega Move names and
controls remain unconfirmed; those fields are deliberately empty.

No finisher or Mega Move is marked verified yet. Each needs setup/control checks,
attacker and defender frame sequences, recovery, and eventual edited-gear checks.
Submissions additionally need hold, escape and release coverage. Two wrestlers
having a Sharpshooter listed does not prove they share the same implementation.

## Verified setup progress

[Watch the actual setup captures](setup.gif): Bret approaches Undertaker, attacks
at close range and knocks him down, followed by a separate replay of a ground
attack. These are original-game animations, not a Sharpshooter or Mega Move.

We traced both wrestlers, rather than only Bret. The two distinct captures have
211 native part requests and 2,758 native tile-field references, all matching ROM
descriptors. Their compressed tile outputs and re-encoding also passed the
existing native comparison. [The mapping report](setup-mapping.json) provides
separate attacker and defender request sequences. Validation totals appear in
both views of each capture; do not sum those duplicate views as independent runs.

The inputs tested at the downed-opponent setup have not yielded a visually
confirmed submission. This does not rule out those buttons under different
position, timing, energy or opponent-state conditions. Repeated attacks also
move the opponent, so simply replaying buttons is not a reliable way to establish
a weakened-opponent setup.

## Reproduce

Start with the paused Bret-versus-Undertaker state from the tested
[two-player cold-boot recipe](../action-mapping/README.md).

For the first capture, unpause with Start at frame 1, hold Right at frame 30 for
55 frames, and Down at frame 90 for four frames. Press button 0 for eight frames
at 120, 160, 200, 240, 280 and 320. Run 360 frames with interval 3 and native
tracing enabled. Save this as `actions-bret-knockdown`.

For the second starting state, replay that same setup to frame 600, continuing
button 0 presses every 40 frames through 600. Reload that snapshot, hold Right
at frame 10 for ten frames and press button 0 at frame 30 for eight frames. Run
120 frames with interval 3 and native tracing enabled. Save this as
`actions-bret-groundattack`. The second clip is a separate replay, not a seamless
continuation of the first clip.

The action mapper now accepts custom case labels and actor slots:

```sh
python3 tools/map_action_parts.py "$WWF_RAW_ROM" TRACE_ROOT \
  --case 'bret-knockdown:Bret close-range attacks and Undertaker knockdown:0' \
  --case 'bret-knockdown:Undertaker receives attacks and falls:2' \
  --case 'bret-groundattack:Bret ground attack on downed Undertaker:0' \
  --case 'bret-groundattack:Undertaker receiving ground attack:2' \
  --window 1 360 --output outputs/finisher-setup-mapping.json
```

Next: establish the actual special-move input routines or obtain a usable SNES
control reference, verify the required setup conditions, and capture Bret's
Sharpshooter. Mega Moves require their own input/condition research and proof.
