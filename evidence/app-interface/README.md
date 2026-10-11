# WrestleEdit app interface

These are Chromium captures of the standalone browser app with the original USA ROM loaded locally. `sprites.png` follows an edited pose PNG upload; `profile.png` shows the portrait and bio tab. No ROM is distributed.

`verification.json` records the app workflow check: unchanged PNG imports for all 12 wrestlers preserve palette indices, an edited PNG updates a source tile, invalid dimensions/outline changes leave edits intact, tab switching preserves changes, the downloaded playable ROM has the native mirrored checksum, and the mobile layout avoids horizontal overflow.

Run `python3 tools/verify_app.py '/path/to/WWF Raw (USA).sfc'` to reproduce. The separate selection verifier also compares the downloaded 4 MiB ROM byte for byte with independently applied IPS output, covering all 12 portrait and bio edits. Existing roster checks compare 102 previews and roundtrip 2,174 source tiles.

This is browser/export proof. Gameplay proof for the underlying gear and selection patch formats is documented in the neighboring evidence folders; this interface change did not add animation coverage.
