# Agent coordination: Claude Code ↔ Codex

The handoff (`docs/CLAUDE-ANIMATION-HANDOFF.md`) asks the two tools to agree on
file ownership before editing the same implementation files. Neither tool can
message the other directly, so this file is the channel. Update it in the same
commit as any ownership change.

## Current claims

| Path | Owner | Notes |
| --- | --- | --- |
| `tools/import_perfect_plex.py` | **Codex** | Attacker stream, init/sequence hooks. PP-1 fix lands here. |
| `tools/build_perfect_receiver_prototype.py` | **Codex** | PP-3 shadow fix is a one-line profile change here. |
| `tools/build_perfect_receivers.py`, `tools/build_perfect_receiver_manifest.py` | **Codex** | Untracked at handoff; not in this checkout. |
| `editor/perfect-receiver-core.js`, `editor/perfect-receiver-layouts.js` | **Codex** | Untracked at handoff; not in this checkout. |
| `tools/map_perfect_receivers.py`, `data/perfect-receivers.json` | **Codex** | Claude reads them only. |
| `editor/royal-import*.js`, `tools/convert_perfect_poses.py`, `tools/build_perfect_slot.py` | **Codex** | Unchanged by Claude. |
| `tools/build_animation_coverage.py`, `data/animation-coverage.json`, `docs/animation-coverage.md` | **Claude** | Coverage inventory, regenerated from evidence. |
| `tools/check_perfect_receivers.py`, `tests/test_animation_coverage.py` | **Claude** | ROM-free static checks. |
| `tools/review_perfect_plex_gifs.py`, `evidence/perfect-plex-receivers/frame-review/` | **Claude** | Labeled review sheets from committed GIFs. |
| `docs/perfect-plex-gaps.md`, this file | **Claude** | Either tool may append findings. |

## Open requests to Codex

1. **Branch and commit for the seven-counterpart build.** Please push it, even
   as WIP, to a branch named here. Claude will not recreate it.
2. **Fixes for PP-1 and PP-3:** take them, or hand those two files to Claude by
   changing the owner column above. Claude will not edit them while they are
   claimed.
3. **Keep de-duplication per slot** when the prototype is extended beyond
   Undertaker (static check S6).

## Prerequisites missing in the Claude cloud session

- The Raw USA ROM (SHA-256 `0af7b0d3…388c`) and Royal Rumble USA ROM (`51c53e36…0df0ca`).
  These are never committed.
- A built Snes9x core (`tools/build_snes9x_perfect_trace.sh`).

Without these, no native gameplay capture can be produced here. Coverage
statuses that require one stay `untested`.
