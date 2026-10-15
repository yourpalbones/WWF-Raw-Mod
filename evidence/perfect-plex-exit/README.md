# Perfect-Plex exit evidence

What the exit does and how it was planned: [`docs/perfect-plex-exit.md`](../../docs/perfect-plex-exit.md).
Everything here comes from controller input only, replayed from a cold boot. ROMs, captures and states stay local.

| File | What it shows |
|---|---|
| [`royal-vs-raw-undertaker.gif`](royal-vs-raw-undertaker.gif) | Royal Rumble (left) and Raw with Mr. Perfect (right, stock import v5), side by side from 30 frames before the bridge until both wrestlers have walked under control. Native screens, aligned on the first bridge frame. The caption under each panel names the phase from that game's own events. |
| [`royal-finishing-plex-no-count.gif`](royal-finishing-plex-no-count.gif) | Royal Rumble: a Perfect-Plex that takes the Undertaker to 0 health. The bridge is held for 56 frames and released, with no referee count. |
| [`editor-preview-exit.png`](editor-preview-exit.png) | The editor's paired preview (stock import v5, Undertaker, Perfect on the right) at step 12, two release steps and the final step: Perfect standing, the receiver down. |
| [`recipes/royal.json`](recipes/royal.json) | Royal: the Perfect-Plex, from the verified source match (`data/royal-perfect-source-capture.json`). This is the capture `tools/plan_perfect_plex_exit.py` plans from. |
| [`recipes/royal-recovery.json`](recipes/royal-recovery.json) | Royal: the same, extended by `tools/recovery_bot.py` until both wrestlers walk. |
| [`recipes/royal-finishing-plex.json`](recipes/royal-finishing-plex.json) | Royal: after the recovery, another Perfect-Plex that ends the opponent's health. |
| [`recipes/undertaker-attacker-right-recovery.json`](recipes/undertaker-attacker-right-recovery.json) | Raw: `undertaker-attacker-right` (Perfect on the right, as in Royal), extended by `tools/recovery_bot.py`. |
| `recovery-*.json` | `tools/check_plex_recovery.py` reports: each wrestler's depth moves the way his stick points once he is back up. |

Reproduce the Royal side with `tools/capture_royal_perfect_plex.py CORE ROYAL.sfc --recipe RECIPE --output DIR`.
Reproduce the Raw side with `tools/run_controller_recipe.py CORE BUILD.sfc RECIPE --output DIR`.
