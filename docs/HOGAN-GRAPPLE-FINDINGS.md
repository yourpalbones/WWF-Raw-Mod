# Hogan: ordinary-move and source-profile findings

Development findings after the verified slot/basic/landing milestone `99065e2`.
The public milestone is a stock-based thirteen-slot test. It does **not** establish
complete animation coverage or compatibility with the user's gear mod.

## Ordinary move directory

Raw's variable-move resolver at `$80:F823` reads five-word move tables through
`$AD:D859`. The corrected thirteen-slot export contains thirteen valid pointers;
entry thirteen (the fourteenth worker) is `00 04 00 04`, which is attribute data,
not a valid pointer. The new player must have an ordinary-move route in addition
to a menu/profile entry.

The WIP `ordinary_move_hook` at `$4A:F700` routes only selector 26 with player
role `<4` to `$4A:8C60`. Other workers and the referee keep their existing route.
The current provisional table is `[234,242,174,190,226]`:

- Body slam (B, 242) and vertical suplex (X, 174) enter their native paired
  actions; receiving Luna enters 244 and 176 respectively.
- A uses a **temporary Samoan-drop route**, not a completed source A import.
- Running hip-toss/boot routes are provisional and require gameplay checks.

Do not put Raw's running-counter action 190 directly in the tie-up A field.
A scratch test did so and reached invalid action values. The tie-up placement
code expects a different action category. That experiment is not a release.

The source Sega controller tests (normal inputs) show Hogan's B throw uses
physical action 184 and visible poses 189–195; C uses action 176 and visible
poses 157–164. The source A test uses action 192, but its complete Raw adapter
is unfinished. Source and Raw action IDs are not interchangeable.

## `$FFFE` is not a profile terminator

Actual Raw vertical-suplex profiles `$C8:4C70`, `4C84`, `4C98`, etc. contain
`$FFFE` between real parts. Native `$80:ECB1`/`ED0B` continue parsing after it;
`$80:EDC8` emits a control marker into the drawing list. It consumes two bytes,
not a four-byte part record. `$FFFF` is the terminator.

The Hogan candidate mapper now continues past `$FFFE`. Claude's fetched
`ca8e647` `tools/raw_profiles.py:entries()` rejects it as an invalid part, so its
profile inventory/candidate pool excludes these real profiles. This is a
concrete parser issue to address when updating the coverage inventory. Retain
boundary metadata where needed for paired composition; do not treat the marker
as a drawable part or stop at it.

The analogous source Genesis `$8000` directive records an object-list split:
`$008890` writes a control word and records the current object count; `$008BD0`
advances that count. It is not itself a shadow drawing. Actual common source
shadow components have indices 0–15 (`$00894A`/`8954` tags these). The existing
Python `shadow` field on the directive is a historical name; it means a skipped
control token, not the shadow component. `render_pose(...,include_shadows=False)`
can now exclude the real shadow components for geometric body comparisons.

## Limits of silhouette matching

Comparing a Raw body with a source composite that still includes its shadow
creates false mismatches. Reading only the parts before `$FFFE` also creates an
incomplete body. Those cases are corrected in the WIP analysis.

Even after that, an exact body silhouette is a candidate, not a verified move.
Some isolated source Hogan composites contain gaps; whether those are occluded
regions, unused variants or another context must be established with native
paired captures. Do not fill them with another worker's head or claim that all
647 parsed composites are complete, usable Hogan animations.

## Newer receiving layout and user-mod preservation

Claude's latest PR head fetched here is `ca8e647`. Its RX3 receiving layout avoids
Syxx/Sting reservations used by older RX2 tests. Hogan's builder accepts an RX3
base and stores the added palette in its own bank (`$4A:6A00`), rather than
assuming `$70:EA60` remains free.

The test's banks 4A/54/55 are currently empty in the user's mod, but they lie
inside the Scott/Nash gear builders' maximum packet reservations. An immutable
emulator test can use that currently empty space; **editor integration must
reserve it explicitly or allocate elsewhere**. Reapplying or expanding those
gear packs must not clear Hogan's data. No release/editor-compatibility claim
should be made until that ownership and preservation check is implemented.
