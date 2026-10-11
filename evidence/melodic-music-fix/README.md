# Melodic sample mapping and preview fix — v0.7

The user reported that the imported NWO melody kept retriggering Razor's intro
screech, although the browser preview sounded like a melody. This was a real
importer error. Previous checks proved uploads, note execution, loops and non-silent
audio; they did not establish suitable musical timbre or correct tuning.

WWF Raw does not directly play MIDI files. The editor compiles MIDI into native
SPC note commands; the driver uses sampled sounds and instrument/envelope data.
A spoken wrestler name can be a BRR sample in the same system. The v0.6 importer
selected instrument 112 for each voice, whose descriptor chooses source sample
50. The user identified its audible result as Razor's intro effect. The old preview
used triangle oscillators and therefore hid this mismatch.

v0.7 defaults to native melodic instrument **113**, source sample **46**.
Instrument **116**, sample **47**, is offered as a melodic variation. Other former
choices are removed from the import dropdown because an audible sample is not
necessarily a melodic instrument. Old projects using effect samples migrate to
113 when loaded. Reopening a previously exported ROM preserves its bytes;
reimport the MIDI and export again to replace its already embedded effect sound.

[Hear twelve seconds of the corrected NWO song in Snes9x](nwo-in-game.wav).
[Workshop capture](workshop.png) shows its six-voice, 125.7-second import.
[Native NWO verification](nwo-verification.json) confirms the complete song reaches
loop starts at frames 52, 7597 and 15142 with all eight uploaded streams intact.

[Sample verification](sample-verification.json) checks the actual DSP registers
and physical sample-directory entry, not just an instrument number or an audio
peak. Instrument 113 plays MIDI notes 60 and 72 at measured spectral peaks of
261.12 and 522.24 Hz, respectively, close to C4/C5. Live NWO voices point to sample
46 rather than the former source 50. The live DSP source numbers are physical
voice-directory slots; the driver copies the selected source's start/loop pointers
into these slots in SPC RAM at page `0200`.

The preview decodes the actual BRR sample from the locally loaded ROM, preserving
its IIR filter arithmetic and sample loop, and plays it at a reference DSP pitch
of 661/4096 for MIDI note 60. Native reference snapshots report 660–662 due to
small envelope pitch variation. The browser BRR decoding matches the bytes and
arithmetic used in the native test. The test forbids generic oscillator creation.
Browser envelopes, Gaussian interpolation, echo and other DSP effects remain
approximate; the emulator recording is the reference for the final sound.

No game samples or ROM bytes are bundled in the editor. It reads the retained
original Razor bank's sample/instrument upload records from the user's ROM.
Public evidence contains only screenshots, recordings and verification metadata;
private ROMs, BRR/PCM data, save states and memory dumps remain local.

## Use the fix

[Download WrestleEdit v0.7](../../downloads/WrestleEdit-v0.7.zip), extract it and
open its HTML. Load the edited ROM, select the wrestler, choose **Melodic sound
(recommended)** under **Custom song**, and reimport the MIDI. Use **Preview game
sound** and **Save playable ROM**. The MIDI itself did not need another edit.

Projects use version 8 and accept earlier versions with the same base ROM.
The new read-only DSP probe adds 128 register bytes to native snapshots.

```sh
bash tools/build_snes9x_research_probes.sh "$WWF_CORE_BUILD"
python3 tools/verify_uploaded_midi.py "$WWF_RAW_ROM" downloads/nwo-snes-ready.mid "$WWF_CORE" "$WWF_CAPTURE_ROOT" --output outputs/nwo-melodic
python3 tools/verify_melodic_sample.py "$WWF_RAW_ROM" "$PITCH_TEST_CAPTURE" outputs/nwo-melodic/native --output outputs/sample-check
```

The pitch-test capture uses an imported 250-tick song with instrument 113:
note 60 at ticks 0–100, note 72 at 125–225. Load the stock Lex selector state,
press Left at frame 1, capture through frame 450 at intervals of 90 with audio.
