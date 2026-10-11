# Theme music: assignment and a custom sequence proof

The editor's **Theme song → Save theme** assigns any of the twelve built-in
wrestler themes. [Earlier native command evidence](../profile-assets/README.md)
verified every assignment. The newer [v0.5 MIDI importer](../custom-midi/README.md) supports complete melodic songs. This page records the earlier research proof.

[Listen to the custom melody](custom-melody.wav). This is a short original
composition played by the actual WWF Raw audio driver in Snes9x. It replaces
Razor's eight sequence streams with one eight-note melody and seven stopped
streams, retaining the game's instruments and samples. The clip contains the
new melody, not a recording of Razor's original theme. It is a research proof,
not a replacement song selected by the user.

The [address-only audio map](audio-map.json) inventories 17 bank upload lists
and 21 song headers. Headers have 5–12 logical streams; the SNES DSP has eight
physical voices. The twelve wrestler themes use IDs 6–16 and 19. The CPU looks
up the required bank and uploads its records before sending song command `06`.

| Structure | File offset / SPC address |
| --- | --- |
| Bootstrap packet | ROM `010000` |
| Main driver | ROM `0100E0`, 6,112 bytes → SPC `0700` |
| Bank upload directory | ROM `011903`, 17 three-byte pointers |
| Song-to-bank IDs | ROM `011936`, 21 entries |
| Song-header pointer table | SPC `24E0`, two bytes per song |

A bank begins with a 16-bit record count. Each seven-byte upload record contains
a 16-bit byte count, a 24-bit ROM source and a 16-bit SPC destination. The bank
contains BRR/sample data, sample-directory entries, instrument and envelope data,
a song header and voice sequences. The driver contains the signature
`SNDDRVR / REN AND STIMPY`; this is an observed internal label, not proof of an
author or complete compatibility with another game.

The sequence reader is at SPC `1A3B` and dispatch at `186B`. This proof verifies
`F2` channel level, `F5` instrument selection, absolute note bytes `80`–`BF`
followed by a duration, and `F0` stream termination. Packed relative notes,
rests, loops and other commands exist; their complete conversion semantics have
not been verified. Absolute note indices in the proof are
`60, 64, 67, 72, 67, 64, 62, 60`, each for 20 ticks.

[Verification](verification.json) confirms all eight uploaded streams, the eight
new note reads in order, termination, non-silent native audio, and no ROM changes
outside those sequence streams and the checksum. Samples, instruments, pointers
and upload sizes are unchanged.

Reproduce locally:

```sh
bash tools/build_snes9x_research_probes.sh "$WWF_CORE_BUILD"
python3 tools/inventory_audio.py "$WWF_RAW_ROM" --output outputs/audio-map.json
python3 tools/build_theme_melody_probe.py "$WWF_RAW_ROM" --output outputs/melody-probe
WWF_AUDIO_PROBE=1 WWF_TRACE_DIR="$PWD/outputs/melody-native" python3 tools/run_headless.py "$WWF_CORE" outputs/melody-probe/theme-melody-probe.sfc --output outputs/melody-native --load-state "$WWF_CAPTURE_ROOT/roster-menu-cycle-settled/frame-001500.state" --frames 1400 --interval 1400 --press 1:6 --audio
python3 tools/verify_theme_melody_probe.py "$WWF_RAW_ROM" outputs/melody-probe outputs/melody-native --output outputs/melody-proof
```

The optional probe exposes read-only SPC RAM and logs reads in Razor's sequence
range. The v0.5 editor now includes a native MIDI song compiler with timing,
loop, instrument and SPC memory checks. Importing arbitrary MP3/WAV audio requires
sample conversion and memory planning; it is not the same operation as replacing
a native note sequence.
