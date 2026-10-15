# Mr. Perfect's stomach (seams between his pieces)

What changed and why: [`docs/complete-wrestler-art.md`](../../docs/complete-wrestler-art.md), section
"Mr. Perfect's stomach". The placements come from `tools/close_perfect_seams.py`
([`data/perfect-seam-report.json`](../../data/perfect-seam-report.json)).

| File | What it shows |
|---|---|
| [`standing-before-after.png`](standing-before-after.png) | Native screens from the same frame of the same cold-boot replay (Syxx match, gear reference mod, frame 19824, Perfect standing after the Perfect-Plex). Left: v5, where the background shows through a 3 px band across his stomach. Right: v6, with his singlet solid. Nearest-neighbour enlargement only. |

Reproduce: replay the recipe with `tools/run_controller_recipe.py CORE BUILD.sfc RECIPE --output DIR` on each
build; the screens are `DIR/frame-NNNNNN.png`. ROMs and captures stay local.
