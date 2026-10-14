# Complete wrestler artwork and animation coverage

Task: [`docs/CLAUDE-COMPLETE-WRESTLER-ART-TASK.md`](CLAUDE-COMPLETE-WRESTLER-ART-TASK.md) (`bd31a0b`).
Branch `claude/charming-allen-njttcx`, draft PR #1. This page is the working checklist. Every status
names its evidence. **Nothing here is complete until native gameplay and a visual review confirm it.**

## Prerequisites and references

- **Latest user ROM: not supplied.** Only the stock Raw and Royal Rumble ROMs are available in this
  session. The current identities are rebuilt with the editor's own reference-gear buttons
  (`tools/editor_driver.py apply-gear`, slots 5, 9, 10 and 7):
  - Scott Hall `SCOTT-HALL-GEAR3`
  - Syxx `SYXX-NATIVE-GEAR3`
  - Kevin Nash `NASH-NATIVE-GEAR2`
  - Sting `STING-NATIVE-GEAR4`

  Mr. Perfect is then imported. **Other user edits cannot be checked** until that ROM is supplied. This
  includes Bret's black-gear prototype, which was never part of the editor.
- Receiving art never uses stock Royal art for a changed identity. For example, Royal Razor is
  skipped when Scott Hall's gear is present (`stock_identity_only`).

## Status vocabulary

| Status | Meaning |
|---|---|
| `missing` | No drawing exists for this role. |
| `generic` | Drawn from stock receiving parts in the slot's own art, but the poses are not Perfect-Plex poses. |
| `royal` | Royal Rumble's drawing of the same person, privately stored for this slot. |
| `own-art` | Rebuilt from this slot's own Raw parts (identity, gear and user edits carry over); donor colour roles fill the gaps. |
| `authored` | New pixels drawn for this slot. |
| `native-verified` | Measured in cold-boot gameplay with the defect assertions. |
| `reviewed` | Visually reviewed and accepted by the user. |

## Foundations built in this batch

- **Part resolver** (`tools/raw_parts.py`, `editor/raw-parts.js`). It resolves any slot's frame part
  as the game does:
  - frame part to descriptor, then tile IDs, then packets;
  - stock directory (`data/raw-tile-directory.json`, addresses only);
  - gear tables, chosen by descriptor bank (`$42/43` Scott, `$4C/4D` Nash, `$56/57` Syxx, `$60/61`
    Sting);
  - slot-12 tables, including the Perfect-Plex frames 1000–1011.

  Checks:
  - 4,128 stock parts match the WRAM-based catalog exactly.
  - Python and JS agree on 3,211 parts across all 13 slots.
  - Profile part IDs are directory byte offsets (frame index × 3).
- **Receiving storage RX3.**
  - RX1/RX2 stored drawings inside the Syxx and Sting gear reservations.
  - RX3 uses only space that the Perfect import owns or that nobody reserves: banks `$70`/`$71`,
    `$7D:A000+`, and `7E8000`/`7F8000` (reached as `$3E`/`$3F:8000`).
  - These regions are free in fresh, v0.16, pre-`569240b` and gear-modded imports.
  - Uninstall restores the base byte for byte and never clears an active gear range.
  - The browser core is the only installer; `tools/receivers_cli.js` runs the same code in Node.
    Browser export equals the Node build byte for byte.
- **Paired preview** (`editor/animation-preview.js`).
  - Shows Perfect and any receiver as the game composes them, in both facings, with play/pause and
    frame step.
  - Timing comes from native captures (7 frames per step; the final pose is held 64).
  - Against native screenshots it matches 99.6–100% of pixels on every step in three unoccluded
    scenarios (`tools/check_preview_native.py`). The referee in front of the pair lowers one
    scenario to 83–99%.
  - Entry (tie-up) and exit (downed) drawings come from other actions and are not yet in the preview.

## Perfect-Plex receivers: following Royal's move (revised after review)

**Review feedback.** "The new Perfect-Plex receiver animations are close but look misaligned, causing the
finished move to look nothing like the Royal Rumble product."
- Cause: the own‑art receivers used Raw's own vertical‑suplex drawings, re‑timed. Royal lifts the receiver
  **over** Perfect: across his shoulders, then inverted above him, then onto his back in the bridge.
- The suplex drawings stood beside him, went straight up next to him and dropped beside him. Royal's receiver
  bounding boxes (`data/perfect-victim-layouts.json`) differ from the suplex drawings by up to 55 px at the lift.

### Second review: Royal's drawings in each wrestler's own pixels (source `reskin`)

**Review feedback** on the own-pose version below: "Does the Royal geometry Bret and the new look the same to
you?" They did not. At step 11, the frame the move ends on, Royal's receiver lies across Perfect with one leg
straight up; the closest Raw pose lay curled with its legs low. Raw has no drawing of that landing, or of most of
the lift, for anyone. "We have perfect examples of taking moves and just need to rebuild it using the animation
style and graphics."

**Now** (`tools/plan_receiver_reskin.py`, `data/receiver-reskin-plan.json`):
- **Shape and placement are Royal's.** Every step keeps the Royal donor's receiving drawing pixel for pixel in
  shape and position, with Royal's anchors. The donors are the same as before (closest build).
- **Every pixel is the wrestler's own.**
  - Examples: Raw draws every wrestler's piece *i* in the same pose, Raw Bret's piece *i* was matched to Royal
    Bret's frame *k* (`data/perfect-pose-matches.json`), and Royal draws every worker's frame *k* in the same pose.
    So the donor's frame *k* and the wrestler's piece *i* show one pose twice: as the donor and as the wrestler.
    Pairs are aligned by silhouette (overlap ≥ 0.5) and used in both facings.
  - For each pixel of Royal's drawing, its 11×11 neighbourhood (centre-weighted) is compared with the donor's
    pixels in all pairs, and the pixel copies the wrestler's pixel at the best match. Neighbouring pixels keep
    copying from the same pair while that stays nearly as good, so legs, arms and heads come across as whole
    stretches of the wrestler's drawing. That is how Owen's legs come out as his trunks, knee pads and boots,
    where Royal Bret wears long tights.
  - A mode filter within each of Royal's colour regions removes isolated pixels; a changed pixel copies the
    neighbour that has the colour.
- **Install** (`editor/receiving-art.js` `reskin`): the plan names, per pixel, a piece and offset; the pixels are
  read from the user's ROM, so gear identities and edits come through. Gear identities have their own plans,
  made from their gear art. Pixels behind Mr. Perfect are removed, as before.
- **Checks:**
  - The browser/Node importer draws exactly the planner's reference rendering: 12/12 steps for all ten plans
    (six stock wrestlers, four gear identities).
  - Every drawing fits the actor's object budget (at most 15 objects).
  - Builds through the editor (Add Mr. Perfect): stock `55e331ba…`, gear reference mod `a2dd91b0…`.
  - Native gameplay on these builds: all 19 controller-only scenarios re-recorded with the bot (art changes
    move the game's timing) and pass every defect assertion; a clean re-run reproduces every recorded value.
    Own-art receivers equal the editor preview on every step (see the matrix below). In-game, the receiver now
    finishes across Mr. Perfect in the bridge with a leg up, as in Royal
    ([Owen](../evidence/complete-wrestler-art/owen-attacker-left.gif),
    [Doink](../evidence/complete-wrestler-art/doink-attacker-left.gif)).
- **Review GIFs** (editor preview at the move's timing; Royal, previous own poses, new):
  [Luna](../evidence/complete-wrestler-art/receiver-review/luna.gif) ·
  [Bam Bam](../evidence/complete-wrestler-art/receiver-review/bam-bam.gif) ·
  [Doink](../evidence/complete-wrestler-art/receiver-review/doink.gif) ·
  [Kid](../evidence/complete-wrestler-art/receiver-review/kid.gif) ·
  [Diesel](../evidence/complete-wrestler-art/receiver-review/diesel.gif) ·
  [Owen](../evidence/complete-wrestler-art/receiver-review/owen.gif) ·
  [Scott Hall](../evidence/complete-wrestler-art/receiver-review/scott-hall-gear.gif) ·
  [Sting](../evidence/complete-wrestler-art/receiver-review/sting-gear.gif) ·
  [Syxx](../evidence/complete-wrestler-art/receiver-review/syxx-gear.gif) ·
  [Kevin Nash](../evidence/complete-wrestler-art/receiver-review/kevin-nash-gear.gif)
- **Limits.** This is an automatic rebuild, not hand-drawn art. Where the wrestler's build or costume differs
  most from the donor's, regions can come out blotchy, for example magenta trunk colour on Owen's raised legs.
  Each drawing stays editable in the sprite editor ("Receiving Perfect-Plex · 1–12").

### First review: the wrestler's own Raw poses (source `own_profiles`, superseded)

**Method** (`tools/plan_receiver_profiles.py`, `data/receiver-profile-plan.json`):
- **Target.** For each step, the target is Royal's composite: the Royal donor's receiving drawing (closest
  build) with Mr. Perfect's own drawing in front, both from the native Royal capture.
  - Royal draws only what shows, so receiver pixels behind Perfect are free.
  - Donors: Shawn for Luna, Kid and Syxx; Crush for Bam Bam; Flair for Doink; Undertaker for Diesel and Nash;
    Bret for Owen; Razor for Scott Hall; Lex for Sting.
- **Candidates.** Every Raw pose profile (1,036, `tools/raw_profiles.py`), drawn with the receiver's **own**
  parts, in four facings (180° rotations included), placed at the best offset.
  - Only own‑range parts: the shared range would draw someone else's art.
  - Only drawings the importer can store.
- **Score.** Overlap of what stays visible, by colour class: skin and hair against gear. An upside‑down body
  cannot stand in for an upright one.
  - Doink's skin indices hold clown greys, so he is classed by Raw's palette roles.
- **Gear.** Gear identities (Scott, Sting, Syxx, Nash) have their own plans from their gear art.
- **Install** (`editor/receiving-art.js` `ownProfiles`):
  - Each step's pose is drawn from the user's ROM, so identity, gear and edits carry over.
  - Pixels behind Perfect are removed, as in Royal's drawings, so sprite priority cannot change what shows.
  - Royal's anchors are used (`body_dx`, `shadow_dx`).
- **Review GIFs of that round** (editor preview, which equals native; Royal geometry, re-timed suplex, own poses):
  [Luna](../evidence/complete-wrestler-art/receiver-review/previous-builds/luna.gif) ·
  [Bam Bam](../evidence/complete-wrestler-art/receiver-review/previous-builds/bam-bam.gif) ·
  [Doink](../evidence/complete-wrestler-art/receiver-review/previous-builds/doink.gif) ·
  [Kid](../evidence/complete-wrestler-art/receiver-review/previous-builds/kid.gif) ·
  [Diesel](../evidence/complete-wrestler-art/receiver-review/previous-builds/diesel.gif) ·
  [Owen](../evidence/complete-wrestler-art/receiver-review/previous-builds/owen.gif) ·
  [Scott Hall](../evidence/complete-wrestler-art/receiver-review/previous-builds/scott-hall-gear.gif) ·
  [Sting](../evidence/complete-wrestler-art/receiver-review/previous-builds/sting-gear.gif) ·
  [Syxx](../evidence/complete-wrestler-art/receiver-review/previous-builds/syxx-gear.gif) ·
  [Kevin Nash](../evidence/complete-wrestler-art/receiver-review/previous-builds/kevin-nash-gear.gif)
- **Limits.** These are Raw drawings of the receiver, not Royal's frames.
  - Step 2: the raised arm is lower than Royal's.
  - Step 11: Royal's legs point straight up; Raw's closest drawings have them bent.
  - Exact matches would need authored drawings.

## Perfect-Plex receiving matrix (all 13 current slots)

Builds (this round; Mr. Perfect with his Royal pose pieces and Royal heads, own-art receivers rebuilt from Royal),
both made through the editor's **Add Mr. Perfect** (`tools/editor_driver.py import`):
- **Stock import v4:** `55e331ba…`, stock Raw.
- **Gear reference mod v4:** `a2dd91b0…`, with Scott, Syxx, Nash and Sting applied, then Mr. Perfect.

Every scenario below is a controller-only cold-boot replay (`tools/verify_perfect_receivers_native.py`).
Each passes every defect assertion:
- spacing ±40;
- no foreign objects;
- damage exactly once (one loss of health);
- no Perfect-Plex pose after the move.

Royal-drawn receivers also register within 1 px. Own-art receivers must equal the editor preview on every
step, and they do: 100% of actor pixels, rebuilt from OAM. A clean re-run reproduces every recorded value.
Data: [`verification-stock-v4.json`](../evidence/complete-wrestler-art/verification-stock-v4.json) and
[`verification-gear-mod-v4.json`](../evidence/complete-wrestler-art/verification-gear-mod-v4.json).
The earlier builds' recipes, reports and GIFs are kept under `previous-builds/`.

| Slot | Identity | Receiving drawings | Native scenarios (all pass) | Status |
|---|---|---|---|---|
| 0 | Luna Vachon | Royal Shawn's, in Luna's own pixels | `luna-attacker-left`, `luna-attacker-right` | own-art, native-verified ([GIF](../evidence/complete-wrestler-art/luna-attacker-left.gif)) |
| 1 | Bret Hart (stock; user gear unknown) | Royal Bret | `bret-attacker-left` | royal, native-verified |
| 2 | Undertaker | Royal Undertaker | `undertaker-attacker-left`, `undertaker-attacker-left-2` | royal, native-verified |
| 3 | Yokozuna | Royal Yokozuna | `yokozuna-attacker-right` | royal, native-verified |
| 4 | Bam Bam Bigelow | Royal Crush's, in Bam Bam's own pixels | `bambam-attacker-left` | own-art, native-verified ([GIF](../evidence/complete-wrestler-art/bambam-attacker-left.gif)) |
| 5 | Razor Ramon (stock) / Scott Hall (gear) | Royal Razor on stock; Royal Razor's in Scott's own pixels with his gear | `razor-attacker-right` (stock), `scott-gear-attacker-left` (gear) | royal + own-art, native-verified ([GIF](../evidence/complete-wrestler-art/scott-gear-attacker-left.gif)) |
| 6 | Lex Luger | Royal Lex | `lex-attacker-right` | royal, native-verified |
| 7 | Doink (stock) / Sting (gear) | Royal Flair's in Doink's own pixels; Royal Lex's in Sting's | `doink-attacker-left` (stock), `sting-gear-attacker-left`, `sting-gear-attacker-left-2` (gear) | own-art, native-verified ([GIF](../evidence/complete-wrestler-art/doink-attacker-left.gif), [GIF](../evidence/complete-wrestler-art/sting-gear-attacker-left.gif)) |
| 8 | Shawn Michaels | Royal Shawn | `shawn-attacker-left` | royal, native-verified |
| 9 | 1-2-3 Kid (stock) / Syxx (gear) | Royal Shawn's, in their own pixels | `kid-attacker-right` (stock), `syxx-gear-attacker-left` (gear) | own-art, native-verified ([GIF](../evidence/complete-wrestler-art/kid-attacker-right.gif), [GIF](../evidence/complete-wrestler-art/syxx-gear-attacker-left.gif)) |
| 10 | Diesel (stock) / Kevin Nash (gear) | Royal Undertaker's, in their own pixels | `diesel-attacker-left` (stock), `nash-gear-attacker-right` (gear) | own-art, native-verified ([GIF](../evidence/complete-wrestler-art/diesel-attacker-left.gif), [GIF](../evidence/complete-wrestler-art/nash-gear-attacker-right.gif)) |
| 11 | Owen Hart | Royal Bret's, in Owen's own pixels | `owen-attacker-left` | own-art, native-verified ([GIF](../evidence/complete-wrestler-art/owen-attacker-left.gif)) |
| 12 | Mr. Perfect (mirror match) | Royal Perfect (installed, previewable) | none: **unreachable in one-on-one** | royal, **not natively tested** |

Perfect ends on the right in six scenarios (Kid, Lex, Luna from the right, Razor, Yokozuna, Nash) and on the left
in the other thirteen. The bot plays wherever the match takes it.

Notes on the matrix:
- **Replay fix.** Every recipe's last R press starts on the frame where the verifier saves state and begins
  capturing (150 frames before the move). Replaying from that state dropped presses still held, so that R lasted
  one frame instead of twenty. Most moves still started; Luna's from the left did not.
  `tools/run_controller_recipe.py` now keeps a held press for the rest of its duration, and all 19 scenarios were
  re-verified with it.
- **Damage check.** PP-4 is documented as "the receiver loses health exactly once", but the code counted every
  change of health. With full-length presses, Owen's and Kid's captures show the move's single hit and then, some
  90 frames later while they lie down, a +16 rise: the game regenerating a downed wrestler's health. The check now
  counts losses of health, as documented. Two losses (the move applied twice, the defect PP-4 guards against)
  still fail. Owen was also re-recorded, starting from the right, before the cause was clear; that recording
  is the one kept.

Notes from the previous round (v2 builds):
- **Re-timing.** Raw's own receiving-suplex sequence lifts at its third drawing; the Perfect-Plex lifts
  at step 10. Played in order, the receiver lay at Perfect's feet during steps 5–9, which was caught in
  visual review. The held drawing now carries steps 2–9, the lift drawings steps 10–11 and the landed
  drawing the bridge (`OWN_NATIVE_STEPS`). This is still Raw's lift-and-fall art, not Royal's exact
  frames, and it needs your visual review.
- **Mirror match.**
  - Two-player selection skips the wrestler P1 chose.
  - One-player "player chooses opponents" does not accept the same wrestler (A has no effect).
  - A bot attempt never reached a match.
  - Other modes (tag team, Survivor Series, Royal Rumble, Bedlam, Raw Endurance) are untested.
- **Recipes.** `tools/recipe_bot.py` played all 19 recipes. It reads memory to choose controller presses
  and writes nothing; the result is a fixed input list. Two bot changes this batch:
  - P1 mashes to get up when it stays down (Luna downed Perfect and the bot waited forever).
  - `--mash 3` for Scott, Lex, Luna (from the right), Owen and Razor. With 8 strikes per round the
    receiver had zero health before the Perfect-Plex, so PP-4's damage check could not observe the move.
    The assertion is unchanged. Those recordings failed and were replaced, as each recipe's note says.
- **Private editing on RX3.**
  - A mouse stroke on Sting's receiving pose (gear mod) changed only Sting's tiles, including 40
    relocated packet bytes. The other 12 receivers decode identically.
  - Reopening and saving gives an identical file.
- **Editor.** Every slot lists its 12 "Receiving Perfect-Plex · n" composite poses. The paired preview
  plays any receiver in both facings ([screenshot](../evidence/complete-wrestler-art/editor-paired-preview-sting.png)).

## Mr. Perfect's ordinary poses (batch 2, revised after review)

Mr. Perfect's slot reuses Raw Bret's 1,720 frame pieces. In v0.16, 289 of them used Royal Perfect art and
1,431 were Raw Bret drawings recoloured into Perfect's palette, with Bret's dark hair, face and build.

**Review feedback.** "We have the Mr. Perfect Royal Rumble images; why are the redone animations and sprites
looking nothing like him?" The first pass only replaced pieces with an exact Royal silhouette. Gameplay traces
showed why that was not enough: Raw **redrew** many of Bret's poses, the idle stance among them, and those had
no silhouette match.
- In a traced match (`luna-attacker-left`), Perfect spent 52% of his screen time in one Bret‑drawn standing pose
  (profile `$C8:4596`).
- Only 20% of his screen time showed nothing but Royal art (12% in the Owen match).

| | v0.16 | first pass | now |
|---|---|---|---|
| Royal Perfect art: exact silhouette match | 289 | 289 | 289 |
| Royal Perfect art: pose match | — | 329 | 329 |
| Royal Perfect art: by frame order (semantic pass, reviewed) | — | — | **136** |
| Adapted Raw Bret art | 1,431 | 1,102 | **966** |
| … of which with Royal Perfect's own head (second review) | — | — | **172** |
| … of which with Perfect's hair colour only | — | 377 | 119 |
| Perfect's screen time showing only Royal art, Luna match | 20% | — | **98%** |
| Perfect's screen time showing only Royal art, Owen match | 12% | — | **97%** |

**Semantic pass** (`tools/match_perfect_poses.py --semantic`, decisions in `data/perfect-pose-review.json`):
- Raw's piece tables follow Royal's frame order. Matched pairs run in step: Raw's upper pieces with Royal's
  upper‑body frames, its lower pieces with Royal's lower‑body frames, with Raw insertions in between.
- A remaining piece takes one of two candidates:
  - the Royal Perfect frame of its nearest matched neighbour, placed with that neighbour's measured transform
    (Raw draws a wrestler's pieces about one body origin);
  - an unused Royal frame between the neighbours, placed at its best overlap.
- Filters:
  - Kind: a torso frame for a torso piece, legs for legs.
  - Area: within 0.6–1.6× of the original.
  - Head position: for torsos, the hair centroid within 0.35 of the bounding box. This stops rolled or
    inverted drawings from getting an upright torso.
- Review: every candidate was checked as a piece and in a composite that uses it.
  - Threshold 0.58: below it, about a third were wrong.
  - 17 rejections: torsos detached from legs, and Raw's own strike drawings, where Royal's hands‑up frame
    would erase the punch.
- The traced standing, walking, back‑view, hunched, knocked‑down, lying and getting‑up poses all show Royal
  Rumble's Perfect: his face, swept‑back hair, singlet, kneepad bands and boots.
- Still Bret‑drawn (blond hair), awaiting authored art: Raw‑only strikes (`p446`–`p476`), poses below the
  threshold (for example `p328`, bent forward) and the shared common range.
- Upgrades:
  - **Update Perfect-Plex** now accepts v0.16 pieces and pieces already recoloured by an earlier branch
    upgrade, and leaves pieces that already hold the new art (marker `POSES-ROYAL4`; `POSES-ROYAL5` after the head rebuild below).
  - v0.16, earlier‑branch and already‑current ROMs all converge on the fresh build (1,732/1,732 pieces).
  - An edited tile is kept.

### Second review: Royal Perfect's head instead of tinted hair

**Review feedback.** "Sloppily throwing yellow dots on Bret isn't exactly making the Perfect graphic … we
need to use these as a baseline to rebuild the graphics." The hair recolour kept Bret's hair shape and its black
dither, so it read as Bret with yellow dots.

Royal Rumble draws Bret and Perfect on the same frame indices, in the same pose and at the same coordinates. It
is a book of paired examples: Bret's head in a pose, and Perfect's head in that pose. `tools/rebuild_perfect_heads.py`
uses it for every adapted upper-body piece with Bret's hair:
1. Head window: Bret's hair (the hair rule finds it) plus 4 pixels.
2. Source: the Royal Bret frame, in either facing, whose pixels in that window agree best with the piece (Royal
   Bret's colours mapped as the importer adapts Raw Bret's), within 6 pixels of the hair centres' alignment.
   Generic Perfect frames (Bret's own tiles, recoloured, with brown hair) and frames without Perfect's blond hair
   are never sources.
3. Inside the window, where the piece agrees with Royal Bret it takes Royal Perfect's pixel there (or none);
   Bret's hair takes Perfect's pixel (or none); where Perfect's fuller hair reaches past Bret's and the piece is
   empty, Perfect's pixel is added. Everything else, including an arm across the face, stays as Raw draws it.

- `data/perfect-head-sources.json` holds the Royal frame, facing, offset, window and score per piece (no pixels).
  The importer applies the same rule to your ROMs (`editor/royal-import-core.js` `headRebuild`).
- Review (`data/perfect-head-review.json`): every piece was compared with its hair-recoloured version.
  - 17 rejected: 11 are other people from the common table (a masked wrestler with stars, a man in a white
    shirt) with no Bret hair; 6 came out with darker, less blond hair than the recolour.
  - **172 pieces** now show Royal Perfect's own hair and face.
  - 119 keep the hair recolour: the 17 rejections, pieces with no usable source and lower-body pieces where the
    hair rule only touched dark dither.
- Checks:
  - The browser, Node and Python give the same 172 pieces; the built ROM holds exactly those pixels.
  - **Update Perfect-Plex** (marker `POSES-ROYAL5`) rebuilds these pieces from v0.16, from the hair recolour and
    from the previous branch build. All converge on a fresh import (1,732/1,732 pieces). Running it twice
    changes nothing.
  - A one-byte edit in a shared tile keeps the 6 pieces that use it.
- Still not Perfect's own drawing: the body below the head on these 172 pieces is Raw's Bret‑drawn body in
  Perfect's colours (the same singlet and build), and the 119 above. Poses Royal never drew have no example to
  rebuild from and need hand-drawn art.

### First pass (silhouette matches and hair)

**How a piece qualifies** (`tools/match_perfect_poses.py`, table `data/perfect-pose-matches.json`; indices
and metrics only, no pixels):
- Royal draws Bret and Perfect on the same frame indices and coordinates (812 of 828 frames share their
  origin). So a Raw Bret piece that matches a Royal Bret frame takes Royal Perfect's frame at the same index,
  placed by the measured transform (flip, dx, dy). Every placement is re-checked against the measured IoU.
- Accepted: IoU ≥ 0.95, or IoU ≥ 0.88 with colour-role agreement ≥ 0.6.
- Excluded:
  - Royal indices below 16 (shadows).
  - Royal frames drawn **only** from tiles that Bret's frame also uses (227 generic frames). Royal recolours
    these by palette, which gave Perfect brown hair in review (`p801`, `p802`, `p805`); `s617` and `s681`
    were wrong in shape or gear.
- Visual review: all 329 replacements, before and after, in Perfect's palette, ordered riskiest first. All
  show the same pose with Perfect's blond hair, singlet, kneepads and boots. (The sheets contain game art and
  stay private.)

**Hair on the remaining adapted pieces.** Standing and walking, the most visible poses, have no Royal match,
and gameplay showed Perfect there with Bret's dark hair. Bret's hair is his palette index 9 (Perfect index 7
after the adapted colour map, which nothing else maps to), dithered with black. The matched pieces confirm it:
co-located pixels turn Bret 9 into Perfect's hair indices 12/9/13 in ~73% of cases.
- Rule (`hair_changes` in `tools/convert_perfect_poses.py`, `hairChanges` in `editor/royal-import-core.js`):
  - Find 8-connected brown regions.
  - A region is hair when its neighbours are mostly dark rather than skin, and it is dithered with black
    (regions over 2 px need dither pixels ≥ 0.3 × size).
  - Hair becomes pale blond (13). Black inside the dither becomes beige (9). Black at its edge becomes dark
    brown (12), the shades Royal uses for Perfect's hair.
- Review:
  - A first version also lit armpit shadows (a solid brown patch next to the singlet). The dither condition
    removed those (445 → 377 pieces).
  - All 377 were reviewed before and after: hair now reads blond, and arm shading stays brown.
- Status: these pieces stay **adapted**. The hair *shape* is still Bret's (long, curly, which is close to
  Perfect's), and only the colour is Perfect's.
- Parity: Python and JS agree on all 1,102 adapted pieces, and the fresh build agrees with the upgrade.
- Upgrade path: an old import is recoloured only where the piece is unedited. The synthetic edit test kept
  the 5 pieces sharing the edited tile.

**Older imports, edits and space**
- `RAW_ROYAL_IMPORT_CORE.upgradePoses` (the editor's **Update Perfect-Plex**) repacks slot 12.
  - A piece is replaced only while its pixels still hash to the adapted art it supersedes (`replaces`).
  - Every other piece is decoded and stored again pixel for pixel, including your edits and the Perfect-Plex
    frames.
  - It refuses to run if another identity's edited tile was relocated into Perfect's space.
- Results:
  - A synthetic one-byte edit in a shared tile kept the affected pieces (2 Royal-matched; 5 with the hair
    rule in place) and replaced the rest.
  - Repack with nothing to replace: 1,732/1,732 pieces identical.
  - The repacked slot uses fewer tiles (12,139 primary / 7,856 secondary, against 12,655 / 8,667).
- Browser and Node agree:
  - Browser update of the RX3 stock build equals Node (uninstall, upgrade, reinstall) byte for byte.
  - Fresh browser import and upgrade carry the same 1,732 pieces.
  - v0.16 and pre-`569240b` imports update. All 13 receivers reinstall afterwards. Reopen and resave are
    byte-identical.

**Native gameplay** (`tools/check_perfect_poses_native.py`)
- Cold boot, controller only. Every second frame after character select, each 8×8 tile of Perfect's
  objects is looked up in his slot's pieces.

| Recipe on stock import v2 (`d15106fc…`) | Frames inspected | Perfect's tiles | Foreign tiles | Old-only Bret tiles | Changed pieces seen |
|---|---|---|---|---|---|
| `luna-attacker-left` | 987 | 34,622 | 0 | 0 | 17 |
| `owen-attacker-left` (pre-`--mash` recording) | 1,917 | 66,253 | 0 | 0 | 18 |

- "Changed pieces seen" counts Royal or recoloured pieces identified by a tile no other piece uses, so it
  undercounts.
- Reports: `evidence/perfect-ordinary-poses/*-tiles.json`.
- Gameplay: [GIF](../evidence/perfect-ordinary-poses/luna-match.gif) of Perfect's standing pose, now blond.
  Before this batch, that pose showed Bret's dark hair.

**Timing changes with the art.** The same inputs replay a different match on a build with different art:
game state first differs at frame 6,618, and the old recipes no longer reach the Perfect-Plex (both a composed
and a bot recipe were tried). Tile decode time feeds the game's timing, so controller recipes are
build-specific. All Perfect-Plex scenarios were re-recorded and re-verified on this batch's builds (matrix
above).

**Still open for Perfect**
- 1,102 adapted pieces have no Royal counterpart (Raw-only actions or generic frames). They need **authored**
  Perfect art. 377 of them carry his hair colour on Bret's shapes. Your visual review of the blond-hair
  result is requested: [GIF](../evidence/perfect-ordinary-poses/luna-match.gif).
- Upgrading a ROM made on this branch before the hair rule (marker `POSES-ROYAL2`, never released) reports
  its Royal pieces as "kept as edited". That is harmless but miscounted.
- 24 of the 289 earlier exact matches use generic Royal frames and need the same review.
- Per-action mapping of pieces (which moves show which pieces) is not built yet. That is part of the
  action-family matrix.

## Findings that shape the art

- Raw draws every worker on one shared base body. The same part index shows the same body position in
  every slot: silhouette agreement is 0.94–0.98 between stock slots, 0.88 for Luna and 0.91 for
  Yokozuna. Palette indices also have the same colour role in every slot.
- So a Royal pose can be rebuilt from the target's **own** Raw parts wherever Raw has a matching
  drawing. The tie-up poses (Royal 1–3) match Raw parts almost exactly, and the target's own head,
  hair, face paint and gear appear (Luna, Bam Bam, Scott, Sting, Syxx, Nash, Owen).
- Royal draws no receiver head in poses 4–9 (it is under the attacker's arm). Royal poses 9–12 (lift
  over, inverted, fall, landing) have no matching Raw drawing. There, only the donor's body with the
  target's colour roles is available; gear shapes such as Bam Bam's flames or nWo lettering must be
  **authored**.
- Luna's art uses colour roles differently (0.88 agreement), and no Royal donor is female. Her drawings
  need separate treatment.

## Open items

- **Your visual review** of the rebuilt Perfect-Plex receivers (review GIFs above) and of Mr. Perfect's Royal
  heads. The receivers are an automatic rebuild: where a costume differs most from the donor's (Owen's trunks and
  bare legs against Bret's tights, Bam Bam's flames, Doink's costume against Flair's), some regions are blotchy.
  Hand touch-ups can be made in the sprite editor on any "Receiving Perfect-Plex" pose.
- **Mr. Perfect still needs hand-drawn art** for 966 pieces whose drawing is Raw Bret's (172 now with Royal
  Perfect's head, 119 with only his hair colour). For most of these poses Royal has no matching drawing, so
  there is no complete example to rebuild them from.
- **Mirror match** in other game modes.
- **Not done:** bridge-to-pin (PP-5), Perfect's green shadow, and all other action families
  (see `docs/animation-coverage.md`).
