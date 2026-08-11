#!/usr/bin/env bash
# Vendor llvm-openmp for LightGBM on macOS (no Homebrew required).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEPS="$ROOT/.deps"
mkdir -p "$DEPS"
cd "$DEPS"

if [[ -f lib/libomp.dylib ]]; then
  echo "libomp already present at $DEPS/lib/libomp.dylib"
  exit 0
fi

URL="https://conda.anaconda.org/conda-forge/osx-arm64/llvm-openmp-17.0.6-hcd81f8e_0.conda"
curl -fsSL -o llvm-openmp.conda "$URL"
python3 - <<'PY'
import pathlib, zipfile, tarfile, sys
try:
    import zstandard as zstd
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "zstandard", "-q"])
    import zstandard as zstd

p = pathlib.Path("llvm-openmp.conda")
with zipfile.ZipFile(p) as z:
    info = next(n for n in z.namelist() if n.endswith(".tar.zst"))
    raw = z.read(info)
dctx = zstd.ZstdDecompressor()
data = dctx.decompress(raw)
pathlib.Path("pkg.tar").write_bytes(data)
with tarfile.open("pkg.tar") as t:
    t.extractall(".")
print("Installed libomp to .deps/lib")
PY
