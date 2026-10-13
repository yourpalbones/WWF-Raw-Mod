# Sting and Lex Luger themes — ready for WrestleEdit

[Download both prepared MIDIs in one ZIP](https://github.com/yourpalbones/WWF-Raw-Mod/raw/refs/heads/main/downloads/Sting-and-Luger-themes.zip)

| Theme | Ready MIDI | Duration | Native voices | Hear it in Snes9x |
| --- | --- | ---: | ---: | --- |
| Sting | [sting-snes-ready.mid](https://github.com/yourpalbones/WWF-Raw-Mod/raw/refs/heads/main/downloads/sting-snes-ready.mid) | 96 seconds | 5 | [15-second recording](sting-in-game.wav) |
| Lex Luger | [luger-snes-ready.mid](https://github.com/yourpalbones/WWF-Raw-Mod/raw/refs/heads/main/downloads/luger-snes-ready.mid) | 115.5 seconds | 8 | [15-second recording](luger-in-game.wav) |

These are prepared versions of the supplied files. Both original arrangements
contain channel-10 percussion, which the importer rejects. The prepared files
omit those drums and retain the melodies, bass, chords, tempo and song length.
No transpose is needed.

Luger's file also has redundant simultaneous notes. Combining 62 equal-pitch,
equal-onset notes retains the longest sustain and highest velocity, allowing
the native arrangement to fit eight voices. Six remaining exact unisons across
different tracks are combined by the editor's existing importer. Distinct note
pitches, onset times and sustain coverage are preserved. Original metadata and
credits remain in both MIDIs, including the Luger file's Dan Estes credit.

## Import

Use the [current WrestleEdit download](https://github.com/yourpalbones/WWF-Raw-Mod/raw/refs/heads/main/downloads/WrestleEdit-v0.14.zip).

1. Load your latest mod and select **Doink / Sting** or **Lex Luger**.
2. Open **Portrait & bio**, then scroll to **Custom song**.
3. Choose **Melodic sound (recommended)**, set **Transpose** to **0**, and leave
   **Loop song** checked.
4. Click **Import MIDI** and choose that wrestler's prepared file.
5. Repeat for the other wrestler, then **Save & play → Save playable ROM**.

The importer converts the MIDI into the game's native SPC sequences. All parts
use the chosen game instrument; General MIDI guitar/string assignments are
replaced. The browser preview remains approximate. The recordings above are the
actual emulator result. Replacing a theme slot affects anyone assigned that theme.

## Verified

Both files import through the downloaded app with the network disabled, save
together in a project and export into the current 8 MiB mod. Reopening the ROM
preserves it byte for byte. Sprites, profiles, original instruments/samples and
the other theme banks retain their bytes.

Native playback verifies all eight uploaded streams per song, the correct
melodic source sample 46, and two complete loops. Loop starts occur at frames
48 / 5810 / 11573 for Sting and 54 / 6988 / 13924 for Luger. Active voices use
the melodic sample rather than Razor's intro effect.

[MIDI preparation checks](preparation.json) · [Editor checks](editor-verification.json) ·
[Native playback checks](native-verification.json)

Reproduce with locally owned ROM/core files:

```sh
python tools/verify_supplied_themes.py "$WWF_RAW_MOD" --output outputs/theme-import
python tools/verify_theme_playback.py "$WWF_CORE" outputs/theme-import/both-themes.sfc outputs/theme-import/native-expectations.json "$WWF_CAPTURE_ROOT" --output outputs/theme-playback
```
