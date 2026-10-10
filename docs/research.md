# WWF Raw (USA): initial graphics/compression investigation

ROM was read only; no ROM bytes or repository files were changed.

## ROM identity

- Size: 3,145,728 bytes (3 MiB), no 512-byte copier header.
- SHA-256: `0af7b0d3022acd24a1fb15865a076519f7f56e7a4b33f12b6d851b3a91e5388c`.
- Internal title: `WWF RAW` at file offset `0x00FFC0`.
- Mapping byte: `0x31` (FastROM HiROM).
- Header checksum/complement: `0x359E` / `0xCA61`; their XOR is `0xFFFF`. This checks the header pair, not the full ROM checksum.

## Static evidence that graphics loading uses compression

Addresses below distinguish CPU addresses from offsets in the headerless ROM.

1. At file offset `0x19D732`, code supplies input pointer `$9D:A774` and output pointer `$7F:0000`, then calls `$99:FF09`.
2. `$99:FF09` (file `0x19FF09`) copies source and destination pointers into direct-page locations `$7C..$7E` and `$80..$82`, clears `$90`, and calls `$AB:F5AE` (file `0x2BF5AE`).
3. `$AB:F5AE` reads a 16-bit field from the input followed by a mode byte. It selects a separate decoding path for mode `2`.
4. The decoding paths test command-byte bits `0x80`, `0x40`, and `0x20`. The code includes literal copies from the input, repeated-byte writes, descending-value runs, and copies from the output buffer. These establish a compressed command stream; the exact codec name is not yet identified.
5. The caller subsequently supplies output RAM `$7F:0000` and VRAM word address `$6000` to `$80:E659` (file `0x00E659`). This routine programs DMA source registers `$4302..$4304`, length `$4305`, target `$2118/$2119`, and starts DMA through `$420B`. Thus the decoding output is used as graphics data.

A second path at file `0x2AF30B` supplies `$AE:9FDD`, decodes to `$7F:0000` using the same wrapper, and transfers the output to VRAM word address `$6000`.

## Concrete input blocks

| CPU input address | ROM file offset | First three bytes | Header interpretation |
|---|---|---|---|
| `$9D:A774` | `0x1DA774` | `60 00 02` | Length field 96; mode 2 |
| `$AE:9FDD` | `0x2E9FDD` | `00 23 02` | Length field 8,960; mode 2 |

The routine returns the first field in A, and the first caller copies A to Y for the DMA length. This supports interpreting it as decoded byte length. Mode 2 writes with a stride of two and changes output position between passes; its exact interleaving and copy semantics still need validation.

## Follow-up extraction results

The mode-2 extractor is now implemented in `tools/decode_graphics.py`.
It restores graphics bytes by filling two interleaved byte lanes backwards.
The block at `0x2E9FDD` expands from 3,728 to 8,960 bytes and renders as
clean large digits 0–9 in SNES 4bpp format. The block at `0x1A0000` includes
player labels, RAW logo fragments, and interface tiles.

All seven statically discovered blocks match the original decoder machine
instructions executed in `tools/decoder_reference.py`. Nine tests also check
malformed input, all four command classes, overlapping and cross-lane copies,
and 100 randomized streams with even and odd output lengths. See
[compression notes](compression.md) for the block inventory and command format.

The limited instruction interpreter is not a full game emulator. Live game
RAM, exact palettes, complete sprite layouts, wrestler asset identity, and
reinsertion remain unverified. Only mode 2 is implemented; the original
routine also has another decoding path.

Raw planar previews and entropy alone were not used as proof of compression.
Compression is established by the command-decoding code and successful
reconstruction of recognizable graphics.

## Next milestone

Trace a wrestler graphics load, identify its source pointer and encoding,
compare extraction against live game RAM, and recover palette and frame
assembly. Keep extracted game data local; publish only original tools,
documentation, and patches.

## Reproduce

From the repository root, using a locally supplied ROM:

```sh
python3 tools/decode_graphics.py "$WWF_RAW_ROM" --offset 0x2e9fdd --output outputs/digits --verify-reference
python3 tools/find_assets.py "$WWF_RAW_ROM" --output outputs/candidates --verify-reference
python3 -m unittest discover -s tests -v
```

Set `WWF_RAW_ROM` to the local ROM path before running these commands.


## Subsequent breakthrough

The live-emulator investigation recovered complete in-ring Bret Hart and
Undertaker frames and identified a separate zero-eliding tile codec. Full game
memory comparisons now supplement the limited interpreter checks above. See
[in-ring sprite notes](in-ring-sprites.md) for current evidence and limitations.
