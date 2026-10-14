#!/usr/bin/env bash
# Add read-only Hogan root tracing to the reproducible Perfect observation core.
set -euo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
build_dir="${1:?Usage: build_snes9x_hogan_trace.sh BUILD_DIRECTORY}"
probe_patch="$script_dir/snes9x-hogan-roots.patch"
if git -C "$build_dir" apply --reverse --check "$probe_patch" 2>/dev/null; then
    git -C "$build_dir" apply --reverse "$probe_patch"
fi
bash "$script_dir/build_snes9x_perfect_trace.sh" "$build_dir"
git -C "$build_dir" apply --check "$probe_patch"
git -C "$build_dir" apply "$probe_patch"
make -C "$build_dir/libretro" -j"${WWF_SNES9X_JOBS:-3}"
