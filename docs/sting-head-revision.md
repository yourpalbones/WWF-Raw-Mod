# Sting native face and outfit checkpoint — v0.14

The sprite pack marker advances to `STING-NATIVE-GEAR3` at `6FF000`. Addresses,
namespaces and engine dispatch remain those of the donor-based v0.13 rebuild.
The dispatcher recognizes the four-byte STIN prefix, so versions 2 and 3 use
the same workers. The browser retains full v0.12 and v0.13 layout manifests;
loading/exporting those mods is unchanged until the user selects the rebuild.

`build_sting_shaded_heads.py` reads native Undertaker and Kid face drawings.
For the frontal head it positions Kid primary piece 1's facial anatomy two pixels
left: eye landmarks `(-1,-35), (0,-35), (2,-35)`, nose `(1,-33)`, lips `(1,-31)`.
Other views preserve their own native face planes. Paint shades use existing
palette slots 5, 8 and 13; the outfit palette is unchanged. The registrar still
matches 197 drawings. Explicit paint planes can replace native hair/neckline
colors inside reviewed heads, rather than losing features through a skin-only gate.

Exact tile hashes cannot establish anatomy by themselves. A jaw plane overlaps
the native donor neckline; propagating garment colors through its tile hash can
paint trousers. Tile fallback therefore accepts native skin/black head pixels,
and never applies to the 426 wrestler-specific lower pieces. v0.13 already had
48 white pixels in 46 lower drawings from this shared-tile effect. The revision
restores native black; the other 380 drawings remain identical.

Primary 738's original shirt rectangle ended above the waist. Reviewed row
spans now cover the exposed flank/abdomen, preserving the left foreground arm.
The Scorpion artwork and other approved outfit shapes remain unchanged.

The independent verifier decodes output descriptors/tiles, checks the native
landmarks, checks every lower drawing, and checks shirt coverage plus the bare
arm. Full cold-boot controller replays cover walk, ropes, punch, kick, the complete
Deathlock and ten giving/taking samples. All 101 editor captures match native PPU
pixels. Browser/native rebuilds match exactly, with offline export/reopen and PNG/
project roundtrips. Extracted ZIP testing also checks v0.12/v0.13 load/export and
their retained 59/101 captured previews before upgrading.

Current ROM SHA256:
`c641ae86deeaaa4d69097b65e0451fa53e8be1b11564ece07d07f6b66307f6dc`.
Private builds/captures are under `outputs/sting-head-revision/`.
Public proof: `evidence/sting-head-revision/README.md`.
This is an art candidate; likeness, rare views and exhaustive matchups remain
subject to visual review. Do not equate private ownership or pixel-exact previews
with a finished likeness.
