#!/usr/bin/env python3
"""Copy the NES Tecmo Super Bowl rosters into SNES Tecmo Super Bowl.

Reads an unmodified-layout NES ROM (iNES, 393,232 bytes) and SNES ROM
(headerless LoROM, 1,572,864 bytes) and writes a new SNES ROM whose 28 team
rosters are the NES ones: names, jersey numbers, all player ratings, skin
colour, kick/punt returners, simulation data and the Pro Bowl selections.
The input files are never modified.

The SNES game keeps two extra bench defensive backs per team (32 players
against the NES 30). Those two spots are filled with original SNES defensive
backs of the same team who do not appear anywhere on the NES rosters, so no
player is listed twice.

Formations, playbooks, uniforms and every other non-roster setting stay SNES.
Start a new season save (or use Team Data -> Reset Players) after loading the
new ROM, because SNES saves keep their own copy of starters and returners.
"""

from __future__ import annotations

import argparse
import hashlib
import struct
from dataclasses import dataclass
from pathlib import Path

TEAMS = 28

# ---- NES layout (offsets are file offsets including the 16-byte iNES header)
NES_SIZE = 0x60010
NES_NAME_POINTERS = 0x48          # 840 little-endian CPU pointers ($8000 bank)
NES_PLAYERS_PER_TEAM = 30
NES_ATTRS = 0x3010                # 28 x 0x75 byte team blocks
NES_ATTR_TEAM = 0x75
NES_RETURNERS = (0x239D3, 0x328D3)  # two identical copies; KR hi / PR lo nibble
NES_SIM = 0x18163                 # 28 x 0x30, same layout as SNES
NES_SIM_OFFENSE_PREF = 0x27526    # 28 bytes, NES team order
NES_PRO_BOWL = (0x32853, 0x3288F)  # AFC, NFC: 30 x (team, slot), read at $8843

# ---- SNES layout (headerless file offsets; LoROM bank $2F = 0x178000)
SNES_SIZE = 0x180000
SNES_NAME_BANK = 0x178000
SNES_NAME_POINTERS = 0x178038     # 28 x 32 pointers + one end pointer
SNES_NAME_DATA = 0x17873A
SNES_NAME_LIMIT = 0x17B7F0        # first byte the name data must not reach
SNES_PLAYERS_PER_TEAM = 32
SNES_ATTRS = 0x17E000             # 28 x 0x7D byte team blocks
SNES_ATTR_TEAM = 0x7D
SNES_RETURN_INDEX = 0x170C90      # per team: KR index hi nibble, PR index lo
SNES_RETURN_TEAM = 0x170CB0       # per team: three slots + 0x80
SNES_SIM = 0x26ACF                # 28 x 0x30, NES team order
SNES_SIM_OFFENSE_PREF = 0x15DFA   # 28 bytes, SNES team order
SNES_PRO_BOWL = (0x170C00, 0x170C48)  # AFC, NFC: 35 x (slot, team)
SNES_PRO_BOWL_ENTRIES = 35
SNES_CHECKSUM = 0x7FDC
SIM_TEAM_BYTES = 0x30

# Bytes per player in the rating tables, by slot. Slots 30-31 are SNES only.
ATTR_SIZES = [5, 5] + [4] * 10 + [3] * 5 + [4] * 11 + [4, 4] + [4, 4]
ATTR_OFFSETS = [sum(ATTR_SIZES[:i]) for i in range(len(ATTR_SIZES))]
FACE_BYTE = 2   # NES face number; the SNES uses only the skin bit (0x80)
POSITIONS = [
    "QB1", "QB2", "RB1", "RB2", "RB3", "RB4", "WR1", "WR2", "WR3", "WR4",
    "TE1", "TE2", "C", "LG", "RG", "LT", "RT", "RE", "NT", "LE", "ROLB",
    "RILB", "LILB", "LOLB", "RCB", "LCB", "FS", "SS", "K", "P", "DB1", "DB2",
]
DB_SLOTS = range(24, 28)

NES_TEAMS = [
    "bills", "colts", "dolphins", "patriots", "jets", "bengals", "browns",
    "oilers", "steelers", "broncos", "chiefs", "raiders", "chargers",
    "seahawks", "redskins", "giants", "eagles", "cardinals", "cowboys",
    "bears", "lions", "packers", "vikings", "buccaneers", "49ers", "rams",
    "saints", "falcons",
]
SNES_TEAMS = [
    "bills", "colts", "dolphins", "patriots", "jets", "bengals", "browns",
    "oilers", "steelers", "broncos", "chiefs", "raiders", "chargers",
    "seahawks", "cowboys", "giants", "eagles", "cardinals", "redskins",
    "bears", "lions", "packers", "vikings", "buccaneers", "falcons", "rams",
    "saints", "49ers",
]
SNES_TO_NES = [NES_TEAMS.index(team) for team in SNES_TEAMS]
NES_TO_SNES = [SNES_TEAMS.index(team) for team in NES_TEAMS]

# Known dumps the offsets were verified against (other revisions/hacks are
# accepted if they pass the structural checks, with a warning).
KNOWN_NES_SHA1 = "0f0284970cffc719c9993a9303e72077c0f8513a"
KNOWN_SNES_SHA1 = "c376a45c72612e35592edb90f637a7e3e55561ce"


@dataclass
class Player:
    name: bytes        # first name lower case + last name upper case
    number: int        # BCD jersey number byte
    attrs: bytes       # rating bytes in the shared NES/SNES format

    @property
    def text(self) -> str:
        cut = first_name_length(self.name)
        first, last = self.name[:cut].decode(), self.name[cut:].decode()
        return f"{first.title()} {last.title()}".strip()

    @property
    def jersey(self) -> str:
        return f"{self.number:02X}"


def first_name_length(name: bytes) -> int:
    """Names are stored as lower-case first name then upper-case last name."""
    cut = 0
    while cut < len(name) and not (65 <= name[cut] <= 90):
        cut += 1
    return cut


def bank_pointer_to_offset(pointer: int, bank_base: int) -> int:
    return bank_base + pointer - 0x8000


def read_names(rom: bytes, pointer_table: int, count: int, bank_base: int,
               end: int | None) -> list[bytes]:
    pointers = [struct.unpack_from("<H", rom, pointer_table + 2 * i)[0]
                for i in range(count)]
    starts = [bank_pointer_to_offset(p, bank_base) for p in pointers]
    if end is None:  # NES: no end pointer, data is 0xFF terminated
        end = starts[-1]
        while rom[end] != 0xFF:
            end += 1
    stops = starts[1:] + [end]
    return [rom[a:b] for a, b in zip(starts, stops)]


def split_entry(entry: bytes) -> tuple[int, bytes]:
    if len(entry) < 2:
        raise ValueError(f"Malformed name entry {entry!r}")
    return entry[0], entry[1:]


def check_bcd(value: int, label: str) -> None:
    if (value >> 4) > 9 or (value & 15) > 9:
        raise ValueError(f"{label}: jersey byte {value:02X} is not BCD")


def read_nes(rom: bytes) -> list[list[Player]]:
    entries = read_names(rom, NES_NAME_POINTERS, TEAMS * NES_PLAYERS_PER_TEAM,
                         0x10, None)
    teams = []
    for team in range(TEAMS):
        roster = []
        block = NES_ATTRS + team * NES_ATTR_TEAM
        for slot in range(NES_PLAYERS_PER_TEAM):
            number, name = split_entry(entries[team * NES_PLAYERS_PER_TEAM + slot])
            check_bcd(number, f"NES {NES_TEAMS[team]} {POSITIONS[slot]}")
            start = block + ATTR_OFFSETS[slot]
            roster.append(Player(name, number, rom[start:start + ATTR_SIZES[slot]]))
        teams.append(roster)
    return teams


def read_snes(rom: bytes) -> list[list[Player]]:
    count = TEAMS * SNES_PLAYERS_PER_TEAM
    end = bank_pointer_to_offset(
        struct.unpack_from("<H", rom, SNES_NAME_POINTERS + 2 * count)[0],
        SNES_NAME_BANK)
    entries = read_names(rom, SNES_NAME_POINTERS, count, SNES_NAME_BANK, end)
    teams = []
    for team in range(TEAMS):
        roster = []
        block = SNES_ATTRS + team * SNES_ATTR_TEAM
        for slot in range(SNES_PLAYERS_PER_TEAM):
            number, name = split_entry(entries[team * SNES_PLAYERS_PER_TEAM + slot])
            start = block + ATTR_OFFSETS[slot]
            roster.append(Player(name, number, rom[start:start + ATTR_SIZES[slot]]))
        teams.append(roster)
    return teams


def snes_name(name: bytes) -> bytes:
    """Use the SNES spelling convention: '.' instead of spaces in first names.

    The SNES release itself writes the NES "freddie joeNUNN" as
    "freddie.joeNUNN"; spaces inside last names ("DE BERG") are kept.
    """
    cut = first_name_length(name)
    return name[:cut].replace(b" ", b".") + name[cut:]


def validate(nes: bytes, snes: bytes) -> list[str]:
    warnings = []
    if len(nes) != NES_SIZE or nes[:4] != b"NES\x1a":
        raise ValueError("NES ROM must be the 393,232-byte iNES Tecmo Super Bowl dump")
    if len(snes) != SNES_SIZE or snes[0x7FC0:0x7FD0] != b"TECMO SUPER BOWL":
        raise ValueError("SNES ROM must be the headerless 1.5 MiB Tecmo Super Bowl "
                         "(USA) dump; remove a 512-byte copier header first")
    team_pointers = [struct.unpack_from("<H", snes, SNES_NAME_BANK + 2 * t)[0]
                     for t in range(TEAMS)]
    if team_pointers != [0x8038 + 0x40 * t for t in range(TEAMS)]:
        raise ValueError("SNES team pointer table is not the expected layout")
    if hashlib.sha1(nes).hexdigest() != KNOWN_NES_SHA1:
        warnings.append("NES ROM differs from the verified dump; layout checks passed")
    if hashlib.sha1(snes).hexdigest() != KNOWN_SNES_SHA1:
        warnings.append("SNES ROM differs from the verified dump; layout checks passed")
    return warnings


def snes_checksum(rom: bytearray) -> int:
    """Checksum for a 1.5 MiB LoROM: the upper 512 KiB is mirrored twice."""
    rom[SNES_CHECKSUM:SNES_CHECKSUM + 4] = b"\xff\xff\x00\x00"
    return (sum(rom[:0x100000]) + 2 * sum(rom[0x100000:])) & 0xFFFF


def choose_bench_dbs(snes_roster: list[Player], nes_names: set[bytes],
                     own_team: set[bytes]) -> tuple[list[Player], list[str]]:
    """Two SNES defensive backs for slots 30-31.

    Prefer the team's SNES DBs who are on no NES roster at all; otherwise
    accept one who is on another NES team (never a duplicate within a team).
    """
    candidates = [snes_roster[slot] for slot in (30, 31, *DB_SLOTS)]
    chosen: list[Player] = []
    notes: list[str] = []
    for allow_other_team in (False, True):
        for player in candidates:
            if len(chosen) == 2 or player in chosen or player.name in own_team:
                continue
            if player.name in nes_names and not allow_other_team:
                continue
            if player.name in nes_names:
                notes.append(player.text)
            chosen.append(player)
    if len(chosen) != 2:
        raise ValueError("Could not find two SNES defensive backs for the bench")
    return chosen, notes


def convert(nes: bytes, snes: bytes) -> tuple[bytearray, dict]:
    warnings = validate(nes, snes)
    nes_teams = read_nes(nes)
    snes_teams = read_snes(snes)
    nes_names = {p.name for roster in nes_teams for p in roster}
    if nes[NES_RETURNERS[0]:NES_RETURNERS[0] + TEAMS] != \
            nes[NES_RETURNERS[1]:NES_RETURNERS[1] + TEAMS]:
        warnings.append("NES returner tables disagree; using the first copy")

    out = bytearray(snes)
    report: dict = {"warnings": warnings, "teams": [], "pro_bowl": []}
    new_rosters: list[list[Player]] = []

    for team in range(TEAMS):
        nes_team = SNES_TO_NES[team]
        roster = [
            Player(snes_name(p.name), p.number,
                   p.attrs[:FACE_BYTE] + bytes([p.attrs[FACE_BYTE] & 0x80])
                   + p.attrs[FACE_BYTE + 1:])
            for p in nes_teams[nes_team]
        ]
        bench, shared = choose_bench_dbs(snes_teams[team], nes_names,
                                         {p.name for p in nes_teams[nes_team]})
        roster += bench
        for name in shared:
            warnings.append(f"{SNES_TEAMS[team].title()} bench DB {name} is also on "
                            "another team's NES roster (no unduplicated SNES DB left)")
        new_rosters.append(roster)

        block = SNES_ATTRS + team * SNES_ATTR_TEAM
        for slot, player in enumerate(roster):
            start = block + ATTR_OFFSETS[slot]
            assert len(player.attrs) == ATTR_SIZES[slot]
            out[start:start + ATTR_SIZES[slot]] = player.attrs

        # Returners. The SNES lists a three-man return team; KR and PR are
        # indexes into it and may point at the same man (as the NES allows).
        kr_pr = nes[NES_RETURNERS[0] + nes_team]
        kr, pr = kr_pr >> 4, kr_pr & 15
        location = SNES_RETURN_TEAM + 4 * team
        first, second, deep_back, terminator = out[location:location + 4]
        if kr == pr:
            decoy = next(s for s in (second, first, 2, 3, 4, 5)
                         if s not in (kr, deep_back))
            out[location:location + 3] = bytes([kr, decoy, deep_back])
            out[SNES_RETURN_INDEX + team] = 0x00
        else:
            out[location:location + 3] = bytes([kr, pr, deep_back])
            out[SNES_RETURN_INDEX + team] = 0x01
        assert terminator == 0x80
        report["teams"].append({
            "team": SNES_TEAMS[team],
            "roster": roster,
            "kr": roster[kr], "pr": roster[pr],
            "return_team": [roster[s] for s in out[location:location + 3]],
            "bench_dbs": roster[30:],
        })

    # Names: rebuild the pointer table and string area in place.
    cursor = SNES_NAME_DATA
    pointers = []
    old_end = bank_pointer_to_offset(
        struct.unpack_from("<H", snes, SNES_NAME_POINTERS + 2 * TEAMS * 32)[0],
        SNES_NAME_BANK)
    area_end = max(old_end, cursor)
    for roster in new_rosters:
        for player in roster:
            data = bytes([player.number]) + player.name
            pointers.append(cursor)
            out[cursor:cursor + len(data)] = data
            cursor += len(data)
    pointers.append(cursor)
    if cursor > SNES_NAME_LIMIT:
        raise ValueError("Converted names do not fit in the SNES name area")
    out[cursor:max(area_end, cursor)] = b"\xff" * (max(area_end, cursor) - cursor)
    for index, offset in enumerate(pointers):
        struct.pack_into("<H", out, SNES_NAME_POINTERS + 2 * index,
                         offset - SNES_NAME_BANK + 0x8000)
    report["name_bytes"] = (SNES_NAME_DATA, cursor)

    # Simulation data: identical 0x30-byte format, both tables in NES order.
    sim_size = TEAMS * SIM_TEAM_BYTES
    out[SNES_SIM:SNES_SIM + sim_size] = nes[NES_SIM:NES_SIM + sim_size]
    for team in range(TEAMS):
        value = nes[NES_SIM_OFFENSE_PREF + SNES_TO_NES[team]]
        if value > 3:
            raise ValueError(f"Unexpected NES sim offense preference {value}")
        out[SNES_SIM_OFFENSE_PREF + team] = value

    # Pro Bowl: the NES all-star selections for the 30 positions (the NES
    # stores (team, slot); the SNES stores (slot, team)). The SNES adds two
    # bench DBs and a three-man return unit; its return specialists are
    # matched by name to the same players on the NES rosters.
    nes_lookup = {p.name: (team, slot) for team, roster in enumerate(nes_teams)
                  for slot, p in enumerate(roster)}
    for conference, (nes_table, snes_table) in enumerate(zip(NES_PRO_BOWL, SNES_PRO_BOWL)):
        selection = []
        for entry in range(30):
            nes_team, slot = nes[nes_table + 2 * entry], nes[nes_table + 2 * entry + 1]
            if slot >= NES_PLAYERS_PER_TEAM or nes_team >= TEAMS:
                raise ValueError("Unexpected NES Pro Bowl entry")
            selection.append((slot, NES_TO_SNES[nes_team]))
        conference_teams = range(14 * conference, 14 * conference + 14)
        for entry in range(30, SNES_PRO_BOWL_ENTRIES):
            slot, team = snes[snes_table + 2 * entry], snes[snes_table + 2 * entry + 1]
            original = snes_teams[team][slot].name
            found = nes_lookup.get(original)
            if found and NES_TO_SNES[found[0]] in conference_teams:
                selection.append((found[1], NES_TO_SNES[found[0]]))
            else:  # fall back to the NES right cornerback / first runner
                selection.append(selection[24] if entry < 33 else selection[2 + entry - 33])
        for entry, (slot, team) in enumerate(selection):
            out[snes_table + 2 * entry:snes_table + 2 * entry + 2] = bytes([slot, team])
        report["pro_bowl"].append([(POSITIONS[e] if e < 30 else
                                    ("DB1", "DB2", "RET1", "RET2", "RET3")[e - 30],
                                    SNES_TEAMS[t], new_rosters[t][s])
                                   for e, (s, t) in enumerate(selection)])

    checksum = snes_checksum(out)
    struct.pack_into("<HH", out, SNES_CHECKSUM, checksum ^ 0xFFFF, checksum)
    report["checksum"] = checksum
    return out, report


def make_ips(original: bytes, patched: bytes) -> bytes:
    if len(original) != len(patched):
        raise ValueError("IPS writer expects equal-size ROMs")
    records = bytearray(b"PATCH")
    i = 0
    while i < len(patched):
        if original[i] == patched[i]:
            i += 1
            continue
        start = i
        while i < len(patched) and i - start < 0xFFFF:
            if original[i] != patched[i]:
                i += 1
            elif patched[i:i + 6] != original[i:i + 6]:
                i += 1  # bridge short runs of unchanged bytes
            else:
                break
        if start == 0x454F46:  # would read as "EOF"
            start -= 1
        records += start.to_bytes(3, "big") + (i - start).to_bytes(2, "big")
        records += patched[start:i]
    return bytes(records + b"EOF")


def write_report(report: dict, path: Path) -> None:
    lines = ["# NES rosters in SNES Tecmo Super Bowl", ""]
    for note in report["warnings"]:
        lines.append(f"> Note: {note}")
    lines += ["Slots 1-30 come from NES Tecmo Super Bowl. DB1/DB2 are SNES-only",
              "bench defensive backs kept from the SNES game (never duplicates).", ""]
    for team in report["teams"]:
        lines.append(f"## {team['team'].title()}")
        lines.append("")
        lines.append("| Pos | # | Player |")
        lines.append("|---|---|---|")
        for pos, player in zip(POSITIONS, team["roster"]):
            lines.append(f"| {pos} | {player.jersey} | {player.text} |")
        ret = ", ".join(p.text for p in team["return_team"])
        lines += ["", f"KR: {team['kr'].text} · PR: {team['pr'].text} · "
                  f"Return team: {ret}", ""]
    for name, selection in zip(("AFC", "NFC"), report["pro_bowl"]):
        lines += [f"## {name} Pro Bowl", "", "| Pos | Team | Player |", "|---|---|---|"]
        lines += [f"| {pos} | {team.title()} | {player.text} |" for pos, team, player in selection]
        lines.append("")
    path.write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("nes", type=Path, help="Tecmo Super Bowl (USA) .nes")
    parser.add_argument("snes", type=Path, help="Tecmo Super Bowl (USA) .sfc")
    parser.add_argument("output", type=Path, help="new .sfc to write")
    parser.add_argument("--ips", type=Path, help="also write an IPS patch")
    parser.add_argument("--report", type=Path, help="also write a Markdown roster list")
    args = parser.parse_args()
    for path in (args.nes, args.snes):
        if path.resolve() == args.output.resolve():
            parser.error("Output must not overwrite an input ROM")
    snes = args.snes.read_bytes()
    out, report = convert(args.nes.read_bytes(), snes)
    args.output.write_bytes(out)
    if args.ips:
        args.ips.write_bytes(make_ips(snes, bytes(out)))
    if args.report:
        write_report(report, args.report)
    for note in report["warnings"]:
        print("Note:", note)
    start, end = report["name_bytes"]
    print(f"Wrote {args.output} ({len(out):,} bytes, checksum {report['checksum']:04X}; "
          f"names use {end - start:,} bytes)")


if __name__ == "__main__":
    main()
