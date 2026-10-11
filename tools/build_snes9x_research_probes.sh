#!/usr/bin/env bash
# Optional read-only APU RAM, score-read and roster-bound probes.
set -euo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
build_dir="${1:?Usage: build_snes9x_research_probes.sh BUILD_DIRECTORY}"
revision=fae2fea08f74180759ef540ee94259213f503480
if [[ -d "$build_dir/.git" && "$(git -C "$build_dir" rev-parse HEAD)" != "$revision" ]]; then
    echo "Choose a build directory at the documented Snes9x revision." >&2
    exit 1
fi
patch="$script_dir/snes9x-research-probes.patch"
if ! git -C "$build_dir" apply --reverse --check "$patch" 2>/dev/null; then
    bash "$script_dir/build_snes9x_profile_trace.sh" "$build_dir"
    git -C "$build_dir" apply --check "$patch"
    git -C "$build_dir" apply "$patch"
    touch "$build_dir/apu/bapu/smp/smp.cpp"
fi
make -C "$build_dir/libretro" -j"${WWF_SNES9X_JOBS:-3}"
