# Bret animation inventory: research milestone

The verified original ROM has **527 primary directory entries**, **526 distinct
frame descriptors**, **5,470 tile IDs**, and **7,758 tile references** for Bret.
This is a primary-body asset inventory, not 527 independently identified moves.
Common/lower-body parts and the meaning of each action still need mapping.

The parser and source lookup matched **16,598 native lookup calls** from an
1,800-frame input sequence. Bret primary references observed in that sequence
were present in the directory inventory. This does not establish all-moves
coverage, nor that the outfit has been drawn on all those frames.

## Experimental private copies

`tools/build_bret_private_frames.py` copies the primary frames and tiles into
expanded ROM space and redirects Bret's directory, avoiding stock shared tile
writes. Baseline mode preserves every tile pixel. One cold-boot standing capture
matched the original PNG, VRAM, OAM, and CGRAM exactly; 3,210 private native source
calls in a longer run fetched the expected original tile bytes.

**This experiment is not ready for a gameplay patch.** Paired runs with the same
1,800-frame input sequence diverged in their match actions. Converting compressed
sources to direct copies and adding a lookup hook changes execution cost; the
cause and impact of the divergence need investigation. Static visual equality
alone is insufficient. The optional black recolor is an exploratory material
replacement and contains no complete logo/pad/tape artwork.

## Reproduce locally

After obtaining a WRAM snapshot from the documented original-ROM cold boot:

```sh
python3 tools/inventory_bret_frames.py "$WWF_RAW_ROM" \
  outputs/match/frame-002940-wram.bin \
  --calls outputs/match/tile_calls.jsonl --output outputs/bret-inventory.json
python3 tools/build_bret_private_frames.py "$WWF_RAW_ROM" \
  outputs/match/frame-002940-wram.bin --output outputs/private-baseline
```

The trace patch now records raw and compressed native tile lookups, descriptor
pointers, and actor slots. Output directories must be empty. All ROMs, full
inventories, extracted tiles, memory, and save states remain local and ignored.

## Finished-outfit requirement

The centered chest mark, elbow pads, and wrist tape must follow anatomy in every
pose: both directions, attacks, receiving attacks, grapples, throws, knockdowns,
getting up, running, and rope/ringside transitions. Each group needs actual game
recordings and checks for effects on other wrestlers. Unknown groups stay
unverified. Current edited-game evidence remains the standing pose and
[90-frame walking prototype](../bret-black-gear/walking-comparison.gif).
