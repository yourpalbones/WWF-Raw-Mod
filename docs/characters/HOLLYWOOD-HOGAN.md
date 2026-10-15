# Hollywood Hogan conversion: inspected implementation and limits

Target: the prepared sixteen-slot ROM at commit `7ab43c5`. Its SHA-256 is
`ed9fe38492241bbd851d5faf81045d09014781cf277d117bd2a087d25a7b0bef`.
A byte-identical private input copy is retained at
`outputs/hollywood-hogan/rollback-original16.sfc`; Git branch
`codex/rollback-before-hollywood` preserves the pre-conversion code.

## Actual implementation

Hogan occupies zero-based slot 13 (fourteenth displayed worker), actor selector
26. The renderer distinguishes him from the referee/NPC through the existing
role guards. This conversion changes no guards or other executable code.

His source artwork is Genesis Royal Rumble World worker 6. The current port
contains **53 mapped Raw roots**, not an entire character animation library.
Each root resolves through `4A7000` and `4AB000` into private full-body
object descriptors in bank `54`, private tile pointers at `548000`, and
zero-eliding 4bpp packets. The physical sprite-packet pools are
`550000..558000`, `55B000..560000` and the optional `54A000..550000`.
The HUD atlas at `558000..55B000` is protected. Added-worker MIDI at
`543000..548000` is also protected.

The 32-byte gameplay palette is private at `4A6A00`: sixteen colors including
transparent index 0. Native 8×8 and 16×16 objects retain their original geometry;
this port budgets at most fifteen body objects plus the native shadow within
the existing seventeen-object / sixty-four-tile limit. No texture/material
system exists. Source pieces repeat within Hogan's own animation library;
they do not share this private tile directory or palette with other wrestlers.

Presentation comes from the 45-byte slot record at `708000 + 13*45`: portrait,
portrait palette, selection name graphics/map/palette, monitor/palette,
bio pointers, weight and theme assignment. The portrait is 128×120 with 64
colors; the monitor is 48×48 with 31 visible colors. Selection graphics use the
existing 256×224 image and tile-budget checker. Match names use a separate
64×8 bitmap and shared byte-indexed HUD atlas. Other name graphics remain
visually identical after the atlas rebuild.

Move tables, stats, AI, collision, animation timing and contextual leg-drop
routing remain byte-identical. The theme assignment and sound/music data are
unchanged. There is no new entrance/vest animation in this conversion.

## Visual choices

The supplied bareheaded in-ring references guide the native sprites: pale
blond side/back hair and horseshoe mustache, balding crown, original muscular
body, bare chest, full black pants, angular silver/white thigh lightning,
black knees/boots and white wrist wraps from the second reference. No bandana
or vest is added to gameplay. At this scale the forked lightning is deliberately
sparse and follows authored hip-to-knee axes in each lower-body source piece.

Clothing masks are attached to the actual source components, including explicit
boundaries for five whole-body landing drawings. Bare thighs are converted
into pants separately from skin on the torso/arms/face; hair is not converted
into black gear. Repeated source pieces receive one consistent design before
compositing. Pixel silhouettes and object coordinates remain exact. A portrait
art edit supplies the black nWo bandana, pale horseshoe mustache and chin
stubble; it is reduced to the actual native portrait palette and copied to the
monitor through the existing editor.

The supported shorter name is **HOLLYWOOD HOGAN**. Its fifteen characters fit a
native 240px selection title; the 64px HUD uses authored 3×5 letters. Bio text
is repacked within the existing unused-profile text pools. Other bio values,
including Hogan's hometown, weight, height and special move, stay unchanged.
The original editor accepts the saved fifteen-character name as its loaded
baseline; its ordinary new-name form still has a fourteen-character limit.

## Build and checks

Inputs remain private. No ROMs, decoded tile arrays or memory captures are
published. The body art study generated during development is not presented
as emulator evidence. Public images distinguish compiled-pose comparisons from
native gameplay captures.

```sh
python tools/build_hollywood_hogan.py prepared16.sfc royal-genesis.md --output outputs/hollywood-hogan
python tools/present_hollywood_hogan.py outputs/hollywood-hogan/Hollywood-Hogan-art.sfc private-portrait.png --output outputs/hollywood-hogan
python tools/check_hollywood_isolation.py prepared16.sfc outputs/hollywood-hogan/WWF-Raw-Hollywood-Hogan.sfc --output outputs/hollywood-hogan/isolation-verification.json
python tools/check_roster16_native_preview.py outputs/hollywood-hogan/WWF-Raw-Hollywood-Hogan.sfc private-native-captures --slot 13 --output private-native-check.json
python tools/check_hollywood_replay.py private-original-captures private-converted-captures --output private-replay-check.json
```

The body builder first checks each compiled input pose against its claimed
source composite; edited/different artwork is rejected rather than overwritten.
All 53 output poses decode exactly to their authored pixels. Real browser
portrait/monitor/name export and reload pass. All fifteen other workers have
identical decoded sprite/palette/presentation hashes. Explicit allocation checks
constrain every changed byte; executable and move-table regions are unchanged.
Two controller-only native runs produce 170/170 editor/body-pixel matches over
23 distinct roots. Player state bytes `0500..0DFF` and every other visible
OBJ record/color match the original run at all 170 snapshots. The second run
is a close-range striking test; it did not establish grapple/finisher coverage.

## Remaining limitations: not full game-ready signoff

The inherited import still uses standing fallback artwork for unmapped Raw
actions. The body-slam study includes sparse/incomplete-looking source drawings
at roots `55FC` and `5610`; their original silhouettes are preserved, not silently
replaced by a different wrestler. Paired grapples, receivers, rope transitions,
all taunts, the complete leg-drop sequence and expanded match modes have not
received full native animation signoff. These are existing import/coverage gaps,
so a successful gear build does **not** establish a complete game-ready Hogan.

The conversion covers all currently mapped artwork and the standing fallback,
with verified ordinary movement/strike playback. The remaining animation import
work must be finished before calling the whole character release-ready.
