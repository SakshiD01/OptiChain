"""Shared pytest bootstrap — native deps (libomp, CmdStan) before imports."""

from app.core.forecasting.bootstrap import bootstrap_native_deps

bootstrap_native_deps()
