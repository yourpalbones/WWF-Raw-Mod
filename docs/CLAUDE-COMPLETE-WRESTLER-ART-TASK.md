# Claude task: complete editable wrestler artwork and animation coverage

## User's goal

Every current wrestler must have all artwork needed to perform and receive
every supported action in WWF Raw, with all poses editable and the full
animations viewable in WrestleEdit. Include the original twelve slots, their
customized identities (Scott Hall, Kevin Nash, Syxx, Sting and any other user
edits), and added characters, currently Mr. Perfect. This requirement also
applies to each future imported character; it is not an instruction to import
the entire proposed 37-person roster during this task.

Missing art must match the specific wrestler's proportions, face, hair, gear,
palette and the original game's native pixel style. The user's target is that
new art looks indistinguishable in style from the existing game graphics.
This requires visual review, not a claim based only on passing code tests.

## Ownership and working base

The user assigns this artwork/coverage work to Claude. Continue on your branch
with the corrected Perfect-Plex implementation and PR #1 work. Read current
coordination notes and update them with ownership of art generation, private
sprite routing, pose manifests, editor sprite editing and animation preview
files before implementation. Those parts are yours for this task; Codex will
avoid concurrent edits to them. Codex's separate task is not yet specified.
Flag any overlapping files before both tools work on them.

Retain the tested Perfect-Plex fixes. Use the independent Bret and Undertaker
checks on `codex/perfect-receivers-wip` as supplementary evidence, not a claim
that all receiving art or customized gear is complete. Do not merge or publish
a release; return reviewable commits/PR and proof.

## Required coverage

Build and maintain a per-slot action/pose matrix. Cover both performer and
receiver roles, component variants, transitions and facing directions:

- Standing, walking, running, turning, ropes and ring entry/exit.
- Strikes, grapples and throws, running counters and all taking-move reactions.
- Ground attacks, falls, recovery, pins and submissions.
- Turnbuckle actions, weapons and other supported contextual actions.
- Each wrestler's assigned finisher and Mega Move, and every eligible opponent
  receiving them. Include the Perfect-Plex for all thirteen current slots,
  including Mr. Perfect receiving it in a mirror match.

Discover the game's actual actions and variants; this list is not exhaustive
proof. A count of parsed pieces or a collection of captures does not establish
coverage. Keep missing, adapted, authored, decoded-only and native-verified
statuses distinct. Include source/descriptor IDs, tile ownership, runtime
routing, editor pose/animation IDs and evidence for each entry.

## Art and routing requirements

1. Supply missing ordinary Mr. Perfect poses and missing receiving poses for
   Raw moves absent from Royal Rumble. Validate compatible source poses before
   reuse; author the rest at native resolution.
2. Complete Perfect-Plex receiving art for Luna, Bam Bam, Sting, Syxx, Nash and
   Owen, plus the existing direct counterparts and Perfect. Never temporarily
   render another wrestler's head, body or gear as a completed receiving pose.
3. Preserve the current mod's gear across every action. Stock Royal Razor art
   is not finished Scott Hall receiving art. Likewise, Sting must not become
   Bret or Undertaker during a move. Use the supplied latest user ROM and
   approved evidence as appearance references. If that ROM is unavailable,
   state the missing prerequisite instead of treating stock art as approved.
4. Every wrestler's editable art must be independent: private tiles, compressed
   packets, descriptors and correct ROM routing where required. Sharing common
   timing/logic or immutable shadows is allowed. Do not duplicate the engine
   solely to eliminate all sharing.
5. Respect palette, compression, bank mapping, OAM/VRAM and object/tile limits.
   Inspect intermediate upload frames as well as finished poses. Keep NPC art,
   profiles, portraits, names, themes and unrelated user edits intact.

## Editor requirements

- Expose every required drawing, including newly authored and receiving poses,
  in the relevant wrestler's editable sprite collection.
- Provide clear action names and performer/receiver labels. Group pieces into
  actual composite poses; do not require the user to reconstruct a body from
  unidentified fragments.
- Let users view full action sequences, including entry and exit, play/pause,
  frame step and both facings. Show paired performer/receiver previews for
  moves such as Perfect-Plex so alignment can be inspected.
- Use real game timing and composition where mapped. Label approximations or
  unverified timing; do not present a slideshow of unrelated poses as an
  accurate animation. Emulator gameplay remains the runtime reference.
- Verify paint/import, palette constraints, packet growth, export, project
  round trips and ROM reopen for the new art. Older edited mods need a clear
  non-destructive upgrade path that preserves user changes and reports conflicts.

## Work in reviewable batches

First finish one complete receiving family, including all current identities,
private ownership, editor editing and paired previews: Perfect-Plex. Then expand
the inventory and complete other action families. Keep updating the same
coverage matrix and missing-art list. Do not pause after an audit if inputs are
available; continue through art, routing, editing and native verification.

For authored art, publish enlarged nearest-neighbor comparisons alongside
native-size and gameplay views. Keep silhouettes, shading and head/gear placement
consistent through adjacent frames. Request targeted visual feedback while
continuing independent work. Do not declare the style indistinguishable without
review of the actual implemented pixels.

## Acceptance and handback

For each completed action family:

1. Trace the actual performer/receiver descriptor and tile routing in exported
   gameplay; test both facings and applicable positional/context variants.
2. Show native full-sequence captures with no foreign identities, missing limbs,
   misplaced pieces, stale exit poses or inconsistent gear.
3. Edit a distinctive pixel for one worker in the editor, export/reopen and
   demonstrate that all other workers are unchanged. Check aliases and changed
   bytes as well as appearances.
4. Demonstrate the corresponding composite poses and animation controls in the
   editor, with project/save/reopen tests and preservation of existing edits.
5. Record exact passed, failed, skipped and untested checks. Do not re-record a
   faulty baseline as expected output to call it a fix.

Keep ROMs, extracted ROM art/tile data, memory dumps and states private. Follow
the repository's source/geometry recipe approach for donor data; commit authored
code, permitted original assets, recipes, coverage reports and gameplay proof.

Return the updated matrix, implementation commits, editor demonstration and
native evidence, with remaining gaps clearly identified. Completion means the
matrix is supported by evidence, not simply that every row has a placeholder.

This document assigns the task; Claude must be started separately by the user.
It does not schedule an automatic takeover when another tool runs out of usage.
