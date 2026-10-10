# First controlled action maps

[Watch the original-game captures](original-actions.gif): Bret walks right,
Undertaker walks left under controller two, Bret punches into empty space, then
Bret kicks into empty space. These are four separate replays of the same starting
state, three seconds each. The outfit is the original game's outfit.

We now trace the game's primary and secondary frame-part requests, including
requests whose tile data may already be cached. This connects an observed action
to directory references, rather than interpreting a tile count as move coverage.
The read-only instrumentation logs CPU 80:ECC1 and 80:ED19, selected table offset,
part ID, resolved frame descriptor and animation-profile pointer.

## Captured scope

Five cases each ran 180 frames, with snapshots every three frames: idle, player
one walking, player two walking, one standing punch and one standing kick. Start
at frame 1 unpauses the saved match. Action inputs start at frame 30. Walking is
held for 60 frames; punch (button 0) and kick (button 8) for eight frames.

| Observed action | Actor | Primary part IDs requested during frames 30–90 |
| --- | --- | --- |
| Bret walks right | Player 1 | 0006, 0009, 000C, 000F, 0012, 0015, 0018 |
| Undertaker walks left | Player 2 | 0021, 0024, 0027, 002A |
| Bret standing punch | Player 1 | 0006, 00BA, 00BD, 00C0, 00C3 |
| Bret standing kick | Player 1 | 0006, 00CF, 00D2, 00D5, 00D8 |

IDs are hexadecimal byte offsets into three-byte pointer entries, not move IDs.
The listed window includes recovery/idle requests, so it is not a canonical
move-definition table. Secondary IDs and the ordered request sequences are in
[the mapping report](summary.json). An idle pose can remain visible without a
new request; absence of requests does not mean absence of a sprite.

Only these observed facing, position and input combinations are mapped. Strike
connections, damage reactions, alternative strikes, grapples, throws, specials,
rope actions and complete animation coverage remain unfinished. This package
does not validate Bret's modified gear for these actions.

## Verification

- All 149 native part requests resolved to the same descriptors read from ROM.
- All 1,928 native tile-field references matched the requested descriptors.
- All 1,428 compressed tile events matched native decoded output and re-encoded
  byte for byte. These totals cover all actors across the five replays.
- With tracing enabled/disabled, idle and punch final snapshots matched exactly
  for PNG, WRAM, VRAM, OAM, CGRAM and register mirror.
- The updated frontend reproduced the earlier 90-frame player-one walking
  capture exactly for those same outputs.
- At frame 60, player-one walking preserved the opponent's tile buffer and
  player-two walking preserved Bret's tile buffer compared with idle.
- A direct cold boot reproduced the staged two-player starting snapshot exactly.
- All 21 existing tests passed with their local ROM/trace prerequisites supplied.

## Reproduce the two-player starting state

Build the pinned instrumented core with `tools/build_snes9x_trace.sh`. Supply the
verified original ROM in `WWF_RAW_ROM`. Each capture output must be empty.

```sh
WWF_TRACE_DIR="$PWD/outputs/two-player-ready" \
python3 tools/run_headless.py /path/to/snes9x_libretro.so "$WWF_RAW_ROM" \
  --output outputs/two-player-ready --frames 3400 --interval 3400 \
  --press 600:3 --press 900:3 --press 1020:5 --press 1100:8 \
  --press 1300:8 --press 1500:8 --press 1700:3 --press 1900:8 \
  --press-p2 2301:7 --press-p2 2600:8 \
  --press 2800:3 --press 3000:8 --press 3200:3
```

This reaches a paused two-player Bret-versus-Undertaker match. To reproduce the
punch case, reload `outputs/two-player-ready/frame-003400.state`, run 180 frames
with interval 3, and use `--press 1:3 --press 30:0:8`. For the kick use `30:8:8`;
Bret walking uses `30:7:60`; Undertaker walking uses `--press-p2 30:6:60` in
addition to player one's Start. Idle uses only Start. Set `WWF_TRACE_DIR` to each
new output's absolute path to collect `parts.jsonl` and tile traces.

The mapper expects folders named `actions-idle`, `actions-p1-walk`,
`actions-p2-walk`, `actions-p1-punch` and `actions-p1-kick` beneath TRACE_ROOT:

```sh
python3 tools/map_action_parts.py "$WWF_RAW_ROM" TRACE_ROOT \
  --output outputs/action-mapping.json
```

The frontend's recorded press tuples now include controller port:
`[port, start_frame, button_id, duration]`. Controller ports are zero-based.
Save states, raw memory and extracted graphics remain local and are not published.

Next: use the controlled opponent to capture successful strikes and reactions,
then grapples and throws, adding evidence-linked action coverage per character.
