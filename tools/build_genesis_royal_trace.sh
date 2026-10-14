#!/usr/bin/env bash
set -euo pipefail
task_root="$(cd "$(dirname "$0")/.." && pwd)"
task_build="${1:?Usage: build_genesis_royal_trace.sh BUILD_DIR}"
task_revision=393f70cd64c7334564c19a424c383f53986c13f4
if [[ ! -d "$task_build/.git" ]]; then
  git clone https://github.com/libretro/Genesis-Plus-GX.git "$task_build"
  git -C "$task_build" checkout "$task_revision"
fi
[[ "$(git -C "$task_build" rev-parse HEAD)" == "$task_revision" ]] || {
  echo 'Wrong research-core revision; use a fresh build directory.' >&2
  exit 1
}
if ! git -C "$task_build" apply --reverse --check "$task_root/tools/genesis-royal-observation.patch" 2>/dev/null; then
  git -C "$task_build" apply --check "$task_root/tools/genesis-royal-observation.patch"
  git -C "$task_build" apply "$task_root/tools/genesis-royal-observation.patch"
fi
make -C "$task_build" -f Makefile.libretro -j"${WWF_BUILD_JOBS:-4}"
test -s "$task_build/genesis_plus_gx_libretro.so"
