# Sting replacement checkpoint

WrestleEdit v0.12 converts Doink selector 7 into the first playable Crow Sting
gear pass and assigns Bret selector 1's submission. User-edited portraits/songs
and existing Hall/Nash/Syxx packs remain preserved.

Finisher type, attacker action, victim action, setup and offsets are the six
two-byte selector entries at `2DD36F`, `2DD387`, `2DD39F`, `2DD3B7`, `2DD3CF`,
and `2DD3E7`. Only their Doink entries (`table + 14`) are changed. Bret's entries
remain intact. Actual controller replays observed action 592, atomic drop 206,
and receiving back suplex 212. No state-memory writes are used for the proof.

Sting storage is isolated above the previous 6 MiB packs:

| Purpose | File offsets |
| --- | --- |
| Descriptors | `600100–620000` exclusive |
| Raw tile packets | `620000–6C0000` exclusive |
| Tile pointers | `6C0000–6CC000` exclusive |
| Primary / secondary tables | `6CC000` / `6CD000` |
| Worker program | `6CE000` |
| Signature | `6CF000`, `STING-NATIVE-GEAR1` |

The result is an 8 MiB ExHiROM with the bank-zero mirror and both checksums.
Six MiB exports still weight the final 2 MiB twice; eight MiB exports sum all
bytes once. Shared dispatchers cover four packs. Worker writes outside a smaller
ROM's allocation are skipped. Applying other packs after Sting retains 8 MiB.
1,648 directory entries receive art changes, with 14,517 deduplicated raw tiles.
Native opaque masks and descriptor positions remain unchanged.

Art is authored in `tools/sting_gear_art.py`. Hair-colored islands locate Doink's
own heads. Shared heads use reviewed anatomical bounds, with explicit face/torso
regions for Sharpshooter pieces 732, 737 and 738. Do not claim exhaustive head
mapping or anatomy validation. This is still a first art pass; portraits remain
independent and unchanged by the preset.

Reproduction tools: `build_nwo_gear.py` selector 7, `capture_sting.py`,
`capture_gear_grapples.py --only sting`, `build_scott_editor_catalog.py` selector 7,
`verify_sting.py`, `verify_sting_previews.py`, and `publish_sting_proof.py`.
Snapshots/ROMs stay in ignored outputs. The public evidence contains no ROM or
save states. All 59 captured previews match native PPU snapshots; offline ROM
and project/PNG roundtrips passed. Existing MIDI tests passed on the expanded
layout, including twelve independent custom songs.

The stock Doink Mega input recipe failed on this edited base both with the new
submission and with original Doink finisher tables restored. Investigate its
setup/conditions separately; do not label the Mega as verified or assume the
finisher reassignment caused that failure.

Final native gear SHA256:
`e6a2e2b513d26eec974d60f425f1bd666757417fdb3594c62ca599876cfca476`.
The export with Sting profile/name edits used in the captures:
`f0bf584f736702b47bb800d989960704471a9633b323a2884c9360e0a2fd6e8f`.

Generated older captures were losslessly archived with every file SHA checked
before approved cleanup. User attachments and original research were retained.
The current native replay and grapples are under `outputs/sting/`.
