"""
run_pipeline.py — one-command driver for the pre-CFD stages.

Runs, in order:
  1. main.py                                     generate the synthetic population + OpenFOAM cases
  2. analysis/data_bound_with_morphed_data_manual.py   convex-hull selection -> universal-interior report
  3. analysis/zip_it.py                          package the interior cases into a CFD-ready zip

All three read the target demographic from config.py, so configure the run once
in config.py and then simply:

    python run_pipeline.py

Each step is also runnable on its own; this script only chains them. The CFD
solve itself (OpenFOAM) is a separate, external step and is not run here.
"""

import subprocess
import sys
from pathlib import Path

# Repo root = this file's directory. Run every step from here so the scripts'
# relative paths (data/input/..., data/output/...) resolve correctly.
ROOT = Path(__file__).resolve().parent

STEPS = [
    ("Generate population + OpenFOAM cases", ["main.py"]),
    ("Convex-hull selection (universal interior set)", ["analysis/data_bound_with_morphed_data_manual.py"]),
    ("Package interior cases for CFD", ["analysis/zip_it.py"]),
]


def main() -> int:
    for i, (label, script_args) in enumerate(STEPS, start=1):
        print(f"\n{'=' * 70}\n[{i}/{len(STEPS)}] {label}\n{'=' * 70}", flush=True)
        # Use the current interpreter (respects the active conda/venv env).
        result = subprocess.run([sys.executable, *script_args], cwd=ROOT)
        if result.returncode != 0:
            print(
                f"\nStep {i} ({label}) failed with exit code {result.returncode}. "
                f"Stopping.",
                file=sys.stderr,
            )
            return result.returncode

    bar = "=" * 70
    print(
        f"\n{bar}\n"
        "Pipeline complete. The interior-case archive "
        "(<gender>_<age>_<suffix>_interior_cases.zip) is ready under "
        "data/output/ofCases/.\n"
        "Next: run the OpenFOAM CFD simulations on the interior cases.\n"
        f"{bar}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
