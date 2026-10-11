# All 12 wrestlers: finishers and Mega Moves

These are emulator gameplay captures from the verified **original USA ROM**, using two controlled joypads. All 24 special action words were observed. No ROM or game-memory edits were used for setup. Each paired GIF shows a finisher on the left and a Mega Move on the right; the overlay identifies the source capture frame.

This is a first verified setup for each special, **not complete coverage of every direction, target, multiplayer mode, interruption, escape or alternate Mega variant**. The original outfits are shown; edited gear has not been validated here. Undertaker's levitation capture verifies movement and recovery without opponent contact.

| Wrestler / gameplay proof | Finisher | Finisher action | Mega action |
| --- | --- | --- | --- |
| [Bret Hart](bret.gif) | Sharpshooter | `0250` | `0238` |
| [Undertaker](undertaker.gif) | Tombstone | `0252` | `023E` |
| [Yokozuna](yokozuna.gif) | Banzai Drop | `0254` | `0230` |
| [Bam Bam Bigelow](bam-bam-bigelow.gif) | Headbutt off the top rope | `0256` | `0244` |
| [Razor Ramon](razor-ramon.gif) | Razor’s Edge | `0258` | `022E` |
| [Lex Luger](lex-luger.gif) | Running Forearm | `025A` | `0232` |
| [Doink](doink.gif) | Whoopee Cushion | `025C` | `023C` |
| [Shawn Michaels](shawn-michaels.gif) | Slingshot Suplex | `025E` | `0234` |
| [1-2-3 Kid](123-kid.gif) | Moonsault | `0260` | `024A` |
| [Diesel](diesel.gif) | Jackknife | `0262` | `0236` |
| [Owen Hart](owen-hart.gif) | Sharpshooter | `0264` | `0240` |
| [Luna Vachon](luna-vachon.gif) | Luna Eclipse | `024E` | `022A` |

## Native frame verification

Each special has separate attacker and opponent views in its `*-mapping.json` file. The verifier resolves the game's primary and secondary directory pointers, checks every requested tile field against the ROM descriptor, and compares compressed tile outputs against the native decoder. The opponent view includes its unchanged frames where the move does not force a new pose. Counts in the two views refer to the same physical capture and must not be added together.

Across **24 physical captures**, verification checked **3,814 part requests** and **51,532 tile fields**, with no descriptor or codec mismatches.

## Reproduce from cold boot

[Input recipes](../../data/roster-special-captures.json) contain the complete setup chain, both controller schedules, and reference hashes for video, WRAM, VRAM, OAM and CGRAM snapshots. They contain no ROM bytes or save states. Use your own matching original ROM and the [pinned instrumented Snes9x build](../../tools/build_snes9x_trace.sh):

```bash
python3 tools/replay_special_capture.py "/path/to/snes9x_libretro.so" "/path/to/WWF Raw (USA).sfc" undertaker-finisher --output outputs/undertaker-finisher
```

Full cold-boot replays of `undertaker-finisher` (8 stages) and `123-kid-mega` (19 stages) matched all five reference hashes at every stage. The other 22 recipes were recorded from their verified capture chains and have not had a separate full cold-boot replay.

Setup stages replay normal gameplay. The final stage records video every six frames and native metadata. All stage endpoint hashes must match; a mismatch stops the replay. The recipe IDs follow `wrestler-finisher` and `wrestler-mega`, matching the filenames here.

The recipes use both shoulder buttons held for the Mega inputs. Direction presses are released before the final action button, following the game's input-history behavior. The Kid's working Mega setup is perched on the upper turnbuckle with a downed opponent nearby; the supplied guide did not explicitly mention that climb. This is a verified setup, not a claim that every other setup fails.

The move-input facts were supplied by the user from William Sigler Jr.'s SNES FAQ (revision 1.00, October 10, 1998). The complete FAQ is not republished. The coverage tracker keeps reported controls separate from observed results.
