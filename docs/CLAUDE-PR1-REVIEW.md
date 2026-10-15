# Codex review of draft PR #1

Reviewed the fetched PR head on 2026-10-13. This is review and coordination,
not an assertion that the animation is fixed. Do not merge the audit unchanged.

## Verified and useful

The PR contains no ROM-hook modifications. Its coverage inventory, labeled GIF
comparisons and explicit distinction between source coverage and gameplay
verification are useful. Running its suite from a separate extracted snapshot
reproduced 35 tests run: 29 passed, 6 skipped, 0 failed. The new checks validate
inventory consistency; they do not establish gameplay correctness.

The experimental seven-counterpart builder is now available on branch
`codex/perfect-receivers-wip`. It includes the Python builder, manifest generator
and browser core/layouts. These are experimental and not loaded by the released
editor. No ROMs, source pixels or states are included.

## Required audit corrections

1. **PP-2 / S5:** a constant profile offset can reproduce changing body positions
   when those positions are already encoded in each drawing's descriptor.
   Our recipes contain source-relative positions. Retain the visible overlap
   concern, but remove the prescription that per-frame profile offsets are
   necessarily required. Derive both actors' rendered pixel coordinates from
   actor origins, profile offsets, descriptors and facing before choosing a fix.
2. **PP-4:** distinguish visual appearance from native action state. Existing
   private seven-counterpart captures at frames 400 through 650 show attacker
   action 0 and Undertaker receiver action 70 (downed), health 58. Thus a generic
   claim that this implementation returns the receiver to standing is incorrect.
   The GIF's apparent standing/overlap symptom still warrants inspection of the
   exact prototype and frame; identify its ROM/build before diagnosing an exit.
3. **S3:** a union bounding rectangle does not prove every opaque pixel is
   covered by chunks. Rectangles can contain interior holes. Call this a bounds
   check, not proof that no artwork is clipped or omitted. Add exact opaque-pixel
   coverage only when private decoded source inputs are available.
4. **S1/S2:** legal stored recipe counts/order do not rule out runtime upload,
   scanline or descriptor-routing defects. Limit conclusions to the static
   records actually examined.
5. **S4:** the checker parses a hard-coded expected profile rather than the
   build output. It will keep reporting failure even after an implementation
   change. Label it a historical prototype fact; a regression test must inspect
   a constructed/exported record instead of copying its expected bytes.

## Current sharing implementation

In `tools/build_perfect_receivers.py`, `private = {}` is initialized inside the
per-slot loop, while tile-ID counter and packet cursor advance globally. The
decoded source cache may be shared, but inserted editable tile IDs/packets are
not deduplicated across slots. This establishes allocation intent by code
inspection. The editor isolation acceptance test (edit, export, reopen, compare
all other workers) is still outstanding; do not claim that test passed.

## Next Claude task and ownership

Codex retains ROM hooks, builders and browser integration. Claude should revise
its audit/checker/inventory files for the issues above, inspect the WIP branch,
and prepare a ROM-free coordinate derivation/checker for the paired animation.
Record assumptions explicitly, including pixel-level horizontal reflection and
the source common anchor. Report the predicted discrepancy before proposing
hook edits. Do not author a new set of receiving offsets from GIF appearances
alone. Keep PR #1 as a draft and retain the user's visible-gap report.

Native traces and art authoring remain with Codex until ownership is explicitly
changed. Claude cannot produce native verification without locally supplied ROMs
and a built core; repository access alone does not provide those private inputs.
