# In-ring sprites: first complete frame

## Recovered result

A headless Snes9x run reached Bret Hart vs. Undertaker. At cold-boot frame 2,940,
the captured VRAM, OAM and CGRAM were byte-identical to the earlier save-state
replay snapshot used for extraction.

Two complete sprites were reconstructed from the captured tile and object
memory. The extractor uses the game's actual tile indices, object positions,
8x8/16x16 sizes, horizontal/vertical flips, and object palettes. It does not
crop the emulator screenshot.

| Character | Reconstructed bounds | Native size | OAM objects | Object palette |
|---|---|---|---|---|
| Bret Hart | x=70..99, y=74..154 | 30x81 | 38..54 | 0 |
| Undertaker | x=159..194, y=88..167 | 36x80 | 20..34 | 1 |

Bret's frame shows his pink/magenta top, black pants, white boots and raised
hands. Undertaker's frame shows his black outfit and purple gloves/boots.
These are one pose per wrestler, not complete animation sheets.

The assembled opaque pixels were also compared with the rendered game frame:
1,133 of Bret's 1,214 and 1,173 of Undertaker's 1,272 match within four RGB
levels. All differences are restricted to foreground ring rows 135–137 and
151–153, plus four Undertaker pixels on shadow row 167. The focused extractor
omits those occluding background/shadow layers; a full PPU renderer includes
them. No unexplained body-pixel differences remain outside those rows.

## The in-ring compression format

This is distinct from mode-1/mode-2 interface compression. The routine is at
CPU `$AC:F775` / ROM offset `0x2CF775`.

Each 32-byte SNES 4bpp tile packet starts with four mask bytes. Interpret each
byte's high nibble, then its low nibble, giving eight nibbles. Each nibble
represents four output bytes, using bits 8, 4, 2, 1 in that order:

- Set bit: read the next payload byte into that output position.
- Clear bit: restore a zero byte without consuming payload.

A packet occupies 4–36 bytes. The mask header and omitted zeros disrupt fixed
32-byte alignment, explaining why directly viewing these regions as ordinary
SNES tiles produces jumbled results.

`tools/decode_sprite_tile.py` implements both decoding and canonical encoding.
In a 90-frame gameplay trace, **717 tile events from 563 distinct ROM input
addresses** matched the live game output byte for byte. Re-encoding every one
also reproduced its original compressed packet byte for byte. A separate cold
boot additionally validated 154 tile events and 44 complete interface blocks.
The game also has a direct-copy path for raw tiles; this mask codec is not a
claim that every tile or every asset is compressed in the same way.

The tile lookup at `$AC:F6E4` maps a logical tile identifier to a source pointer.
The wrapper at `$AC:F959` selects the compressed or direct-copy path. The trace
records logical identifiers, source addresses and WRAM destinations for
compressed tiles. Full animation/frame-table mapping is still outstanding.

## Partial interface decoding

Some interface decoding calls intentionally yield before filling the whole
output block. The original routine returns with carry set and later resumes.
The patch records this as `partial`, and the validator skips these incomplete
snapshots. In the focused loading trace, 24 calls yielded and four complete
outputs matched exactly. Initial apparent mismatches were these partial
outputs, not a codec failure.

## Reproduce from a cold boot

Requires Python 3.10+, Pillow, Git, Make and a C++ compiler. Build a local core
using the pinned upstream revision and the read-only research patch:

```sh
python3 -m pip install -r requirements.txt
./tools/build_snes9x_trace.sh /tmp/wwf-snes9x
export WWF_RAW_ROM='/path/to/WWF Raw (USA).sfc'
WWF_TRACE_DIR=outputs/match python3 tools/run_headless.py \
  /tmp/wwf-snes9x/libretro/snes9x_libretro.so "$WWF_RAW_ROM" \
  --output outputs/match --frames 2940 --interval 2940 \
  --press 600:3 --press 900:3 --press 1100:8 --press 1300:8 \
  --press 1500:8 --press 1650:3 --press 1830:8 --press 1980:8 \
  --press 2200:3 --press 2400:8 --press 2600:3 --press 2730:3
python3 tools/extract_oam.py outputs/match/frame-002940 \
  --objects 38:54 --output outputs/bret
python3 tools/extract_oam.py outputs/match/frame-002940 \
  --objects 20:34 --output outputs/undertaker
python3 tools/validate_traces.py "$WWF_RAW_ROM" outputs/match
```

Each emulator run requires an empty output directory. The output includes
screenshots, native transparent sprite PNGs, enlarged previews, memory captures,
local save states, trace metadata and validation records. Keep ROMs, raw memory
dumps and save states local. Selected screenshots and small IPS patches are
published in the evidence packages alongside the original research tools.

The upstream core is `https://github.com/libretro/snes9x`, pinned to
`fae2fea08f74180759ef540ee94259213f503480`; its own license applies. The patch
only observes memory and exposes additional PPU snapshots. It does not modify
the game ROM or game memory.

## Remaining work

Small edits and a standing-pose gear prototype have now been reinserted and
verified in-game. Remaining work includes full animation/frame mapping and
checking shared assets across other wrestlers. Larger packets may require
pointer updates or relocation; the prototypes avoid growing any tile packet.

The cloud chat's image previews did not reach the user. Publishing screenshots
and comparisons in the GitHub evidence folders resolved delivery; the user
confirmed that those images were visible.

## Reinsertion verified in game

A reversible test copy changes the compressed Bret torso tile at file offset
`0x220152` (CPU `E2:0152`, logical tile `0x2918`). Reversing the bits in each
existing plane byte preserves the four-byte masks and the 13-byte packet size.
No pointers or asset allocation need changing. The original uploaded ROM is
unchanged (SHA-256 checked).

The edited copy updates the HiROM checksum to `0x3860`, using the 3 MiB mirrored
sum: the first 2 MiB once, the final 1 MiB twice. Its checksum complement is
updated too. A cold boot with the same input sequence reaches frame 2940.
The expected edited tile matches VRAM tile 6 exactly; only nine VRAM bytes differ
from the original run. OAM and CGRAM are identical. Five rendered screen pixels
change, within x=73–80, y=109–111 on Bret's torso. This establishes extraction,
encoding, reinsertion, loading, and visible rendering for this tile. It does not
establish that arbitrary replacement sprites will fit or that the game is fully
mapped.

Local outputs (ignored): `outputs/edit-test/bret-torso-test.ips`, the separate
edited ROM, `patch-report.json`, and `runtime-verification.json`. The IPS includes
only the tile packet and checksum pair; no full ROM is included in the patch.

## Black-gear prototype

[Reference-inspired standing-pose edit](../evidence/bret-black-gear/README.md)
changes ten mapped tiles and Bret palette color 6. It adds a black singlet,
centered pink/white chest mark, black elbow pad, black wrist tape and pink boot trim while keeping
the existing black tights and pink stripe. All ten edited tiles load exactly
as expected at cold-boot frame 2940. Only Bret's body pixels differ; OAM and all
other VRAM bytes remain unchanged. This is not a complete animation conversion.
