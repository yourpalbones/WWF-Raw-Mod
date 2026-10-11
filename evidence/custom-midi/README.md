# Custom MIDI song importer — WrestleEdit v0.5

The editor imports complete melodic MIDI songs, compiles up to eight simultaneous
voices into native SPC sequences and writes separate relocated audio upload lists
for the twelve wrestler theme slots. It supports MIDI formats 0/1, musical ticks,
tempo changes, running status, note velocity, sustain, silence, long notes and
optional indefinite looping. Songs use the selected stock sound instead of MIDI
program assignments. The seven choices are native instrument codes
112, 113, 114, 117, 118, 120 and 121 from the Razor audio bank.

[Download the editor](../../downloads/WrestleEdit-v0.5.zip).
Load your original or edited ROM, choose a wrestler, open **Portrait & bio**,
scroll to **Custom song**, choose sound and loop settings, and click **Import MIDI**.
Save a project to preserve the editable notes; save a playable ROM for your emulator.
Changing sound or loop after import updates the pending song. Transpose is applied
when importing. The browser preview approximates pitches with a triangle oscillator;
it is not an emulation of the game's instruments.

[This original MIDI](original-theme.mid) has 640 notes, four simultaneous parts,
a tempo change and 92.8 seconds of music. [Listen to its first twelve seconds
played in Snes9x](imported-song-in-game.wav).
[The workshop screenshot](workshop.png) shows the imported song.
[Editor verification](editor-verification.json) covers malformed inputs, overflow,
sustain/running status, undo, project version 7, all twelve storage allocations,
untouched original samples/instruments and byte-exact edited-ROM reopening.
[All seven stock sound choices](instrument-verification.json) also pass native playback.
[Native verification](native-verification.json) confirms all eight uploaded streams
for each of the twelve theme slots, non-silent native audio and three loop-start
observations: frames 50, 5620 and 11191. Both repetitions occur after the full song,
not after a short preview.

## Boundaries

- Notes must fit MIDI pitches 32–95; transpose can shift them before import.
- More than eight overlapping notes, pitch bends, percussion-channel notes,
  malformed MIDI and songs that exceed memory are refused before an edit is saved.
  Export melodic tracks without drums or bends from your music program.
- MIDI program changes are replaced by the chosen stock sound. This is a native
  arrangement, not a General MIDI soundfont or MP3/WAV recording importer.
- Each song must fit its 20 KiB ROM slot, including its upload directory.
  SPC storage starts at `8C79` and stops before `FB00`; the driver, samples,
  instrument data and stack/scratch area remain intact.
- Replacing a theme slot changes it for any other wrestlers assigned that theme.
  Import selects the wrestler's original theme slot; built-in theme reassignment
  remains available afterwards.
- A reopened exported ROM preserves its music exactly. Save the project to retain
  the MIDI notes/settings for further editing. Removing a pending import restores
  the music in the loaded base ROM; it cannot reconstruct music replaced before
  that ROM was loaded.

## Storage and native commands

The original Razor bank upload list remains at file `039C37` (236599).
Common/sample/instrument uploads are copied by reference; its original song pointer,
header and eight streams are omitted. Each custom song uses ROM slot
`3C0000 + wrestler_id * 5000`, and redirects that theme's existing bank-directory
entry at `011903`. The native song header pointer is uploaded to
`24E0 + theme_id * 2`; its eight stream pointers address the relocated SPC data.
Stock records, graphics and other original assets retain their bytes.

The compiler emits `F5` instrument selection, `F2` level, absolute notes plus
byte durations, `C0`–`DF` rests, `FC` continuation, `F0` termination and `F6`
loop descriptors. Long sustained notes use continuation events. Empty voices stop
at song end; active voices loop independently at a common song duration.

Reproduce with locally owned files and the instrumented core:

```sh
python3 tools/verify_custom_music.py "$WWF_RAW_ROM" --output outputs/midi-test
python3 tools/verify_native_custom_music.py "$WWF_CORE" outputs/midi-test/all-12-custom.sfc outputs/midi-test/native-expectations.json "$WWF_CAPTURE_ROOT" --output outputs/midi-native
```

No ROMs, game samples, save states or memory dumps are published. The MIDI is an
original test composition; the WAV is a native playback capture.
