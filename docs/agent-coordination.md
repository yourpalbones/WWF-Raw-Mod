# Agent coordination: Claude Code ↔ Codex

> **Ownership update (complete wrestler art task, `docs/CLAUDE-COMPLETE-WRESTLER-ART-TASK.md` @ `bd31a0b`).**
> Claude owns, for this task and until handing it back:
> - **Art generation:** receiving and ordinary pose composites, authored pixels, and the recipes that build them
>   (`tools/build_perfect_receivers.py`, `tools/build_perfect_receiver_manifest.py`, new `tools/*receiv*`,
>   `tools/*own_art*`, `data/perfect-receivers.json`, new `data/*-receiving*.json`).
> - **Private sprite routing:** `tools/import_perfect_plex.py`, `tools/build_perfect_slot.py`, the receiver hooks,
>   the new part resolver (`tools/raw_parts.py`, `editor/raw-parts.js`, `data/raw-tile-directory.json`).
> - **Pose manifests:** `editor/*-layouts.js` for receiving and pose catalogues, and `tools/canonical_perfect_geometry.py`.
> - **Editor sprite editing and animation preview:** `editor/perfect-receiver-core.js`, `editor/royal-import*.js`,
>   the new `editor/animation-preview.js`, and the sprite and preview parts of `editor/index.html`, `editor/editor.js`
>   and `editor/app.js`.
> - **Coverage:** `tools/build_animation_coverage.py`, `data/animation-coverage.json`, `docs/animation-coverage.md`.
>
> Codex should avoid concurrent edits to these. **Possible overlap:** `editor/index.html`, `editor/editor.js`,
> `editor/app.js` and `tools/bundle_editor.py` also hold non-sprite features (profiles, music, names). If Codex
> needs them, record the parts here first. Gear builders for Scott, Nash, Syxx and Sting (`tools/build_nwo_gear.py`,
> `tools/build_sting_replacement.py`, `editor/scott-sprites.js`) are read, not changed, unless noted here.

> **Active ownership update:** The user has assigned the Perfect-Plex fixes to
> Claude. [Implementation task](CLAUDE-PERFECT-PLEX-FIX-TASK.md) supersedes the
> earlier Codex ownership/read-only restrictions below for its listed scope.
> Claude owns the importer, paired hooks/builders, necessary browser integration
> and their verification until handing the task back. Codex pauses those edits.
> The earlier table and trace notes below are retained as historical context.

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
| Art authoring, implementation fixes | **Codex** | Native measurement tooling is shared; either tool may run it. |
| `tools/build_animation_coverage.py`, `data/animation-coverage.json`, `docs/animation-coverage.md` | **Claude** | Coverage inventory. |
| `tools/check_perfect_receivers.py`, `tests/test_animation_coverage.py` | **Claude** | ROM-free record checks. |
| `tools/derive_perfect_pair_coordinates.py`, `docs/perfect-plex-pair-coordinates.md`, `evidence/perfect-plex-receivers/pair-coordinates.json` | **Claude** | Paired coordinate model (predictions). |
| `tools/review_perfect_plex_gifs.py`, `evidence/perfect-plex-receivers/frame-review/` | **Claude** | Labeled review sheets. |
| `docs/perfect-plex-gaps.md`, this file | **Claude** | Either tool may append findings. |
| `tools/check_perfect_receiver_pixels.py`, `tools/measure_perfect_pair.py`, `tools/run_controller_recipe.py` | **Claude** | Read-only measurement tools; they take user-supplied ROMs and write numbers only. |
| `tools/compose_perfect_recipes.py`, `tools/verify_perfect_receivers_native.py`, `tools/sheet_perfect_captures.py`, `evidence/perfect-plex-receivers/recipes/` | **Claude** | Controller recipes and the cold-boot verifier. |
| `tools/diagnostic_restore_hirom_mirror.py` | **Claude** | Diagnostic only; builds a scratch ROM so gameplay can be measured until PP-0 is fixed. Not an importer fix. |
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

## Status after the fix task (`docs/CLAUDE-PERFECT-PLEX-FIX-TASK.md`, 396896a)

Claude implemented the assigned fixes on `claude/charming-allen-njttcx` (draft PR #1, for Codex
review). Results are in `docs/perfect-plex-fix-report.md`. Files Claude changed that Codex owned before
this task: `editor/royal-import.js`, `editor/royal-import-core.js`, `editor/perfect-receiver-core.js`,
`editor/editor.js`, `editor/index.html`, the generated layouts, `tools/import_perfect_plex.py`,
`tools/build_perfect_receivers.py` and `tools/perfect_profile_assets.py`. Please review these before
any merge.

Open for Codex (not done here):
1. Bridge-to-pin (PP-5) and receiving art for the Raw-only workers (Luna, Bam Bam, Sting, Syxx, Nash,
   Owen); these use the generic stock-part path.
2. Mirror match (Perfect receiving): slot 12 cannot be picked by P2 against P1's Perfect, so it is
   untested.
3. Perfect's shadow is drawn green in every capture inspected (also outside the Perfect-Plex, on the old and
   new builds); this looks like a palette entry of the imported worker.

## Private prerequisites (ROMs and core)

- Supplied by the user in this session; hashes verified. A core was built locally.
  ROMs and states are never committed, and a later cloud session will not have
  them unless they are supplied again.

Without these, no native gameplay capture can be produced. Coverage
statuses that require one stay `untested`.
