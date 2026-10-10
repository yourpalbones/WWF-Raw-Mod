#!/usr/bin/env bash
# Build a pinned local research core. No ROM or game data is downloaded.
set -euo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
build_dir="${1:?Usage: build_snes9x_trace.sh BUILD_DIRECTORY}"
revision=fae2fea08f74180759ef540ee94259213f503480
if [[ ! -e "$build_dir" ]]; then
    mkdir -p "$build_dir"
    git -C "$build_dir" init --quiet
    git -C "$build_dir" remote add origin https://github.com/libretro/snes9x.git
    git -C "$build_dir" fetch --depth 1 origin "$revision"
    git -C "$build_dir" checkout --quiet --detach FETCH_HEAD
fi
if [[ "$(git -C "$build_dir" rev-parse HEAD)" != "$revision" ]]; then
    echo 'Build directory must use the documented Snes9x revision; choose a new directory.' >&2
    exit 1
fi
patch="$script_dir/snes9x-trace.patch"
if git -C "$build_dir" apply --reverse --check "$patch" 2>/dev/null; then
    : # Instrumentation already applied; reuse compatible object files.
else
    if [[ -n "$(git -C "$build_dir" status --porcelain)" ]]; then
        echo 'Build directory has local changes; choose a new directory to preserve them.' >&2
        exit 1
    fi
    git -C "$build_dir" apply --check "$patch"
    git -C "$build_dir" apply "$patch"
    make -C "$build_dir/libretro" clean
fi
make -C "$build_dir/libretro" -j"${WWF_SNES9X_JOBS:-3}"
echo "Core: $build_dir/libretro/snes9x_libretro.so"
