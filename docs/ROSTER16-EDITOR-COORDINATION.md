# Roster 16 and new editor ownership

The user requested Ric Flair from SNES Royal Rumble as added slot 16, and a new editor for the expanded roster.

Codex works on the separate roster branch and new `editor-v01/` application. Claude PR #1 head `c8666bb` is the integration reference; Claude's existing editor, animation coverage, Perfect-Plex and receiving artwork remain under his ownership and will not be overwritten. The new application will identify its source snapshot and preserve the source implementation for subsequent integration.

Before release: permanent allocation must cover existing gear reservations, all four added slots, profile/name/music assets and future sprite edits. Current Hogan/Boss Man prototypes must not be saved in the old editor. Native source extraction does not by itself establish imported move coverage.

Confirmed Flair source: SNES Royal Rumble USA selector 6, source hash pinned in `royal_rumble_sprites.py`; 828 piece entries decode. A cold native Flair/Shawn match verified 255 tile requests (123 unique IDs) against source bytes. Source palette entries are dimmed by one RGB5 level in native gameplay; original ROM colors and native observed colors must be distinguished.

Implemented: Flair selector 30 with actor-role guards, a sixteen-entry stat initializer, protected sixteen-slot editing/export and ROM-free Windows packaging. Browser edits/export/reopen pass; 50 native edited-Flair body snapshots match the editor pixels. The separate editor preserves Claude's code/art region byte-for-byte. See [verification](../evidence/roster16-editor/README.md).

Still pending: Flair's Figure Four, complete imported receiving/grapple/recovery coverage, Boss Man's finisher, expanded match-mode checks and automatic import of all added workers into arbitrary ROMs. This is a preview, not the finished v0.1 game release.
