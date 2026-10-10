# WWF Raw SNES research tools

Original tools for decoding and reconstructing WWF Raw (USA) graphics.
We have recovered complete in-ring frames of **Bret Hart** and **Undertaker**,
including their palettes and object layouts. We also decoded interface graphics
such as digits, player labels and logo fragments.

The project now handles three formats: contiguous mode-1 streams, interleaved
mode-2 streams, and the zero-eliding mask packets used for in-ring sprite tiles.
The sprite packet encoder reproduces the original packets in the tested trace.
A same-size compressed tile edit has been reinserted and verified in the running
game; see [the evidence package](evidence/bret-tile-edit/README.md).
The [current movement prototype](evidence/bret-movement/README.md) covers
walking left/right and six observed running poses, with bare arms and a chest
logo on the visible front. Four gameplay tests verify 173 paired frames;
complete match coverage remains unfinished.
A [primary animation inventory](evidence/bret-animation-inventory/README.md) now
maps 527 directory entries; full outfit animation coverage remains unverified.
The [roster directory inventory](evidence/roster-inventory/README.md) identifies
all twelve selectable wrestlers through original-game selection and match
captures, with 1,561 native primary frame references checked. Lower-body and
complete action coverage remain unfinished. The
[secondary directory inventory](evidence/roster-inventory/secondary-graphics.md)
now maps 426 entries per directory and verifies 1,991 observed secondary
references; anatomical labels and the remaining common fallback ranges still
need research.
The [first controlled action maps](evidence/action-mapping/README.md) connect
Bret walking/punching/kicking and Undertaker walking to native frame-part
requests. The capture frontend now supports both controllers.

No ROM, raw extracted game data, emulator binary, or patched ROM is included.
The evidence package includes screenshots and a small IPS patch.
Supply your own local ROM; generated outputs stay in ignored output folders.
All extraction tools leave the input ROM unchanged.

## Recover a wrestler frame

See [the in-ring sprite notes](docs/in-ring-sprites.md) for a tested cold-boot
recipe: build the instrumented headless emulator, reach a match, capture video
memory and object/palette data, then assemble the sprites. No GUI is required.

The patch and build helper pin the emulator source revision. Each cloud task
already has an isolated checkout; use the existing checkout rather than
creating a Git worktree unless explicitly requested.

## Decode an interface block

Use Python 3.10+ and install Pillow for PNG previews:

```sh
python3 -m pip install -r requirements.txt
export WWF_RAW_ROM='/path/to/WWF Raw (USA).sfc'
python3 tools/decode_graphics.py "$WWF_RAW_ROM" --offset 0x2e9fdd --output outputs/digits --verify-reference
python3 tools/find_assets.py "$WWF_RAW_ROM" --output outputs/candidates --verify-reference
```

The extractor writes a binary, grayscale tile preview and JSON metadata.
Grayscale is a placeholder palette. Offsets refer to the ROM after removing a
copier header, if present. The static finder skips dynamic pointers, and a
successful decode does not establish a block's asset type.

## Validate

```sh
WWF_RAW_ROM='/path/to/WWF Raw (USA).sfc' \
WWF_RAW_TRACE='outputs/match' \
python3 -m unittest discover -s tests -v
python3 tools/validate_traces.py "$WWF_RAW_ROM" outputs/match
```

Twenty-one tests cover both interface codecs, hand-built and randomized
streams, sparse tile encoding, malformed input, sprite size/position/flip/
palette handling, and comparisons with original instructions and live game
memory. Five tests need local ROM and/or trace data and skip when unavailable.

The interface reference interpreter is intentionally limited. Independent live
SNES emulator traces now validate complete interface blocks and in-ring tile
outputs as well. Partial/yielded blocks are counted separately and skipped.

## Research status

[Editor goal and staged roadmap](docs/editor-roadmap.md) ·
[Interface compression](docs/compression.md) ·
[Initial code evidence](docs/research.md) ·
[In-ring sprites and reproducible workflow](docs/in-ring-sprites.md)

Not yet completed: common/lower animation inventories, semantic move mapping,
full wrestler replacement, gameplay changes, or complete game editing.
