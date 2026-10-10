# Bret's Sharpshooter: first verified finisher capture

[Watch the Sharpshooter](sharpshooter.gif) in the unmodified original game:
entry, turning Undertaker over, hold, automatic release and Bret returning to
his standing pose. [The second capture](sharpshooter-recovery.gif) gives
Undertaker repeated controller inputs and shows him getting up afterward.
Those inputs did not visibly escape the hold early; early escape remains
unverified. A Y press by Bret during the hold did not establish manual release.

The user supplied a SNES move reference: William Sigler, Jr., *WWF RAW FAQ/MOVE
LIST*, revision 1.00, October 10, 1998. Its reported conditions guided these
tests: a downed opponent with red energy, Bret near the legs, then R. Only
factual input/condition records are saved; the full FAQ is not republished.

## What was verified

- Left for 25 frames moved Bret into the near-leg setup; R for eight frames at
  frame 60 triggered the Sharpshooter. Moving left for only five or fifteen
  frames from the same starting state did not trigger it.
- A higher-energy comparison used the same directions and R timing. At frame
  57, both captures had identical player/opponent coordinates, actor flags and
  character selectors. The observed opponent energy word at WRAM 0A7A was 792
  in the comparison and 92 in the successful capture. The higher-energy case
  did not perform the Sharpshooter. This does not establish the exact cutoff.
- Both participants' primary and secondary part requests are mapped, including
  attacker release and the receiver's subsequent get-up in the active-input case.
- Across three distinct captures, all 702 native part requests, 7,903 tile-field
  references and 5,914 sparse tile output/re-encoding events passed verification.
  Attacker and defender views duplicate each capture's overall check counts;
  do not sum all five report entries as five independent replays.

[The mapping report](sharpshooter-mapping.json) contains ordered part references
and input schedules. This verifies the captured original animations, not the
modified outfit, every receiver, mirrored directions, rope breaks or early escape.
Owen's Sharpshooter requires its own capture despite having the same move name.

## Reproduce without changing game memory

Start from the paused two-player Bret-versus-Undertaker state in the
[cold-boot recipe](../action-mapping/README.md). Use the verified
[close-range attack setup](README.md): unpause at 1; Right at 30 for 55 frames;
Down at 90 for four frames; button 0 at 120 and every 40 frames through 600,
eight frames per press. Save frame 600.

Reload that downed-opponent state. Over 3,000 frames, repeat this pair every
100 frames: Right for ten frames at `100*i + 1`, then button 0 for eight frames
at `100*i + 30`, for `i = 0..29`. This lowers Undertaker's energy through normal
gameplay. The tested workflow split this into 2,400 and 600 frames, reloading
the intermediate state. The final energy word was 76; it rose to 92 while
positioning Bret before the R input. No health value was written by our tools.

Reload the final state and capture the move:

```sh
WWF_TRACE_DIR="$PWD/outputs/actions-bret-sharpshooter" \
python3 tools/run_headless.py /path/to/snes9x_libretro.so "$WWF_RAW_ROM" \
  --load-state /path/to/red-energy-state \
  --output outputs/actions-bret-sharpshooter --frames 600 --interval 3 \
  --press 10:6:25 --press 60:11:8
```

For the recovery case, replay from that same state and additionally send
controller-two buttons 0 and 8 for eight frames at 100, 120, 140, ... 440.
For the high-energy comparison, use the intermediate state after only 400
frames of the repeated ground attacks, then use the same Left and R inputs.
Capture 360 frames for this comparison. These states remain local.

The structured coverage tracker now marks Bret's captured finisher inputs,
setup, attacker/defender sequences, hold, automatic release and observed recovery
as verified. Early escape, full variants and edited-gear checks remain pending.
Bret's [Mega Move](bret-mega.md) was verified in subsequent research; the other
Mega Move entries remain unverified.
