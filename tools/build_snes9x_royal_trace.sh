#!/usr/bin/env bash
# Royal Rumble source graphics: read-only CPU and decompressed-tile captures.
set -euo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
build_dir="${1:?Usage: build_snes9x_royal_trace.sh BUILD_DIRECTORY}"
patch="$script_dir/snes9x-royal-trace.patch"
# Temporarily remove this layer so the underlying probe checks remain exact.
if git -C "$build_dir" apply --reverse --check "$patch" 2>/dev/null; then
    git -C "$build_dir" apply --reverse "$patch"
fi
bash "$script_dir/build_snes9x_research_probes.sh" "$build_dir"
git -C "$build_dir" apply --check "$patch"
git -C "$build_dir" apply "$patch"
make -C "$build_dir/libretro" -j"${WWF_SNES9X_JOBS:-3}"
