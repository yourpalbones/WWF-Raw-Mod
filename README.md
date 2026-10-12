# WWF Raw SNES research tools

## Wrestler editor prototype

[Download WrestleEdit ZIP](https://github.com/yourpalbones/WWF-Raw-Mod/raw/refs/heads/main/downloads/WrestleEdit-v0.10.zip) · [WrestleEdit instructions](editor/README.md) · [View the app](evidence/app-interface/sprites.png)

Paint all 12 wrestlers’ original sprites, preview captured poses,
change selection portraits, monitor photos, bios, in-match names and existing
theme assignments, save projects and export playable ROMs or IPS patches. Full animation coverage remains incomplete.


[Scott Hall health-bar name proof](evidence/match-names/README.md) ·
[Custom theme melody proof](evidence/theme-music/README.md) ·
[Thirteenth-slot research](evidence/roster-expansion/README.md)

[Revised Scott, Nash and Syxx gameplay proof](evidence/nwo-art-revision/README.md):
v0.10 gives Nash black pants/boots, dark brown hair and small Outsiders chest
lettering. Syxx gets an improved red bandana, dark hair and chin detail, a red
chest mark and removal of stray white gear marks. Scott's plain trunk pieces
receive red detail while existing marked poses are retained. All three preserve
the native body artwork and expose 1,720 known frame pieces each. The editor
includes 130 Scott, 109 Nash and 146 Syxx captured full-body poses. Load your
current ROM, apply each wrestler's reference gear in Sprites, then save the
playable 6 MiB ROM. All six specials ran in Snes9x; 385 editor previews match
native captures pixel for pixel. v0.8 Scott and v0.9 mods upgrade successfully.
Exhaustive live interaction coverage remains unverified.

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
[Watch all twelve wrestlers' finishers and Mega Moves](evidence/roster-specials/README.md):
all 24 specials now have an original-game capture and native frame-part maps.
[Cold-boot recipes](data/roster-special-captures.json) reproduce the setups using
both controllers and verify snapshot hashes. This covers one working setup per
special; alternate variants, interruption/escape behavior and edited gear remain
unfinished. Bret's earlier [Sharpshooter](evidence/finisher-research/sharpshooter.md)
and [Mega Move](evidence/finisher-research/bret-mega.md) comparisons provide
additional condition checks and shared-frame findings.

The [first Shawn kick-finisher prototype](evidence/shawn-kick-prototype/README.md)
reroutes R to a standing kick with damage on contact and verified subsequent
get-up/walking. It still uses stock kick artwork; a finished Sweet Chin Music
animation and full match validation remain future work.
The [raised-leg extension update](evidence/shawn-superkick-pose/README.md) now
renders the experimental kick in both directions, with contact and recovery
checks. Additional graphics hooks shift timing slightly; this remains a prototype.

The [leaning full-body update](evidence/shawn-superkick-body/README.md) reposes
three torso phases and the impact leg while retaining stock timing. Both
directions connect and recover in loaded-state captures; fresh-boot setup
reproduction remains unresolved.

The [newly drawn eight-pose animation](evidence/shawn-superkick-animation/README.md)
replaces the entire experimental kick sequence with complete drawn body poses.
All eight assembled poses match the authored artwork in both directions; this
is still an artwork draft with native kick collision logic.

The [game-style artwork revision](evidence/shawn-superkick-style/README.md)
uses newly authored indexed sprites guided by the original Shawn art and the
viewed Sweet Chin Music reference. Both directions pass pixel and gameplay
checks; transitions and likeness still need visual refinement.

The [front-facing revision](evidence/shawn-superkick-front/README.md) opens
Shawn's chest toward the screen at impact and adds a native four-pixel
backward/forward preparation step. Actual emulator footage shows both directions.

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

Custom MIDI songs are available in v0.5: [complete-song playback proof and instructions](evidence/custom-midi/README.md).

Version 0.6 fixes layered MIDI imports and displays errors beside the button. [The supplied NWO MIDI imports and loops in the emulator](evidence/nwo-midi-import/README.md).

Version 0.7 fixes the effect-sample selection and misleading generic preview. [Hear the corrected NWO import in the emulator](evidence/melodic-music-fix/README.md).
