"""Raw's pose profiles (composite drawings) as the game references them.

A profile is a list of [part ID (u16; bit 15 = secondary), dx (s8), dy (s8)] ended by 0xFFFF; part IDs are byte
offsets into the slot's frame directory (index * 3), and 0x8024 is the shadow. Animation streams reference
profiles with 7-byte entries that start with the bank byte 0xC8 and a 16-bit pointer, so the profiles are the
pointers that follow a 0xC8 byte and parse as a plausible profile. 973 of the 1,036 found are chained end to
start, which is how the game lays them out.

    from raw_profiles import profiles, entries
    for address in profiles(rom): entries(rom, address)
"""
from functools import lru_cache

BANK = 0xC8
SHADOW = 0x8024


def _s8(v):
    return v - 256 if v > 127 else v


def _valid(part):
    if part & 0x8000:
        j = part & 0x7FFF
        return j % 3 == 0 and j // 3 < 722
    return part % 3 == 0 and part // 3 < 1014


def entries(rom, address, limit=8):
    """[(part_id, dx, dy), ...] for the profile at a CPU or file address in bank $C8, or None if implausible."""
    a = (address & 0xFFFF) | 0x080000
    out = []
    while a + 2 <= len(rom):
        part = rom[a] | rom[a + 1] << 8
        if part == 0xFFFF:
            return out or None
        if not _valid(part) or len(out) >= limit:
            return None
        dx, dy = _s8(rom[a + 2]), _s8(rom[a + 3])
        if abs(dx) > 96 or abs(dy) > 110:
            return None
        out.append((part, dx, dy))
        a += 4
    return None


@lru_cache(maxsize=4)
def _scan(rom):
    found = set()
    for a in range(len(rom) - 3):
        if rom[a] == BANK:
            p = rom[a + 1] | rom[a + 2] << 8
            if p not in found and entries(rom, p):
                found.add(p)
    return tuple(sorted(BANK << 16 | p for p in found))


def profiles(rom):
    """CPU addresses ($C8:xxxx) of every profile an animation stream references."""
    return list(_scan(bytes(rom)))
