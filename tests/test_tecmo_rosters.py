"""Tecmo Super Bowl NES -> SNES roster converter checks.

ROM-free tests always run. Set TSB_NES_ROM and TSB_SNES_ROM to the USA dumps
to also convert locally and check the output.
"""

import os
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tecmo"))
import tsb_nes_rosters_to_snes as tsb

NES_ROM = os.environ.get("TSB_NES_ROM")
SNES_ROM = os.environ.get("TSB_SNES_ROM")


def apply_ips(original: bytes, patch: bytes) -> bytes:
    data = bytearray(original)
    assert patch[:5] == b"PATCH"
    i = 5
    while patch[i:i + 3] != b"EOF":
        offset = int.from_bytes(patch[i:i + 3], "big")
        size = int.from_bytes(patch[i + 3:i + 5], "big")
        i += 5
        data[offset:offset + size] = patch[i:i + size]
        i += size
    return bytes(data)


class RomFreeTests(unittest.TestCase):
    def test_team_orders_are_permutations(self):
        self.assertEqual(sorted(tsb.SNES_TO_NES), list(range(tsb.TEAMS)))
        for snes_index, nes_index in enumerate(tsb.SNES_TO_NES):
            self.assertEqual(tsb.NES_TO_SNES[nes_index], snes_index)
            self.assertEqual(tsb.SNES_TEAMS[snes_index], tsb.NES_TEAMS[nes_index])

    def test_rating_layout_sizes(self):
        self.assertEqual(sum(tsb.ATTR_SIZES[:30]), tsb.NES_ATTR_TEAM)
        self.assertEqual(sum(tsb.ATTR_SIZES), tsb.SNES_ATTR_TEAM)

    def test_first_name_spaces_follow_snes_spelling(self):
        self.assertEqual(tsb.snes_name(b"freddie joeNUNN"), b"freddie.joeNUNN")
        self.assertEqual(tsb.snes_name(b"steveDE BERG"), b"steveDE BERG")
        self.assertEqual(tsb.snes_name(b"c.BENNETT"), b"c.BENNETT")
        self.assertEqual(tsb.Player(b"c.BENNETT", 0x97, b"").text, "C. Bennett")

    def test_ips_round_trip(self):
        original = bytes(range(256)) * 300
        patched = bytearray(original)
        patched[10:14] = b"abcd"
        patched[20] ^= 0xFF
        patched[70000:70100] = b"x" * 100
        patch = tsb.make_ips(original, bytes(patched))
        self.assertEqual(apply_ips(original, patch), bytes(patched))


@unittest.skipUnless(NES_ROM and SNES_ROM, "set TSB_NES_ROM and TSB_SNES_ROM")
class RomTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nes = Path(NES_ROM).read_bytes()
        cls.snes = Path(SNES_ROM).read_bytes()
        cls.out, cls.report = tsb.convert(cls.nes, cls.snes)

    def test_players_match_nes(self):
        nes_teams = tsb.read_nes(self.nes)
        out_teams = tsb.read_snes(bytes(self.out))
        for team, roster in enumerate(out_teams):
            source = nes_teams[tsb.SNES_TO_NES[team]]
            for slot in range(30):
                nes_player, snes_player = source[slot], roster[slot]
                face = nes_player.attrs[tsb.FACE_BYTE] & 0x80
                expected = (nes_player.attrs[:2] + bytes([face])
                            + nes_player.attrs[3:])
                self.assertEqual(snes_player.name, tsb.snes_name(nes_player.name))
                self.assertEqual(snes_player.number, nes_player.number)
                self.assertEqual(snes_player.attrs, expected)
            own = {p.name for p in source}
            self.assertFalse({p.name for p in roster[30:]} & own)

    def test_only_roster_tables_change(self):
        allowed = [
            (tsb.SNES_CHECKSUM, tsb.SNES_CHECKSUM + 4),
            (tsb.SNES_SIM_OFFENSE_PREF, tsb.SNES_SIM_OFFENSE_PREF + tsb.TEAMS),
            (tsb.SNES_SIM, tsb.SNES_SIM + tsb.TEAMS * tsb.SIM_TEAM_BYTES),
            (tsb.SNES_PRO_BOWL[0], tsb.SNES_PRO_BOWL[1] + 2 * tsb.SNES_PRO_BOWL_ENTRIES),
            (tsb.SNES_RETURN_INDEX, tsb.SNES_RETURN_INDEX + tsb.TEAMS),
            (tsb.SNES_RETURN_TEAM, tsb.SNES_RETURN_TEAM + 4 * tsb.TEAMS),
            (tsb.SNES_NAME_POINTERS, tsb.SNES_NAME_LIMIT),
            (tsb.SNES_ATTRS, tsb.SNES_ATTRS + tsb.TEAMS * tsb.SNES_ATTR_TEAM),
        ]
        for i, (before, after) in enumerate(zip(self.snes, self.out)):
            if before != after:
                self.assertTrue(any(lo <= i < hi for lo, hi in allowed), hex(i))

    def test_checksum_and_patch(self):
        out = bytes(self.out)
        total = (sum(out[:0x100000]) + 2 * sum(out[0x100000:])) & 0xFFFF
        self.assertEqual(int.from_bytes(out[0x7FDE:0x7FE0], "little"), total)
        self.assertEqual(int.from_bytes(out[0x7FDC:0x7FDE], "little"), total ^ 0xFFFF)
        self.assertEqual(apply_ips(self.snes, tsb.make_ips(self.snes, out)), out)

    def test_pro_bowl_uses_nes_selection(self):
        afc = self.report["pro_bowl"][0]
        self.assertEqual(afc[1][2].text, "Warren Moon")
        nfc = self.report["pro_bowl"][1]
        self.assertEqual(nfc[0][2].text, "Joe Montana")
        self.assertEqual(nfc[29][2].text, "Sean Landeta")


if __name__ == "__main__":
    unittest.main()
