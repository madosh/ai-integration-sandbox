"""Cross-platform task runner (stdlib-only).

Mirrors the Makefile targets so the repo runs anywhere `python` exists, even
when GNU make / uv are unavailable (e.g. stock Windows + PowerShell).

Usage:
    python tasks.py <target> [args...]

Targets:
    setup        Create a venv (if missing) and install the package + dev deps.
    run          Boot the FastAPI service (uvicorn) on :8000.
    test         Run the full pytest suite.
    lint         Ruff lint + Black format-check.
    type         mypy type-check.
    eval         Run the eval harness and write a scorecard report.
    ui           Run the dashboard dev server (npm run dev in dashboard/).
    deploy-local Provision the stack against LocalStack and run a smoke test.
    drill-katas  Run ONLY the practice kata tests (expected to fail until solved).
    mock-apis    Boot the mock partner APIs (uvicorn) on :9000.
    sandbox      Boot mock-apis + service + dashboard (all-in-one).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
IS_WINDOWS = os.name == "nt"
VENV = ROOT / ".venv"
VENV_BIN = VENV / ("Scripts" if IS_WINDOWS else "bin")


def _python() -> str:
    """Return the venv python if it exists, else the current interpreter."""
    candidate = VENV_BIN / ("python.exe" if IS_WINDOWS else "python")
    return str(candidate) if candidate.exists() else sys.executable


def _run(cmd: list[str], **kwargs: object) -> int:
    print(f"$ {' '.join(cmd)}", flush=True)
    return subprocess.call(cmd, cwd=ROOT, **kwargs)  # type: ignore[arg-type]


def setup(_: list[str]) -> int:
    if not VENV.exists():
        if _run([sys.executable, "-m", "venv", str(VENV)]) != 0:
            return 1
    py = _python()
    if _run([py, "-m", "pip", "install", "--upgrade", "pip"]) != 0:
        return 1
    return _run([py, "-m", "pip", "install", "-e", ".[dev]"])


def run(_: list[str]) -> int:
    return _run([_python(), "-m", "uvicorn", "aih.service.app:app", "--reload", "--port", "8000"])


def mock_apis(_: list[str]) -> int:
    return _run([_python(), "-m", "uvicorn", "mock_apis.app:app", "--reload", "--port", "9000"])


def test(args: list[str]) -> int:
    return _run([_python(), "-m", "pytest", *(args or [])])


def lint(_: list[str]) -> int:
    rc = _run([_python(), "-m", "ruff", "check", "src", "tests"])
    rc |= _run([_python(), "-m", "black", "--check", "src", "tests"])
    return rc


def type_check(_: list[str]) -> int:
    return _run([_python(), "-m", "mypy"])


def eval_(_: list[str]) -> int:
    return _run([_python(), "-m", "aih.evals"])


def ui(_: list[str]) -> int:
    dashboard = ROOT / "dashboard"
    npm = "npm.cmd" if IS_WINDOWS else "npm"
    if not (dashboard / "node_modules").exists():
        if subprocess.call([npm, "install"], cwd=dashboard) != 0:
            return 1
    return subprocess.call([npm, "run", "dev"], cwd=dashboard)


def deploy_local(_: list[str]) -> int:
    return _run([_python(), "-m", "deploy.smoke_test"])


def drill_katas(_: list[str]) -> int:
    return _run([_python(), "-m", "pytest", "drills/katas", "-v"])


def sandbox(args: list[str]) -> int:
    """Boot the full stack via the platform launcher script."""
    if IS_WINDOWS:
        script = ROOT / "run-sandbox.cmd"
        cmd = [str(script), *args]
        return _run(cmd)

    script = ROOT / "run-sandbox.sh"
    cmd = ["bash", str(script), *args]
    return _run(cmd)


TARGETS = {
    "setup": setup,
    "run": run,
    "mock-apis": mock_apis,
    "test": test,
    "lint": lint,
    "type": type_check,
    "eval": eval_,
    "ui": ui,
    "deploy-local": deploy_local,
    "drill-katas": drill_katas,
    "sandbox": sandbox,
}


def main(argv: list[str]) -> int:
    if not argv or argv[0] in {"-h", "--help", "help"}:
        print(__doc__)
        return 0
    target, *rest = argv
    fn = TARGETS.get(target)
    if fn is None:
        print(f"Unknown target: {target!r}\n")
        print(__doc__)
        return 2
    return fn(rest)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
