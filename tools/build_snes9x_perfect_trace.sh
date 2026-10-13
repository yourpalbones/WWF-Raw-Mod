#!/usr/bin/env bash
# Read-only finisher gate tracing layered over the Royal graphics research core.
set -euo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
build_dir="${1:?Usage: build_snes9x_perfect_trace.sh BUILD_DIRECTORY}"
probe_patch="$script_dir/snes9x-perfect-gates.patch"
if git -C "$build_dir" apply --reverse --check "$probe_patch" 2>/dev/null; then
    git -C "$build_dir" apply --reverse "$probe_patch"
fi
bash "$script_dir/build_snes9x_royal_trace.sh" "$build_dir"
git -C "$build_dir" apply --check "$probe_patch"
git -C "$build_dir" apply "$probe_patch"
make -C "$build_dir/libretro" -j"${WWF_SNES9X_JOBS:-3}"
