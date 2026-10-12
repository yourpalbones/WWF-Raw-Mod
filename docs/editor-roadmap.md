## Scott gear pass (v0.8)

Scott now has 207 native full-body captures and 1,720 parsed frame pieces:
953 wrestler-specific entries plus 767 structurally decoded common entries.
The reference gear recipe clones modified descriptors and tiles into a 6 MiB
ExHiROM. Actor guards redirect the common pieces only for Scott; original shared
sources and other eleven palettes remain unchanged. Captures cover walking,
strikes, rope running, giving/taking grapples, finisher and Mega Move.
Exhaustive action, interruption, reversal and ring-position coverage remains
unverified. Detailed trunk marks and elbow artwork need further visual review.

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

## Current findings and next milestones

The editor now updates the in-match health-bar name separately from the bio and
large logo. All twelve exported labels are verified in native drawing buffers;
see [name evidence](../evidence/match-names/README.md).

Theme reassignment and custom melodic MIDI import are available in v0.5. Complete
songs compile into up to eight native streams with tempo changes, sustain,
velocity, rests, long notes and looping. All twelve theme slots pass native
upload/playback checks; a 92.8-second four-part composition completes and loops
twice. Projects preserve imported notes and exported ROMs reopen byte-for-byte.
Stock sound selection replaces MIDI program changes. Percussion, pitch bends,
General MIDI instrument mapping and recorded-audio streaming remain future work.
See [playback proof](../evidence/custom-midi/README.md).

A relocated thirteenth profile is selectable and enters a native match. It still
uses a placeholder label and Shawn's directory, and reads beyond the stock
small-monitor arrays. The next expansion step is one fully independent extra
wrestler, including its assets, initialized attributes, move/special assignments
and match-mode tests. This experiment is not shipped as an editor feature.
See [extra-slot evidence](../evidence/roster-expansion/README.md).

Complete ordinary action and shared-fallback mapping remains necessary for gear
editing and cross-game character imports. An added selection does not establish
complete move coverage or safe conversion of another game's sprite set.
