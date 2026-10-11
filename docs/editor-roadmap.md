# WWF Raw editor roadmap

The goal is an editor that lets people change wrestlers and eventually the
game's graphics, menus, music, roster and moves. Research should produce reusable
asset maps and editing tools, with Bret's outfit serving as the first prototype.

## 1. Map the complete stock roster

Identify each character's directory, palettes, primary and lower-body parts,
shared graphics, and animation references. Assign character names only after
confirming them in the running game; a directory selector alone is not a name.

For each character, record:

- ROM revision and original hash; directory and source addresses.
- Compression, palette, object layout and frame composition.
- Which actions use each frame, including giving and receiving moves.
- Assets shared with other wrestlers, referees or scenery.
- Evidence and verification status, with unknown actions left explicit.

Capture controlled matches to cover walking, running, turns, ropes, strikes,
grapples, special moves, damage, falls, recovery, pins and ringside actions.
Directory entry counts describe an inventory, not completed move coverage.

Current evidence: all twelve roster identities and primary/secondary directories
are inventoried. Each wrestler now has a verified original-game finisher and
Mega Move capture with native part references for both actors; see the
[roster special evidence](../evidence/roster-specials/README.md). This is one
working setup per special, not complete action or variant coverage. Shared
fallback inventories and ordinary action mapping remain incomplete. Bret's
edited outfit is verified for 173 paired movement frames, not these specials.

## 2. Build the first character editor

Start with replacing graphics and palettes for an existing roster slot. Preview
assembled animations rather than asking users to edit jumbled tile sheets.
Show shared-asset dependencies before an edit affects another character.

Use the same asset model for preview, export and validation. Support reversible
project files and patch export against a known original ROM. Keep the original
ROM unchanged. Verify re-encoding, frame composition, palette changes and actual
gameplay before declaring a character replacement complete.

The first milestone is one editable wrestler whose outfit survives every mapped
action, followed by applying that workflow across the stock roster.

## 3. Expand graphics and menu editing

Inventory portraits, fonts, logos, backgrounds, arenas, menus and their tilemaps
and palettes. Existing interface decoders are a starting point; successful
decompression alone does not identify an asset or prove safe reinsertion.

## 4. Research music and sound editing

Identify the audio driver, song sequences, instruments, samples and upload
tables. Graphics codecs do not establish an audio format. Begin with verified
replacement of an existing sound or track before offering composition tools.

## 5. Investigate roster expansion and cross-game imports

Compare specific SNES WWF Acclaim titles for graphics formats, frame layouts,
palettes and animation conventions. Treat imported wrestlers as conversions
until compatibility is demonstrated.

Replacing a slot and adding a slot are separate milestones. Expansion requires
locating roster limits and every dependent system: selection screens, names,
portraits, palettes, animation tables, move assignments, AI and match logic.
Additional ROM space alone does not establish support for more characters.

## 6. Research move creation

Map action states, animation sequences, collision and grapple rules, damage,
opponent reactions, transitions and AI. Start with reassigning a verified
existing move, then modifying it, before creating a new move with coordinated
attacker and defender behavior.

## Immediate next milestone

Extend the shared fallback inventory using the new special captures, then map
ordinary grapples, strikes, rope interactions, damage and recovery across the
roster. Use the evidence-linked coverage table to track remaining actions and
validate edited outfits before including them in editor claims.
