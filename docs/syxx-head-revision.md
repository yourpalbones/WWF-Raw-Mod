# Syxx head revision checkpoint — v0.11

The user marked the original primary1 eyes (grid row9, columns9/10 and12), nose (col11,row11), and mouth (col11,rows13/14), then approved the corrected lower-face beard. Native coordinates map columns0..16 to x=-8..8 and rows0..20 to y=-44..-24. Jaw row15 is inferred. The accepted front mask remains in data/syxx-face-seeds.json template1.

v0.11 uses 22 separately authored source templates and 269 registered head pieces, including 9 occluded heads whose covering arm receives no beard. Registration requires every non-skin feature and every skin-mask pixel to match, with at least 75 percent identical original shades. The template1 front texture is exact in its original 31 copies; other templates and shade variants expand the pass. Bandana positions and beard masks transfer with the face transform. Painting is limited to tile fields participating in the matched face core. Verified manual bounds in data/syxx-head-anchors.json replace misleading body/arm boxes, including six recovered full-piece heads. Limb/weapon/effect-only boxes with insufficient native hair receive no bandana. Native brown hair highlights are darkened only when surrounded by original hair.

Current private native build: outputs/syxx-head-revision/final/syxx/gear.sfc, SHA256 d4c644214e02b6d0d5762b2c34c26efebfea52e8056165d36b577854dc664b0c. Syxx marker SYXX-NATIVE-GEAR3; 1,419 modified entries and 7,538 private raw tiles. Scott/Nash art is unchanged from v0.10. Reserved frame/packet/pointer ranges are cleared when upgrading an older 6 MiB input so native/browser outputs agree byte-for-byte.

Validation completed:
- Syxx cold-boot controller replays: finisher 608, Mega 586, walk, running/ropes, punch, kick. Ten giving/taking grapple controller samples also replayed. give-back-suplex remained a tie-up; do not claim ten successful moves.
- All 1,720 original opaque masks preserved; 1,247 visible protected feature pixels preserved across 269 registered pieces.
- Browser presets match the native build byte-for-byte. 384 native OAM/VRAM previews pass: Scott 130, Nash 109, Syxx 145. Unchanged Scott/Nash v0.10 fixtures are reused; Syxx was replayed on this ROM.
- v0.8 Scott, published v0.9 and v0.10 upgrades pass. Legacy manifest records are arrays keyed by marker, preserving older captures before upgrading.
- PNG/project roundtrip, direct edited-ROM reload and 6 MiB profile export pass. Twelve-slot custom MIDI and twelve-character profile regressions pass.
- ZIP integrity and packaged HTML verified; network disabled before ROM load/edit/export. Direct file:// navigation is blocked by cloud Chromium administrative policy, so packaged HTML was served locally for the test; no policy was altered.

Published package: downloads/WrestleEdit-v0.11.zip plus downloads/WrestleEdit.zip. Evidence: evidence/syxx-head-revision (native screenshot,before/after,eight GIFs,verification JSON). The original approved face study remains under evidence/syxx-head-study.

Private capture backups (do not publish):
- /tmp/wwf-raw-v010-syxx-evidence.tar.gz: v0.10 Syxx captures/grapples, 110,027 files, individually SHA-verified before approved deletion of duplicate directories.
- /tmp/wwf-raw-syxx-v011-first-replay.tar.gz: first v0.11 replay plus ROM/metadata, 110,216 files, individually SHA-verified; archive SHA e5fcc8ab411475d1766cc8703be68d652cfc9c2cbbff996a3c71e70136f08c92. Duplicate first-pass capture/grapple directories were removed after automatic approval; corrected replays now occupy their paths.
- v0.9 Syxx/Nash backups are also in /tmp. Preserve user uploads and /workspace/raw-analysis.

Fixture caution: outputs/nwo-gear/complete/syxx/gear.sfc is the published v0.9 layout (SHA fe2b967f242f5d3e1172b7b6b3bde634380da764e1be5c7575c246c9e44463f2). outputs/nwo-gear/final/syxx/gear.sfc is an earlier unnormalized research ROM using bank 55; it is not the published v0.9 upgrade fixture.

Remaining work: other visible head drawings still need registration, and complete live animation/opponent/interrupt coverage is unverified. Data for exploratory body registration and hair-core proposals is not used as a blanket paint rule. Do not claim all animations or every move is finished. Keep the game-native silhouettes/style and verify future corrections against actual face landmarks, not skull-height guesses.
