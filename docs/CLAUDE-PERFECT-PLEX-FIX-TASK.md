# Claude implementation assignment: fix the measured Perfect-Plex defects

The user explicitly requested that Claude implement the fixes, rather than
continue diagnosis only. This assignment supersedes the earlier read-only
restriction in the handoff, PR review and coordination notes for the scope below.
Codex will pause edits to these implementation files while Claude works.

## Ownership transferred to Claude

- `tools/import_perfect_plex.py`, `tools/build_perfect_slot.py` and relevant
  importer allocation/mirror handling.
- `tools/build_perfect_receivers.py`, `tools/build_perfect_receiver_manifest.py`.
- `editor/perfect-receiver-core.js`, generated receiver layouts, and
  `editor/royal-import*.js` for equivalent importer fixes.
- Receiver mapping/geometry recipes and editor script/bundle integration where
  required for these fixes. Update generators before regenerating outputs.
- Focused tests, native replay tooling, gameplay evidence and audit updates.

Use the code from `codex/perfect-receivers-wip` (starting at `2955d5c`) together
with your draft PR #1 work. Keep changes on your branch/PR; do not merge or
publish a release. This task authorizes implementation changes and native
testing, not merely another report. Make focused commits with results.

## Work order

1. Fix PP-0 in the actual importer: stock 3 MiB inputs must reach gameplay
   without `diagnostic_restore_hirom_mirror.py`. Preserve existing expanded
   user mods and occupied allocations; do not blindly overwrite a 1 MiB range.
   Validate new imports and reload/export of older imported ROMs separately.
2. Fix PP-7: preserve the stock loader's object counter and other live scratch
   state. Verify that no extra OAM objects or pink fragments remain for any
   supported receiver. Keep Python and browser machine-code generation aligned.
3. Fix canonical facing, paired registration and shadows (PP-1/2/3). Derive
   coordinates from the measured renderer rules. Keep both facing directions
   correct at either rope and mid-ring, with source-accurate paired poses.
4. Fix PP-4: no sequence wrap to lift pose and no indefinitely stale artwork
   after action changes. Demonstrate actual standing/downed/recovery artwork
   and renewed walking/attacks after the move. Preserve damage exactly once.
5. Integrate the corrected receiving path into the editor and verify private
   editing: edit one wrestler, export/reopen, prove other workers unchanged.

First finish these measured defects on the direct-counterpart path. Raw-only
receiving art and customized gear coverage remain open; do not fill those slots
with another wrestler or claim complete roster coverage. Bridge-to-pin is a
separate remaining behavior requirement: implement only once the fixes above
are stable, or report it explicitly as unfinished.

## Acceptance evidence

- Run the ten cold-boot controller scenarios against the corrected export;
  include all six available receivers, both facings and the boundary cases.
- Add assertions that fail on the old defects (counter/OAM excess, registration,
  stale exit art and stock-input stall). Do not simply re-record a defective
  baseline with `--record` and count that as a passing fix.
- Retain controller-only execution: no emulator memory writes or gameplay cheats.
- Match new Python and browser output for the regions they generate; exercise
  the actual browser import/export path, not only a diagnostic Python ROM.
- Verify NPC palettes, the original twelve slots, existing portraits/profiles,
  names/themes and unrelated customized graphics are preserved.
- Show labeled before/after native GIFs and frame checks. Separate verified
  scenarios, missing art, untested mirror matches and remaining behavior work.
- Keep ROMs, extracted source pixels, memory dumps and states private. Commit
  code, reproducible recipes, reports and gameplay screenshots/GIFs only.

Continue through implementation and verification without asking for another
ownership handoff. If a prerequisite is missing, complete independent work
and state the exact blocker. Return the PR/commit, what changed, native results,
editor results and remaining limitations for Codex review.
