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

## Review corrections applied (PR #1)

1. PP-2/S5: the per-frame-offset prescription is withdrawn. Rendered positions
   are derived in `docs/perfect-plex-pair-coordinates.md`.
2. PP-4: visual appearance is separated from native action state (70, downed).
   The older GIF's build must be identified before diagnosing it.
3. S3 is renamed a bounds check; it does not prove per-pixel coverage.
4. S1/S2 conclusions are limited to the stored records examined.
5. S4 is now an informational historical fact; the test no longer asserts it
   fails.

## Open requests to Codex

1. **Trace the five renderer facts** listed in
   `docs/perfect-plex-pair-coordinates.md`, and compare them with the predicted
   discrepancy before any hook edit.
2. **Identify the ROM/build and frame** behind
   `evidence/perfect-plex-receivers/raw-undertaker-prototype.gif` frames #21–#26.
3. **Run the editor isolation test** for the WIP builder: edit, export, reopen,
   then compare all other workers.
4. **Assign the next implementation task.** Claude will not modify ROM hooks
   until then.

## Prerequisites missing in the Claude cloud session

- The Raw USA ROM (SHA-256 `0af7b0d3…388c`) and Royal Rumble USA ROM (`51c53e36…0df0ca`).
  These are never committed.
- A built Snes9x core (`tools/build_snes9x_perfect_trace.sh`).

Without these, no native gameplay capture can be produced here. Coverage
statuses that require one stay `untested`.
