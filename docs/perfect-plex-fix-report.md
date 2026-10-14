# Perfect-Plex fixes: report

Task: [`docs/CLAUDE-PERFECT-PLEX-FIX-TASK.md`](CLAUDE-PERFECT-PLEX-FIX-TASK.md) (Codex, `396896a`).
Branch `claude/charming-allen-njttcx`, draft PR #1, for Codex review. Not merged and not released.

How the evidence was gathered:
- Every native result comes from controller input only, starting from a cold boot. No emulator
  memory is written.
- The "fixed export" is the file that the real browser editor downloads after it adds Mr. Perfect
  to the unmodified 3 MiB Raw ROM (`tools/editor_driver.py import`). It needs no mirror restore and
  no other post-processing.
- The "before" build is the one measured earlier: the Codex WIP build `4ca2856…`, which includes
  the diagnostic mirror restore.
- ROMs, states, memory dumps and extracted pixels stay local.

## Causes (confirmed) and fixes

### PP-0

**Cause.** Imports from the stock ROM stalled on the announcer screen.
- Raw's announcer reads four tables, each holding one 16-bit entry per slot. Two of them hold
  address words and two hold banks (bank in the low byte).
- The importer copied the bank tables (`0x2EE927`, `0x2EE957`) as 12 single bytes, and wrote
  Mr. Perfect's bank at +12.
- So slots 6–12 read bank `$FF` from erased space.
- The earlier "missing `$F0–$FF` mirror" explanation was wrong. Restoring the mirror only made
  those bad reads land on a copy of the right data.

**Fix.**
- `editor/royal-import.js` rebuilds all four tables (13 entries, word stride) from the profile
  records, so user monitor edits are kept.
- Older imports are repaired by "Save playable ROM", and the editor says so when such a ROM is
  opened.
- `tools/perfect_profile_assets.py` gets the same fix.

### PP-1/2/3: facing, registration, shadow

**Cause.**
- Raw's art faces right when unflipped. The imported Perfect-Plex attacker frames faced left.
- So the whole scene was mirrored, and the receiver was registered |spacing| − 34 px toward the
  attacker.

**Fix.**
- The attacker frames are now used as captured, and the receiver drawings are mirrored
  (`tools/canonical_perfect_geometry.py`).
- Offsets come from the measured flip rule: flipped x = origin − dx − size + 8.
- The init hook fixes the pair spacing at 40 px on the receiver's existing side.
- The receiver body offset is 45, and the shadow offset is computed per pose.
- Builds carry the markers `ROYAL-RX2` and `PLEX-CANON1`.

### PP-4: exit art

**Cause.** Both sequence hooks tested `$06B4,X`, the current action, instead of the action being
dispatched. So the next action's dispatch was sent back to step 0 of the Perfect-Plex stream, and
both actors froze in a Perfect-Plex pose after the move.

**Fix.**
- The hooks test the dispatched action (`lda 3,s` at `$80:F073`).
- On the receiver-only exit path, the receiver hook restores the stock sequence bank (`$C4`) from
  its own bank (`$71`).
- Non-special actors keep their exact original code paths, so the recipes stay frame-synchronous.

### PP-7: extra objects and pink fragments

**Cause.** The WIP receiver hook used `$90` as scratch. That is the stock part loader's running
object total (`$80:EC97`/`$80:ECE4`), so the loader emitted extra stale objects.

**Fix.** The hooks compute slot×3 on the stack and keep the stream base in `$7C`. `$90` and `$92`
are untouched. The Python builder and the browser core generate the same bytes.

## Verification

Native scenario results, the before/after GIFs and the remaining-work list follow in the next
revision of this report, once the full recipe run on the fixed export has finished.
