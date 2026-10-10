# Mode-2 graphics compression

This is a description inferred from WWF Raw (USA)'s code. No standard codec
name has been established. Source offsets apply to the headerless 3 MiB image
with SHA-256 `0af7b0d3022acd24a1fb15865a076519f7f56e7a4b33f12b6d851b3a91e5388c`.

The decoder begins at CPU `$AB:F5AE` (ROM offset `0x2BF5AE`). The wrapper at
`$99:FF09` passes its source and destination pointers through direct page.

## Header

| Field | Size | Meaning |
|---|---|---|
| Decoded length | 2 bytes | Little endian |
| Mode | 1 byte | Must be 2 for this implementation |

Output is filled backwards, first at odd byte offsets, then at even byte
offsets. Each write advances backwards by two bytes. This arrangement restores
interleaved bytes used in SNES planar graphics. It is separate from arranging
tiles into a complete image or sprite.

## Commands

| Control byte | Additional input | Meaning |
|---|---|---|
| `00` | None | End stream |
| `01–1F` | One value byte | Repeat value `(control & 31) + 2` times |
| `20–3F` | One value byte | Write descending values, starting at the given byte, `(control & 31) + 3` times; values wrap at 256 |
| `40–7F` | `(control & 63) + 1` bytes | Literal block |
| `80–FF` | One distance byte | Backreference; count `((control & 0x78) >> 3) + 3`, distance `(((control & 7) << 8) | next_byte) + 1` |

Literal byte order is preserved within the current output lane. Constant and
descending runs are written in reverse output order. Backreferences copy from
higher output addresses with a stride of two and permit overlap. When a source
start crosses the output end, it wraps into the other byte lane using the
original routine's parity adjustment. The standalone tool rejects references
to bytes that have not yet been decoded.

## Validated blocks

| ROM offset | Decoded bytes | Compressed bytes including terminator | Observation |
|---|---:|---:|---|
| `0x1A0000` | 29,504 | 5,002 | Player labels, RAW logo fragments, interface tiles visible in 4bpp preview |
| `0x1D7D4C` | 2,048 | 132 | Asset purpose not identified |
| `0x1D7DD0` | 2,048 | 215 | Asset purpose not identified |
| `0x1DA774` | 96 | 44 | Small graphics block; purpose not identified |
| `0x2E9FDD` | 8,960 | 3,728 | Large digits 0–9; 280 4bpp tiles |
| `0x2F0000` | 13,888 | 9,113 | Asset purpose/layout not identified |
| `0x2F2399` | 1,792 | 864 | Asset purpose not identified |

Every output byte in all seven blocks matches execution of the original
instructions in `tools/decoder_reference.py`. Additional synthetic streams
exercise all command classes and odd output lengths. Independent full-emulator traces now also validate complete blocks of both
modes. Partial/yielded calls are tracked separately. See [in-ring sprite
notes](in-ring-sprites.md) for the separate sprite format and runtime checks.


## Mode-1 support

`tools/decode_graphics.py` also supports mode 1: the output is filled backwards
contiguously rather than in two lanes. Literal, repeated-value and multibyte
backreference commands retain the same counts. Controls `20–3F` instead copy a
single byte from distance `(control & 31) + 1`; they are not descending runs.
Mode-1 blocks at `0x19AC80` and `0x2ADBE3` match original instruction execution.
The raw in-ring tile format is documented separately.
