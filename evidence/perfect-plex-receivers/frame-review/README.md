# Perfect-Plex frame review

These are labeled crops of the three committed gameplay GIFs: Royal native,
the private Raw Undertaker prototype, and the released v0.16 with Luna. Crops
are at native 256×224 coordinates and enlarged 2× with nearest-neighbour only.
They add no new captures. Each label names the source GIF and frame index.
Regenerate with `python3 tools/review_perfect_plex_gifs.py`.

| Sheet | Shows | Gap |
| --- | --- | --- |
| [entry-side-swap](entry-side-swap.png) | Tie-up to first lift. Royal keeps Perfect on the left; Raw (prototype and v0.16) switches him to the right. | PP-1 |
| [lift-registration](lift-registration.png) | In Royal both wrestlers are visible side by side; in Raw the receiver is hidden behind Perfect. | PP-2 |
| [detached-shadow](detached-shadow.png) | The receiver's grey shadow stays at its tie-up spot while the body is lifted. | PP-3 |
| [bridge](bridge.png) | Final bridge, mirrored in Raw; the receiver body and colours differ. | PP-1, PP-6 |
| [exit](exit.png) | The receiver snaps to standing inside the attacker after the bridge. | PP-4 |

Diagnosis and fix order: [docs/perfect-plex-gaps.md](../../../docs/perfect-plex-gaps.md).

![Entry](entry-side-swap.png)
![Lift](lift-registration.png)
![Shadow](detached-shadow.png)
![Bridge](bridge.png)
![Exit](exit.png)
