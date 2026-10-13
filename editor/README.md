# WrestleEdit — WWF Raw browser app

![WrestleEdit sprite editor](../evidence/app-interface/sprites.png)

## Easy download

[**Download WrestleEdit ZIP**](https://github.com/yourpalbones/WWF-Raw-Mod/raw/refs/heads/main/downloads/WrestleEdit-v0.14.zip)

1. Click the download link above.
2. Right-click the downloaded ZIP → **Extract All**.
3. Open the extracted **WrestleEdit** folder and double-click **WrestleEdit.html**. The app opens in your browser.
4. Click **Load ROM** and choose your original or edited WWF Raw USA ROM.
5. Choose a wrestler. Edit **Sprites** or **Portrait & bio**.
6. Under **Save & play**, click **Save playable ROM** and open the saved file in your emulator.

This is the browser editor, not an EXE. Once downloaded, it works offline. Use **Save project** to keep work editable; **Open project** restores it after loading the same ROM you started with. Your original ROM stays unchanged, and no ROM is bundled or uploaded. **Load ROM** also accepts a WrestleEdit edited ROM directly, keeping its existing portraits, bios, sprites and other assets. Checksums and supported asset locations are checked. Restore/reset returns to the ROM you loaded. Projects are tied to that starting ROM.

A Windows EXE preview was built, but GitHub release uploads are blocked by the cloud integration. Its local task-output link also failed in the chat client. The ZIP above is committed to the repository so it has a normal public download URL. [Desktop build details](../desktop/README.md).

To edit a sprite image externally, use **Save pose image**, edit that PNG, and import it back. Keep its dimensions, transparent outline and opaque visible pixels. Colors are matched to the wrestler's current palette. Import changes the selected pose's underlying tiles; it does not generate a full set of animations. Shared tiles can change other poses too, so preview them and test in an emulator.

## Sting conversion

Load your latest mod, choose the **Doink / Sting slot**, then **Sprites → Rebuild
Sting sprites → Save & play**. The donor-based rebuild uses Undertaker's native
body and flowing hair foundation, with authored Crow face paint, shoulder-length
dark hair, a black sleeveless scorpion shirt and black trousers/boots. It also
assigns Bret's Sharpshooter as the **Scorpion Deathlock** and updates the bio,
selection name artwork and health-bar name to **STING**. Use R near a downed
opponent's legs while their health is red.

The existing Hall/Nash/Syxx gear and other user edits are retained. This fourth
pack creates an **8 MiB ExHiROM**, tested in Snes9x. The rebuilt slot exposes 101
captured full-body poses and 1,720 parsed frame pieces. Every captured preview
was compared with native PPU snapshots. This remains an art pass: individual
poses still need refinement, the main/monitor portraits remain independent, and
the Mega Move has not been verified on this edited base.

[View the current head, gear review and complete Deathlock GIF](../evidence/sting-head-revision/README.md).
All tiles are privately replaced, including shared heads in the lower-body
directory and the finisher's entry poses. v0.14 replaces the flat face draft with native facial shading and Kid/Syxx
eye, nose and lip placement for the front head. It also fills the Deathlock shirt
to the waist and removes stray white pixels on shared leg tiles. This remains
a visual candidate. Older v0.12/v0.13 Sting mods keep their
previous preview layouts until you choose to rebuild.

## Scott, Nash and Syxx reference gear

1. Load your latest edited ROM and choose Scott Hall, Kevin Nash (Diesel slot), or Syxx (1-2-3 Kid slot).
2. In **Sprites**, click the reference gear button. Repeat for the other two wrestlers if wanted.
3. Open **Save & play** and click **Save playable ROM**.
4. Run that file in Snes9x. Your previous portraits, bios, names and songs are kept.

[See Syxx's native gameplay GIFs](../evidence/syxx-head-revision/README.md) and the
[previous trio captures](../evidence/nwo-art-revision/README.md).
Nash wears a red top with small Outsiders lettering, black pants/boots and dark brown hair. Syxx wears black/red with a red bandana, dark hair and a connected lower-face beard in registered head drawings; stray white gear marks are removed. Scott’s previously plain trunk pieces gain red detail.
The Syxx pass registers 269 head pieces using separate native face templates.
Occluded faces keep the covering arm intact. Some other head drawings still
need mapping; full live coverage remains unverified.
The reference pass retains native body shapes and animation timing, adds black
trunks with red detail, red boots and black/red knee-pad details, and removes the
old gold jewelry. Stubble, chest hair and new elbow-pad artwork are not included.
Tiny trunk markings remain a first pass, particularly in narrow or rotated views.

The gear button expands the ROM to 6 MiB using ExHiROM mapping. It checks the
original wrestler artwork before applying; conflicting body edits or engine hooks
are refused. You can then paint or import poses using the private detail tiles.
Full-body previews are grouped separately from upper/lower and common pieces.
The 1,720 parsed entries do not prove every live animation variant is covered.
Other wrestlers continue to use their existing sampled poses.

Projects saved after applying the gear belong to the new starting ROM. Save that
ROM too and load it before reopening the project. The button incorporates any
pending portrait, bio and song edits into that new starting ROM.

## Names and themes

In **Portrait & bio**, saving a bio updates the name above the health bar too.
For a previously renamed mod, click **Save bio** once, then export a new playable
ROM. You can also enter **SCOTT HALL** under **In-match name** and click
**Save match name**. The preview shows the small label used during matches.
Long names may need a shorter match name. Stock labels remain available through
restore/reset. The separate large name/logo graphic has its own controls.

Under **Theme song**, choose a built-in theme and click **Save theme**, then export
the ROM. Import a full MIDI song with the game’s melodic samples. Preview notes uses a
browser synthesizer; the actual instrument is heard in your emulator. MP3/WAV
import is not supported.

[Scott Hall in-game proof](../evidence/match-names/README.md) ·
[Custom melody proof and audio format](../evidence/theme-music/README.md) ·
[Thirteenth-slot experiment](../evidence/roster-expansion/README.md)

## Available previews

| Wrestler | Captured poses |
| --- | ---: |
| Bret Hart | 15 |
| Undertaker | 10 |
| Yokozuna | 7 |
| Bam Bam Bigelow | 4 |
| Razor Ramon / Scott Hall | 130 plus 1,720 frame pieces |
| Lex Luger | 11 |
| Doink / Sting | 101 plus 1,720 frame pieces |
| Shawn Michaels | 10 |
| 1-2-3 Kid / Syxx | 145 plus 1,720 frame pieces |
| Diesel / Kevin Nash | 109 plus 1,720 frame pieces |
| Owen Hart | 8 |
| Luna Vachon | 6 |

Scott, Nash and Syxx have 384 captured full-body poses combined and 1,720 known
frame pieces each. Rebuilt Sting adds 101 full-body poses and 1,720 pieces. The other wrestlers retain their existing samples. Layouts
use native positions, palettes and flips. Counts describe samples rather than
every live animation. **Play poses** cycles samples at a fixed preview speed;
use the emulator gameplay GIFs to judge native timing.

v0.9 and v0.10 ROMs retain their older captured previews until you apply revised
reference gear. A v0.10 mod needs only the Syxx update to reach v0.11; Sting is an optional conversion, rebuilt in v0.13. Existing
portraits, bios, names and songs are preserved; each button replaces that
wrestler's preset gear artwork. Save the new ROM before reopening a project
saved from it. v0.8 Scott ROMs are supported too.

## Editing behavior

- Paint with 15 visible palette slots, or select a slot and choose a new color.
  Colors snap to SNES 5-bit RGB. Transparency remains locked.
- The usage count reports visible pixels in the current pose. Palette changes
  recolor all uses of that slot, including skin or hair sharing it.
- Tile edits follow the same ROM source across loaded poses and wrestlers.
  The editor names other loaded wrestlers using an edited shared source.
  Shared users outside these captures remain unverified.
- Switching wrestlers retains your edits. Export includes all edited wrestlers.
- Undo covers tile and palette edits across the roster. **Reset all edits** clears
  the entire project. Save/load projects and native-resolution PNGs are supported.
- Version 5 projects include sprites, palettes, main portraits, monitor photos, name artwork, bios and theme assignments. Versions 1–4 remain supported. Versions 1/2 attach their palette edits to Bret; version 4 renamed characters receive generated name artwork.
- Export validates the original USA ROM hash, accepts an optional copier header,
  uses native sparse compression and updates the HiROM checksum. Compressed
  edits exceeding their original allocations are refused.

Full action coverage, palette ownership outside the verified captures, in-ring tile
relocation, automatic shared-asset isolation and an embedded emulator remain
future work. Test edited patches through the rest of the moves in an emulator.
Original sprite work is retained, including Shawn's original look.

## Selection portraits and bios

Choose a wrestler, then open **Portrait & bio**.

- **Choose portrait image** accepts PNG, JPEG or WebP. Images are centered and cropped
  to 128 × 120, reduced to 64 colors, and snapped to SNES color precision.
  Portrait colors are independent of the in-ring palette.
- Edit name, hometown (**From**), weight, height and the special move label, then
  click **Save bio**. The move label changes the displayed text, not move behavior.
- New names use uppercase letters and spaces, up to 14 characters. Original
  names such as `1-2-3 KID` and the 15-character `BAM BAM BIGELOW` can remain unchanged. Other fields accept supported
  uppercase text and punctuation; line limits are shown beside each field.
- Names are reused elsewhere in the game. Original shared bio strings are kept;
  edited text receives separate storage. The editor shows text-space usage and
  blocks export if the combined edited text will not fit (183 bytes).
- Undo, roster switching, project saving/loading and IPS export include these
  edits. **Restore portrait and bio** restores only the selected wrestler's
  selection assets. **Reset all edits** clears gear and selection edits together.
- An imported portrait, monitor photo or replacement name graphic expands the exported patch target to 4 MiB and relocates
  the new graphics. Your original ROM remains unchanged.

### Small photos, name artwork and themes

- Main portrait uploads also update the **Small monitor photo** by default. Uncheck that option to keep the two images separate. You can import another small photo, click **Use main portrait**, or restore it independently. These images are 48 × 48 with 31 visible colors; export updates the announcer and other verified picture directories.
- The typed name updates the main selection title and shared text. Separate name artwork is used by the Royal Rumble name card and other logo routines. **Save bio** generates new artwork by default when the name changes. You can turn that option off, enter a separate graphic name, upload a transparent logo, or restore the original. Generated names use lettering decoded from your ROM. Imports fit 256 × 224 and 15 visible colors; excessive tile counts are refused.
- **Theme song** lets you choose one of the 12 existing wrestler themes, then click **Save theme**. Undo and projects retain the assignment. This does not import or compose new music.
- **Load ROM** opens an edited mod directly. **Open edited ROM** remains available for importing edits onto a loaded original ROM. The uploaded test ROM retained its seven replaced portraits and Scott Hall, Syxx and Kevin Nash names; unchanged old logos for renamed wrestlers receive generated replacements. Save a project after recovery.

[See native monitor-photo and name-card proof](../evidence/profile-assets/game-comparison.png).

[See all 12 selection screens with editor-created changes](../evidence/selection-editor/selection-comparison.png).

## Developer validation

The editor needs only a browser. Optional automated verification needs Python,
Pillow, Playwright and Chromium, a local original ROM, the earlier research
captures and the new movement captures:

```sh
python3 tools/verify_editor.py '/path/to/WWF Raw (USA).sfc' \
  --capture-root /path/to/raw-analysis \
  --movement-root outputs/editor-roster-live \
  --chromium /usr/bin/chromium --page gear-workshop.html
```

This compares all 102 browser previews against native OAM extraction, checks
2,174 source tiles re-encode byte for byte, exercises editing and export for all
12 wrestlers, validates roster/legacy projects and shared-source warnings, and
checks invalid palette and compression overflow refusal. Private test ROMs and
screenshots are written under ignored `outputs/`.

See [roster evidence and reproduction](../evidence/roster-editor/README.md).
Regenerate the address-only manifest using `tools/build_roster_editor.py`, then
rebuild the standalone download with `python3 tools/bundle_editor.py`.

To verify portrait decoding/imports, bios, version 4 projects and expanded patch
output (no prior gameplay captures needed for these browser checks):

```sh
python3 tools/verify_selection_editor.py '/path/to/WWF Raw (USA).sfc'
```

Rebuild selection metadata with `tools/build_selection_manifest.py`, then run
`tools/bundle_editor.py`. [Selection evidence and emulator reproduction](../evidence/selection-editor/README.md).

Verify the app workflow, pose PNG imports, local playable-ROM download and mobile layout with:

```sh
python3 tools/verify_app.py '/path/to/WWF Raw (USA).sfc'
```

To verify monitor and logo imports, themes, version 8 projects and edited-ROM recovery:

```sh
python3 tools/verify_profile_assets.py '/path/to/WWF Raw (USA).sfc'
# Optional recovery check for a previous edited ROM:
python3 tools/verify_profile_assets.py '/path/to/WWF Raw (USA).sfc' --edited-rom '/path/to/WWF-Raw-edited.sfc'
```

[Profile asset formats and emulator evidence](../evidence/profile-assets/README.md).

Verify health-bar labels, shared graphics preservation and direct edited ROM loading:

```sh
python3 tools/verify_match_names.py '/path/to/WWF Raw (USA).sfc' --edited-rom '/path/to/WWF-Raw-edited.sfc'
python3 tools/verify_direct_mod_load.py '/path/to/WWF-Raw-edited.sfc'
```

Projects now use version 8. Older project versions are accepted when their base
ROM matches; renamed old bios gain a matching health-bar label on import.

## Custom MIDI songs (v0.5)

Load your ROM, choose a wrestler, open **Portrait & bio**, and scroll to **Custom song**. Choose a stock sound and whether it loops, then click **Import MIDI**. Use **Preview notes** for an approximate preview and **Save playable ROM** to hear the real game instruments in your emulator. Save a project to keep the imported notes editable.

The importer supports complete melodic MIDI songs with tempo changes, chords, note velocity and sustain, up to eight overlapping notes. It uses your chosen stock sound for all tracks. Percussion and pitch bends need to be removed before import; transpose can bring notes into range. Memory overflow stops the import without changing your project. Changing a theme affects other wrestlers assigned that theme.

[Full-song native playback and all twelve slot checks](../evidence/custom-midi/README.md). Reopening an exported ROM preserves its custom music; load the matching saved project to edit the notes again. Removing a pending custom song restores the loaded ROM's music.

Version 0.6 combines identical note layers at native timing resolution, keeping the strongest velocity. Import errors appear directly in the Custom song panel. The supplied `nwo.mid` now imports and plays its complete 125.7-second song in six voices, with no distinct notes dropped. [Exact-file native verification](../evidence/nwo-midi-import/README.md).

Version 0.7 fixes the instrument mapping: the default is a verified melodic sample, and **Preview game sound** uses that same game sample instead of a generic synth. Existing exported ROMs need the MIDI reimported and the ROM exported again; old projects migrate effect instruments to the melodic default. [Native NWO recording, pitch/sample checks and preview limits](../evidence/melodic-music-fix/README.md).
