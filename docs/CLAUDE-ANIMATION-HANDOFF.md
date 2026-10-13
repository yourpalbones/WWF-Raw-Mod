# Claude Code task: complete independent wrestler animations

## Goal

Help finish WWF Raw's expanded roster while preserving its original SNES art
style. The immediate priority is Mr. Perfect and the Perfect-Plex. The user
reports visible gaps between sprite pieces; the latest native Undertaker
receiving prototype looks closer to Royal Rumble, but is still not correct.
Do not equate a successful damage test with a finished animation.

Read the repository's applicable agent instructions first. Work on a separate
branch and submit reviewable commits or a PR. Coordinate file ownership with
Codex before editing the same implementation files. This document is a task
brief, not evidence that any remaining work has been completed.

## What independence means

Every wrestler must have independently editable artwork for every required
performing and receiving pose. This includes heads, hair, gear, body components,
private compressed tile packets, descriptors and the ROM references selecting
them. Editing one wrestler must not change another wrestler's appearance.

Common move logic, animation timing and immutable shadows can remain shared
where appropriate. Shared logic is not itself the cause of the visible gaps.
Trace the actual cause: missing pieces, wrong anchors or flips, incorrect
descriptor routing, stale VRAM tiles, mismatched paired frames or transitions.
Do not duplicate all engine code merely to eliminate sharing.

An imported wrestler must cover Raw's actions even when those poses do not exist
in the donor game. An imported move must have suitable receiving poses for every
eligible opponent. Reuse a compatible receiving motion only after validating it;
each opponent must keep their own identity and customized gear throughout it.

## First deliverable: audit and coverage matrix

Create a maintained machine-readable coverage inventory and a readable report.
Include all twelve original slots and Mr. Perfect. Use logical slot IDs as well
as display names, because the user renames and redraws wrestlers.

For each action and pose, record:

- Performer or receiver role; ordinary actions, grapples, strikes, running,
  ropes, turnbuckles, weapons, falls, recovery, pins, submissions, finishers and
  Mega Moves, including transitions into and out of each action.
- Source game, source pose/component IDs, descriptor and tile-pointer locations,
  palette owner, component anchors, facing/flip handling and runtime routing.
- Ownership and aliases: which other slots reference the same editable bytes.
- Coverage status: native port, authored replacement, adapted placeholder,
  missing, decoded only, or verified in gameplay. Keep these distinctions.
- Evidence path and outstanding defect. Do not infer completeness from a piece
  count or a set of captured screenshots alone.

Prioritize a concrete gap list for Perfect-Plex before broad roster work. Report
the required missing art and routing changes without claiming all moves mapped.

## Second deliverable: correct the Perfect-Plex pair

Compare the paired native Royal animation with Raw frame by frame. Inspect both
wrestlers together, not isolated head/body previews. Fix registration, component
seams, frame synchronization, flips and entry/exit transitions. Check every
intermediate frame for partially updated or stale tiles. Check the final bridge
and explain any remaining difference in move behavior.

Prove Undertaker first, then the other direct Royal counterparts, then Raw-only
and customized wrestlers. Do not silently render a donor wrestler on a Raw-only
slot. Scott Hall, Nash, Syxx and Sting must retain the user's edited appearance.
Mr. Perfect also needs his own artwork when receiving another Perfect-Plex.

Draw missing poses at native pixel resolution using the game's proportions,
silhouettes, outlines, shading and palette constraints. Preserve recognizable
face and gear details. Enlarged previews must use nearest-neighbor scaling.
Provide labeled drafts for review; generated concept art is not proof of an
implemented SNES sprite. Fit the renderer's actual object/tile budgets.

## Current implementation and limits

- Released v0.16.1 has a playable independent thirteenth slot and fixes referee
  and announcer palettes. Its Perfect-Plex receiving sequence is still an
  inaccurate generic vertical-suplex approximation.
- Many ordinary Mr. Perfect pieces are adapted Raw artwork, not a complete Royal
  port. Automatic bridge-to-pin behavior remains open.
- `tools/map_perfect_receivers.py` and `data/perfect-receivers.json` reconstruct
  twelve Royal receiving drawings. Undertaker's decoded source reconstruction
  matches the captured native Royal pixels; this does not validate Raw alignment.
- `tools/build_perfect_receiver_prototype.py` is an Undertaker-only private test.
- Direct counterpart mapping, Raw logical slot to Royal logical slot:
  `{1:3, 2:2, 3:9, 5:8, 6:10, 8:7, 12:1}`.
  These are Bret, Undertaker, Yokozuna, Razor, Lex, Shawn and Mr. Perfect.
- Luna, Bam Bam, Doink/Sting, Kid/Syxx, Diesel/Nash and Owen need receiving art
  beyond that direct mapping. Palette remapping alone does not preserve edited
  gear patterns.
- A seven-counterpart experimental build exists locally in
  `tools/build_perfect_receivers.py`, with browser counterparts
  `editor/perfect-receiver-core.js`, `editor/perfect-receiver-layouts.js` and
  `tools/build_perfect_receiver_manifest.py`. At handoff these are untracked,
  not integrated into the editor or included in a release. They may be absent
  from a GitHub checkout. Ask Codex for the current branch/commit before relying
  on them; do not recreate or overwrite concurrent work blindly.

## Start with these tracked files

- `evidence/perfect-plex-receivers/README.md`: Royal reference and current Raw
  prototype GIFs, with explicit limits.
- `tools/import_perfect_plex.py`: attacker, receiving sequence and native hooks.
- `tools/convert_perfect_poses.py`, `tools/build_perfect_slot.py`: slot/graphics.
- `editor/royal-import.js`: importer, existing-ROM handling and NPC repair.
- `tools/verify_perfect_native.py`: native controller replay; functional checks
  alone do not establish visual correctness.
- `tools/verify_royal_import.py`, `tools/verify_referee_repair.py`: regressions.
- `tools/run_headless.py`, `tools/build_snes9x_perfect_trace.sh`: capture tooling.
- `evidence/sting-native-heads/README.md` and the NWO/Syxx evidence directories:
  approved appearance work to preserve.

ROMs and existing private captures are not committed. Request locally supplied
Raw and Royal ROM paths if absent. Never commit ROMs, extracted ROM pixel/tile
data or savestates. Commit code, address/geometry recipes and gameplay proof
images/GIFs consistent with this repository's practice. Do not fabricate tests
when source inputs are unavailable; state the missing prerequisite.

## Acceptance checks

1. Trace actual ROM routing for performer and receiver in both facing directions.
   Confirm the expected private descriptor and tile data are used in gameplay.
2. Inspect full paired animations, including intermediate frames, near both
   sides/ropes and during entry, impact, bridge and recovery. No missing limbs,
   visible seams caused by placement, foreign heads/gear or stale sprite pieces.
3. Change a distinctive pixel in one wrestler's private receiving art. Export,
   reopen and demonstrate that only that wrestler changes. Check pointer aliases
   and changed byte ranges as well as the visible result.
4. Preserve all existing profiles, portraits, HUD names, music assignments and
   customized sprites. Keep referee and announcers visible and correctly colored.
5. Preserve damage-once behavior, match recovery and controller operation without
   emulator RAM edits. Respect ROM bank mapping, compression and renderer limits.
6. Add new poses to the editor, with editable private tiles, project round trips
   and stable save/reopen behavior. Validate both newly imported and existing mods.
7. Publish reproducible commands and labeled native gameplay GIFs in GitHub.
   Track tested, untested, approximate and missing coverage separately.

## Expected handoff back

Return the coverage inventory, diagnosed gap causes, focused changes, exact test
results, gameplay evidence and remaining work. Do not publish a release declaring
complete roster animation coverage until the matrix supports that claim.

This task does not arrange an automatic takeover when Codex usage expires.
The user must start Claude Code with this brief. Persist findings in the repo so
either tool can resume without relying on chat memory.
