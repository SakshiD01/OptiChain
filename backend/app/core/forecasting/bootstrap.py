"""Runtime environment bootstrap for forecasting dependencies.

Prophet's pip wheel ships a broken bundled CmdStan on some macOS setups;
we point cmdstanpy at a user-level CmdStan install when available.

LightGBM/XGBoost need libomp on macOS. We vendor llvm-openmp under
backend/.deps/lib (see scripts/bootstrap_native_deps.sh) and prepend it
to DYLD_LIBRARY_PATH before those libraries load.
"""

from __future__ import annotations

import os
from pathlib import Path

_BOOTSTRAPPED = False


def bootstrap_native_deps() -> None:
    global _BOOTSTRAPPED
    if _BOOTSTRAPPED:
        return

    backend_root = Path(__file__).resolve().parents[3]  # .../backend
    deps_lib = backend_root / ".deps" / "lib"
    libomp = deps_lib / "libomp.dylib"
    if deps_lib.is_dir():
        current = os.environ.get("DYLD_LIBRARY_PATH", "")
        prefix = str(deps_lib)
        if prefix not in current.split(":"):
            os.environ["DYLD_LIBRARY_PATH"] = (
                f"{prefix}:{current}" if current else prefix
            )
        current_fb = os.environ.get("DYLD_FALLBACK_LIBRARY_PATH", "")
        if prefix not in current_fb.split(":"):
            os.environ["DYLD_FALLBACK_LIBRARY_PATH"] = (
                f"{prefix}:{current_fb}" if current_fb else prefix
            )
        # SIP ignores late DYLD_* changes — preload OpenMP into the process
        if libomp.exists():
            import ctypes

            ctypes.CDLL(str(libomp), mode=ctypes.RTLD_GLOBAL)

    cmdstan = Path.home() / ".cmdstan" / "cmdstan-2.39.0"
    if cmdstan.is_dir() and "CMDSTAN" not in os.environ:
        os.environ["CMDSTAN"] = str(cmdstan)

    # Bypass Prophet's incomplete bundled CmdStan directory if present
    try:
        import prophet
        from pathlib import Path as P

        stan_model = P(prophet.__file__).parent / "stan_model"
        bundled = stan_model / "cmdstan-2.33.1"
        broken = stan_model / "cmdstan-2.33.1.broken"
        if bundled.is_dir() and not broken.exists():
            # Incomplete install (missing makefile) breaks Prophet init
            makefile = bundled / "makefile"
            if not makefile.exists():
                bundled.rename(broken)
    except Exception:
        pass

    _BOOTSTRAPPED = True
