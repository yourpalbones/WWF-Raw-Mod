# Layered MIDI import fix — v0.6

The supplied `nwo.mid` parsed correctly in v0.5 but failed the eight-voice limit:
it had nine overlapping notes, including duplicate layers. The error was shown
only at the top of the page, leaving the visible Custom song panel saying
“No custom song added.”

The importer now combines notes that have identical native start/end times and
pitch, retaining the strongest velocity. This is appropriate because all MIDI
tracks use the selected native game sound. Different pitches or timings remain
separate; real chords exceeding eight voices still fail atomically. Duplicate
combining happens after timing quantization to the driver's 50 Hz resolution.
Errors now appear beside the import button with a live status announcement.

[Successful import screenshot](import-success.png) and
[verification](verification.json) come from the exact supplied file through the
packaged v0.6 browser app. It contains 1,131 note events; 412 duplicate notes are
combined into 719 distinct notes, using six voices over 125.7 seconds. No distinct
notes are discarded. The native Snes9x driver uploads all eight streams and reaches
loop starts at frames 52, 7597 and 15142, confirming complete playback and two
repetitions. Project reload and exported-ROM reopening retain the song exactly.

The existing 92.8-second, four-part MIDI tests also pass, including tempo,
sustain, running status, malformed input refusal, genuine polyphony overflow,
undo, twelve independent theme slots and untouched original samples/instruments.
The regression now verifies strongest-velocity duplicate combining and visible
inline failures.

Download [WrestleEdit v0.6](../../downloads/WrestleEdit-v0.6.zip), load the ROM,
choose a wrestler, and import the same `nwo.mid` under **Portrait & bio → Custom song**.
Save a project and a playable ROM. The supplied MIDI, ROM, converted streams,
SPC memory and audio captures remain local; only the screenshot and verification
metadata are published.

Reproduce using locally owned files:

```sh
python3 tools/verify_custom_music.py "$WWF_RAW_ROM" --output outputs/midi-regression
python3 tools/verify_uploaded_midi.py "$WWF_RAW_ROM" "$USER_MIDI" "$WWF_CORE" "$WWF_CAPTURE_ROOT" --output outputs/uploaded-midi
```
