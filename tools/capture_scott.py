"""Replay Scott's slot (Razor Ramon's) from cold boot: walk, ropes, punch, kick and the Outsider's Edge (Razor's Edge).
Same as tools/capture_wrestler.py --capture razor-ramon-finisher.

    python3 tools/capture_scott.py CORE ROM --output DIR
"""
import runpy
import sys
from pathlib import Path

sys.argv += ['--capture', 'razor-ramon-finisher']
runpy.run_path(str(Path(__file__).with_name('capture_wrestler.py')), run_name='__main__')
