# Donor-based Sting checkpoint — v0.13

The replacement in Doink slot 7 now uses Undertaker selector 2 as its native
graphics foundation. All 1,720 descriptors and every referenced tile are private;
no unchanged donor references are left to be interpreted through Doink's packed
tile directory. The actor selector, normal moves and stats remain Doink's. The
six finisher entries retain Bret's submission assignment from v0.12.

The old conversion missed full-body heads in the secondary directory. The
submission entry also uses primary pieces 623 and 729–731, before the previously
reviewed 732–739 sequence. Authored makeup/hair covers all 14 visible heads:
primary 623, 729, 730, 731, 732, 737, 738 and secondary 617–622, 628. The native
trace and decoded private tiles verify the complete sequence, not only its hold.

`tools/sting_rebuild_art.py` authors the donor anatomy. `data/sting-head-seeds.json`
records independent face planes, eye sockets, cheek lines, lips, noses and hair.
Some obscured drawings preserve the native facial contour inside reviewed head
regions. The registrar matches 197 complete drawings under translation/reflection
and also carries masks through exact tile hashes. Foreground arms/gloves must
remain intact; do not infer makeup from a whole skin-connected component.

Scorpion placement uses reviewed front torso drawings and actual shirt regions,
independently of head translation. Shared submission torsos have explicit masks.
This remains an art candidate; exhaustive animation/matchup coverage is unproven.

## Storage and compatibility

| Purpose | File offsets, end exclusive |
| --- | --- |
| Primary descriptors | `600100–610000` |
| Secondary descriptors | `610100–620000` |
| Raw packets | `620000–6E0000` |
| Primary tile pointers | `6E0000–6EC000` |
| Secondary tile pointers | `6F0000–6FC000` |
| Primary / secondary frame tables | `6FC000` / `6FD000` |
| Worker program | `6FE000` |
| Marker | `6FF000`, `STING-NATIVE-GEAR2` |

There are 11,180 primary and 7,756 secondary tiles. Each namespace remains below
16,384, while the combined total is 18,936. Descriptor bank 60 selects the primary
pointer table; bank 61 selects secondary. Every field carries a private C000 tag.

Shared dispatchers support both new and v0.12 Sting. They check the four-byte
STIN prefix at the new/old markers, then route v0.12 to its unchanged `6CE300`,
`6CE400`, `6CE500` workers. This prevents another wrestler's gear update from
disabling old Sting. The editor likewise uses old Sting's full layout manifest,
while other legacy packs retain their captured layouts plus current known pieces.
Original Doink still exposes its eight stock captures plus 1,720 parsed pieces.

The browser replacement recipe reads native donor tiles from the supplied ROM,
checks their fingerprint, materializes all fields and supports the authored hair
outline changes. No original ROM/tile payload is bundled in the download. Imported
PNG edits preserve the outline of the loaded replacement. Save the rebuilt ROM
before restoring a project created against it.

## Verified outcomes

- Full Scorpion Deathlock, walk, ropes, punch, kick and ten successful giving/taking
  controller samples. Folder names inherited from Scott's recipes are not move
  names: Doink's A/B/X samples are Samoan drop / faceplant / vertical suplex.
- 101 editor captures match native OAM/VRAM pixels exactly.
- All 1,720 descriptors are fully private; 11,735 observed Sting tile requests
  have zero original-graphics fallbacks.
- v0.12 upgrade, private PNG/project roundtrip and offline ROM export/reopen.
- Original, v0.8 Scott, published v0.9, v0.10 and v0.12 load/export unchanged.
- Updating Syxx 2→3 alongside old Sting 1 preserves old Sting's bytes and native
  screenshot pixels exactly.

Rebuild SHA256:
`7cf1bbb37be4f5cf0b2fa93e8a0540333463952c480374b12cd4a28ad40713c9`.
Input was the prior export retaining the user's latest photos, profiles and songs.
ROMs and raw captures remain private under `outputs/sting-rebuild/`.

Tool entry points: `build_nwo_gear.py` selector 7 (supply Undertaker's verified
WRAM lookup), `register_sting_heads.py`, `capture_sting.py`,
`capture_gear_grapples.py --only sting`, `build_scott_editor_catalog.py
--selector 7 --donor-selector 2`, `verify_sting.py`, `verify_sting_identity.py`,
`verify_sting_previews.py`, and `publish_sting_rebuild.py`.
