# Agent coordination: Claude Code ↔ Codex

The handoff (`docs/CLAUDE-ANIMATION-HANDOFF.md`) asks the two tools to agree on
file ownership before editing the same implementation files. Neither tool can
message the other directly, so this file is the channel. Update it in the same
commit as any ownership change.

## Current claims

Per Codex's review (`docs/CLAUDE-PR1-REVIEW.md` on `codex/perfect-receivers-wip`):
Codex keeps the ROM hooks, builders, browser integration, native traces and art
authoring until ownership is explicitly changed.

| Path | Owner | Notes |
| --- | --- | --- |
| `tools/import_perfect_plex.py`, `tools/build_perfect_slot.py`, `tools/convert_perfect_poses.py` | **Codex** | Attacker stream and slot hooks. |
| `tools/build_perfect_receiver_prototype.py` | **Codex** | Older Undertaker-only prototype. |
| `tools/build_perfect_receivers.py`, `tools/build_perfect_receiver_manifest.py` | **Codex** | WIP on `codex/perfect-receivers-wip` @ `2955d5c`. |
| `editor/perfect-receiver-core.js`, `editor/perfect-receiver-layouts.js`, `editor/royal-import*.js` | **Codex** | Browser integration; WIP files not loaded by the released editor. |
| `tools/map_perfect_receivers.py`, `data/perfect-receivers.json` | **Codex** | Claude reads them only. |
| Native traces, art authoring | **Codex** | Claude has no ROMs or core. |
| `tools/build_animation_coverage.py`, `data/animation-coverage.json`, `docs/animation-coverage.md` | **Claude** | Coverage inventory. |
| `tools/check_perfect_receivers.py`, `tests/test_animation_coverage.py` | **Claude** | ROM-free record checks. |
| `tools/derive_perfect_pair_coordinates.py`, `docs/perfect-plex-pair-coordinates.md`, `evidence/perfect-plex-receivers/pair-coordinates.json` | **Claude** | Paired coordinate model (predictions). |
| `tools/review_perfect_plex_gifs.py`, `evidence/perfect-plex-receivers/frame-review/` | **Claude** | Labeled review sheets. |
| `docs/perfect-plex-gaps.md`, this file | **Claude** | Either tool may append findings. |
| `tools/check_perfect_receiver_pixels.py`, `tools/measure_perfect_pair.py`, `tools/run_controller_recipe.py` | **Claude** | Read-only measurement tools; they take user-supplied ROMs and write numbers only. |
| `docs/perfect-plex-native-trace.md`, `evidence/perfect-plex-receivers/native-wip/`, `evidence/perfect-plex-receivers/pixel-coverage.json` | **Claude** | First native measurement (observation only). |

## Review corrections applied (PR #1)

1. PP-2/S5: the per-frame-offset prescription is withdrawn. Rendered positions
   are derived in `docs/perfect-plex-pair-coordinates.md`.
2. PP-4: visual appearance is separated from native action state (70, downed).
   The older GIF's build must be identified before diagnosing it.
3. S3 is renamed a bounds check; it does not prove per-pixel coverage.
4. S1/S2 conclusions are limited to the stored records examined.
5. S4 is now an informational historical fact; the test no longer asserts it
   fails.

## Native trace run by Claude (user supplied ROMs)

The user supplied the Raw and Royal ROMs in this session. Claude ran
observation-only traces: controller inputs only, no memory writes, no change to
any hook, builder or editor file. Codex's WIP builder ran unmodified in a scratch
worktree. Results are in `docs/perfect-plex-native-trace.md`. Art authoring and
all implementation stay with Codex.

## Open requests to Codex

1. **PP-0 (blocking):** imports from the unmodified 3 MiB ROM need the
   `$F0–$FF` mirror (`0x300000–0x3FFFFF`). Without it no match starts.
2. **Review the measured renderer facts** (flip rule `+8`, profile dx negated,
   attacker on top, spacing +40) and the measured +6 px registration error.
   Choose the PP-1/PP-3 approach from them.
3. **Other facing and ropes:** not measured yet. Claude can run them with the
   same tools if asked.
4. **PP-7 stray fragment** and **PP-4** (standing at action 70): sources not
   traced.
5. **Run the editor isolation test** for the WIP builder.
6. **Assign the next implementation task.** Claude will not modify ROM hooks
   until then.

## Private prerequisites (ROMs and core)

- Supplied by the user in this session; hashes verified. A core was built locally.
  ROMs and states are never committed, and a later cloud session will not have
  them unless they are supplied again.

Without these, no native gameplay capture can be produced. Coverage
statuses that require one stay `untested`.
