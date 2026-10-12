# Native nWo art revision checkpoint

v0.10 art and verification are complete. The package is downloads/WrestleEdit-v0.10.zip; public proof is evidence/nwo-art-revision.

Changes:
- Nash: red top with small Outsiders lettering, black pants/boots, dark brown hair.
- Syxx: black/red gear, revised red bandana, dark hair and a three-row chin patch. Removed generic white gear marks.
- Scott: red detail on mapped trunk pieces that would otherwise be plain black; retained already marked poses.
- Kept native opaque masks, object geometry and move code. Existing portraits, names, bios and songs are preserved when applying the preset.

The old head filter used the first sprite object, although upper-head pixels can live in separate objects. build_native_anatomy.py compares corresponding native Nash/Syxx frames and uses original hair highlights to constrain head regions. native_gear_art.py authors details inside those regions. build_scott_trunk_anatomy.py propagates marked trunk pixel classifications through identical source tiles; scott_trunk_art.py supplies detail for the previously plain pieces.

Final private build: outputs/nwo-art-revision/final/syxx/gear.sfc.
SHA256: 640436cfd937129116b75ff794567064fdb8e65ff8fcdec62191791c3490cde0.
User input SHA256: 42434945cac01da84bac6c9ce1481b02a55a56f4f69e018dee7e7039d8a34994.

Verified:
- Six specials replayed from cold boot with controller inputs only.
- Thirty giving/taking recipes sampled; observed states are recorded, including recipes reaching only tie-ups or alternate moves.
- 130 Scott, 109 Nash and 146 Syxx captured previews match native OAM/VRAM pixel for pixel; all three expose 1,720 known frame pieces.
- Browser presets reproduce the native build byte for byte.
- v0.8 Scott and v0.9 mod upgrades reproduce the same build. v0.9 captured previews remain available before upgrading.
- Private PNG edits, project save/reopen, bio exports, all twelve custom MIDI slots and all twelve profile assets pass their regression checks.

Syxx's setup needed earlier X and climb/R inputs so the opponent remained dizzy. Those changes affect the capture recipe, not the game's move logic. Capture caches now check ROM/state hashes and exact input recipes before reusing a result.

Limitations: small logos and facial details are approximations at native resolution. Complete live interaction coverage is not proven. Early draft sheets are superseded by the final native captures.
