# NES rosters for SNES Tecmo Super Bowl

`tsb_nes_rosters_to_snes.py` copies the 28 team rosters from NES *Tecmo Super
Bowl* (USA) into SNES *Tecmo Super Bowl* (USA). It writes a new `.sfc` and,
optionally, an IPS patch and a Markdown roster list. No ROM data is stored in
this repository.

```bash
python3 tecmo/tsb_nes_rosters_to_snes.py "Tecmo Super Bowl (USA).nes" "Tecmo Super Bowl (USA).sfc" "Tecmo Super Bowl (NES Rosters).sfc" --ips nes-rosters.ips --report rosters.md
```

The SNES ROM must be headerless (1,572,864 bytes). Verified dumps: NES SHA-1
`0f0284970cffc719c9993a9303e72077c0f8513a`, SNES SHA-1
`c376a45c72612e35592edb90f637a7e3e55561ce`. Other dumps are accepted with a
warning if their tables have the same layout.

## What changes

| Data | SNES location | Source |
|---|---|---|
| Names and jersey numbers, 32 per team | `0x178038` pointers, `0x17873A` text | NES `0x48`; the SNES spells spaces in first names as `.` |
| Ratings (RS, RP, MS, HP and position ratings) | `0x17E000`, `0x7D` per team | NES `0x3010`, byte for byte |
| Skin colour | rating byte 2 | NES face byte, high bit only (the SNES has no faces) |
| Kick and punt returners | `0x170C90`, `0x170CB0` | NES `0x239D3` |
| Simulation ratings and team sim strength | `0x26ACF` | NES `0x18163` (same format, both in NES team order) |
| Simulation run/pass tendency | `0x15DFA` | NES `0x27526` |
| AFC and NFC Pro Bowl | `0x170C00`, `0x170C48` | NES `0x32853`, `0x3288F` |
| Header checksum | `0x7FDC` | recalculated |

The SNES teams carry two extra bench defensive backs (32 players versus the
NES 30). They stay SNES 1993 players, chosen so nobody appears twice on a
team. Denver has only one such player, so Charles Dimry also appears with
Atlanta. The SNES Pro Bowl's three dedicated return men are mapped by name to
the same players on the NES rosters (Woodson, Verdin, Metcalf; Sanders, Gray,
Sikahema).

Unchanged: playbooks, offensive formations, uniforms, schedule, menus and the
"rosters accurate as of August 16, 1993" screen.

After loading the new ROM, start without an old SNES save, or use **Team Data →
Reset Players**, because saves keep their own starters and returners.

## Verification

`python3 -m unittest tests/test_tecmo_rosters.py` runs the ROM-free checks. Set
`TSB_NES_ROM` and `TSB_SNES_ROM` to also convert and check every player, the
changed byte ranges, the checksum and the IPS patch. The converted ROM was also
checked in Snes9x: Team Data, starters, returners and both Pro Bowl screens, a
player ratings page, and a kickoff and scrimmage play.
