# Hogan from Genesis Royal Rumble: active Codex task

The user supplied Genesis Royal Rumble (World) and requested Hulk Hogan's
graphics, his moves on Raw's SNES controller layout, and colors fitting the
SNES game. Goal: an additional independent wrestler, not replacing a current
slot. Do not claim a playable port before native Raw verification.

## Input

The supplied `.md` file is a binary 2 MiB Sega Genesis ROM, not Markdown.
Header: `SEGA GENESIS`, `WWF ROYAL RUMBLE`, `GM T-081196 00`, region `JUE`.
SHA-256: `fa8d80b0646fe463bea669c14590ddbfe0a55142ae924098503185b864cc66a4`.
Keep the ROM, source pixels and emulator state private.

## Coordination

Codex owns new Genesis analysis/extraction tools and the Hogan conversion/
importer work. Claude owns the current-roster artwork/coverage assignment.
Claude should continue against its corrected 13-slot base; Hogan will be added
to the coverage inventory when his import is ready. Avoid simultaneous edits
to Claude's existing sprite manifests, paired hooks and browser integration.
Use separate Hogan-specific modules and agree on shared integration files before
changing them. Adding Hogan must preserve Mr. Perfect and the original twelve.

## Required work

1. Verify Genesis Hogan's identity, palette and pose data with native gameplay;
   recover sprite pieces, geometry, compression/source references and sequencing.
2. Convert Genesis packed tiles and component geometry to Raw's planar graphics,
   descriptors and private tile storage. Author missing Raw action/receiving
   poses in the original SNES game's style; source extraction alone is not a
   complete compatible wrestler.
3. Preserve Hogan's yellow/red gear, blond hair and mustache with coherent SNES
   shading. Review native-size previews and gameplay rather than indiscriminate
   saturation increases. Keep palette indices editable and within renderer limits.
4. Add an independent logical slot after Perfect, with profiles/menu/HUD assets,
   private graphics and correct move routing. Audit roster-size assumptions and
   NPC selectors before changing tables.
5. Map supported moves to Raw's existing SNES controls (run, grapple, punch,
   kick and contextual finisher). Source Genesis buttons do not directly define
   Raw actions. Verify Hogan's finisher and all eligible receiver identities.
6. Provide editable composite poses/animations through the editor in coordination
   with Claude, plus controller-only Raw gameplay proof and preservation tests.

## Current status

Input and source graphics verified; no Raw slot has been verified yet.
Building a Genesis Plus GX observation core at pinned commit
`393f70cd64c7334564c19a424c383f53986c13f4`, with read-only VRAM/CRAM/SAT/register
exposure, to obtain native source evidence. Maintain findings here as work proceeds.

Source identity is internal worker 6 / native selector 12, not portrait-menu
position 2. Both player positions were identified with read-only renderer
traces. Source frame geometry, tile packing and per-actor palette-byte translation
are implemented in the new Genesis tools.

All 835 Hogan component entries and 647 common composites parse. Native checks
match 573 completed-object last tiles across all four compression families,
69 complete basic-action snapshot bodies, and 62/63 checked leg-drop snapshots.
The unmatched first finisher transition still needs investigation. Native source
leg drop action `0x170` uses distinct landing poses 475–479; activation was
captured using A+B near a downed opponent below 20 source health, without RAM
edits. Planned SNES mapping is Raw's contextual R finisher, with Y run, B punch,
A kick and X grapple; those Raw routes are not implemented or verified yet.

An exact normalized Bret-silhouette comparison finds 201 unambiguous source
piece candidates among 1,720 Raw entries (203 have any exact candidate).
These are geometry candidates, not validated action assignments. Other Raw-only
poses will require further mapping or authored Hogan art. Source details and
gameplay proof: [Hogan source evidence](../evidence/hogan-genesis-source/README.md).
