# Syxx head revision checkpoint

User supplied a Syxx figure-package reference with long wet hair, tall red forehead bandana and connected moustache/beard. They rejected v0.10's small chin patch. New connected-beard draft was published in evidence/syxx-head-study; user says the bandana is better but the beard sits in the middle of the face. They offered to point out the nose. Do not publish this beard in the editor until the facial landmarks are corrected.

Original native head grid: evidence/syxx-head-study/original-head-grid.png. Its columns 0..16 map to native x=-8..8; rows 0..20 map to native y=-44..-24 in primary piece 1. User nose/mouth/chin coordinates will anchor beard placement instead of the crown-relative offsets that put it too high.

Work files:
- tools/syxx_head_art.py: current draft drawing. Beard depths 8..12 are too high and must be replaced by face-landmark anchors.
- tools/native_gear_art.py: calls the draft head drawing for selector 9, including shared heads when mapped. Nash/Scott art is unchanged.
- tools/build_nwo_gear.py: Syxx marker3, and reserved selected ranges are cleared before rebuilding so old-ROM upgrades remain byte-exact.
- data/syxx-common-heads.json: 133 shared head proposals from exact native head-source pixels and a thick-hair tile filter, with three hand-checked bounds in data/syxx-head-anchors.json. Several bounds are partial and need review before claiming coverage.
- data/syxx-registered-heads.json: 38 shared heads registered with original body tile sources. data/syxx-pixel-registered-heads.json confirms only piece705 matches a known own-body pose exactly at present. These registrations are not yet merged into the art module.
- tools/register_shared_heads.py and register_shared_heads_pixels.py are anatomical research; no source game pixels are published in their output.
- tools/find_shared_head_cores.py produces unreviewed proposals under outputs/syxx-head-revision/head-proposals.json. Do not blindly merge proposals; head/arm ambiguity remains in shared poses.

Current private draft build: outputs/syxx-head-revision/build/gear.sfc, SHA256 b6f78c946a4f3c4a6d221c79cfabf624bd3279335800d78400b35d4ced7302f6. It has not been verified in gameplay and is not a release.

The current public downloadable editor is still v0.10. v0.10 Syxx native captures and grapple snapshots were preserved in a lossless archive /tmp/wwf-raw-v010-syxx-evidence.tar.gz; all 110,027 files were compared byte-for-byte before approved deletion of the duplicate directories to free space. Original evidence and public GIFs remain committed. Can restore with tar when required; other Scott/Nash capture directories remain present.

Next: obtain/verify facial landmarks, place moustache below the nose and beard around the mouth/jaw, show corrected enlarged art, review shared-pose head boxes and orientations, replay Syxx specials/movement/grapples, update the Syxx editor manifest and old-version preview handling, run byte/pixel/export checks, then publish a new version. Do not change Nash or Scott art as part of this correction.
