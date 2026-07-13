"""
patch_visualization_metrics.py
================================
Patches geometry_metrics.json and metrics_summary.txt in every case folder
under ofCases/submission_v2/v2_b/{parabolic,plug}/ with the corrected values
from the postProcess xlsx files.

What is updated
---------------
geometry_metrics.json  →  base.shape.{volume, surface_area, sphericity,
                           convexity, average_radius, surface_volume_ratio,
                           hull_volume}
                           base.centerline.{centerline_length, tortuosity}
metrics_summary.txt    →  "Base Geometry:" block only

What is NOT updated
-------------------
* "Morphed Geometry" block in metrics_summary.txt  — requires re-running the
  morphing pipeline; corrected values are not available in the xlsx.
* relative_changes in geometry_metrics.json        — depend on morphed values.
* base.shape.{roundness, hull_surface_area, straight_length}  — not in xlsx.

Run from the Method_4 root:
    python patch_visualization_metrics.py
"""

import json
import re
import sys
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent          # Method_4/
OFCASES_V2B  = ROOT / "data/output/ofCases/submission_v2/v2_b"
POSTPROC_V2B = ROOT / "data/output/postProcess/correlation/submission_v2/v2_b"

XLSX = {
    "parabolic": POSTPROC_V2B / "parabolic/aaa_parameters_metrics_parabolic.xlsx",
    "plug":      POSTPROC_V2B / "plug/aaa_parameters_metrics_plug.xlsx",
}

# Columns we pull from the xlsx (must exist in both sheets)
SHAPE_COLS      = ["volume", "surface_area", "sphericity", "convexity", "average_radius"]
CENTERLINE_COLS = ["centerline_length", "tortuosity"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def strip_postprocessing(case_id: str) -> str:
    return re.sub(r"_postProcessing$", "", case_id, flags=re.IGNORECASE)


def case_folder_name(profile: str, case_id_stripped: str) -> str:
    """
    The plug xlsx omits 'plug' from case_id, but the actual folder has it.
    e.g. AAA_F_70-79_stat_3_prob_distribution_morph_8
      →  AAA_F_70-79_stat_3_prob_distribution_plug_morph_8
    """
    if profile == "plug" and "_plug_" not in case_id_stripped:
        return re.sub(r"_morph_", "_plug_morph_", case_id_stripped, count=1)
    return case_id_stripped


def find_json_for_case(profile: str, case_name: str) -> Path | None:
    """Glob for geometry_metrics.json inside the correct case folder."""
    matches = list((OFCASES_V2B / profile).rglob(f"{case_name}/visualizations/geometry_metrics.json"))
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        print(f"  [WARN] Multiple matches for {case_name}: {matches}")
        return matches[0]
    return None


def patch_json(json_path: Path, row: pd.Series, dry_run: bool = False) -> bool:
    with open(json_path) as f:
        data = json.load(f)

    base = data.setdefault("base", {})
    shape = base.setdefault("shape", {})
    centerline = base.setdefault("centerline", {})

    # Update shape metrics
    for col in SHAPE_COLS:
        shape[col] = float(row[col])

    # Recompute derived fields from new values
    if shape["volume"] > 0:
        shape["surface_volume_ratio"] = shape["surface_area"] / shape["volume"]
    if shape["convexity"] > 0:
        shape["hull_volume"] = shape["volume"] / shape["convexity"]

    # Update centerline metrics
    for col in CENTERLINE_COLS:
        centerline[col] = float(row[col])

    if not dry_run:
        with open(json_path, "w") as f:
            json.dump(data, f, indent=4)
    return True


def patch_txt(txt_path: Path, row: pd.Series, dry_run: bool = False) -> bool:
    """Replace only the 'Base Geometry' block in metrics_summary.txt."""
    text = txt_path.read_text()

    # New base block content
    new_base_block = (
        "Base Geometry:\n"
        "-------------\n"
        f"Volume: {row['volume']:.1f} mm³\n"
        f"Surface Area: {row['surface_area']:.1f} mm²\n"
        f"Centerline Length: {row['centerline_length']:.1f} mm\n"
        f"Tortuosity: {row['tortuosity']:.3f}\n"
        f"Sphericity: {row['sphericity']:.3f}\n"
        f"Convexity: {row['convexity']:.3f}\n"
        f"Average Radius: {row['average_radius']:.1f} mm\n"
    )

    # Replace the block between "Base Geometry:" and the next section header
    pattern = r"Base Geometry:\n-+\n.*?(?=\n\w|\Z)"
    new_text, n = re.subn(pattern, new_base_block.rstrip(), text, flags=re.DOTALL)

    if n == 0:
        print(f"  [WARN] Could not find 'Base Geometry' block in {txt_path}")
        return False

    if not dry_run:
        txt_path.write_text(new_text)
    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(dry_run: bool = False):
    if dry_run:
        print("=== DRY RUN — no files will be written ===\n")

    total_ok = total_skip = total_err = 0

    for profile, xlsx_path in XLSX.items():
        print(f"\n{'='*60}")
        print(f"Profile: {profile}  —  {xlsx_path.name}")
        print(f"{'='*60}")

        if not xlsx_path.exists():
            print(f"  [ERROR] xlsx not found: {xlsx_path}")
            continue

        df = pd.read_excel(xlsx_path)
        print(f"  Loaded {len(df)} rows\n")

        for _, row in df.iterrows():
            raw_id    = str(row["case_id"])
            case_name = case_folder_name(profile, strip_postprocessing(raw_id))

            json_path = find_json_for_case(profile, case_name)
            if json_path is None:
                print(f"  [SKIP] JSON not found: {case_name}")
                total_skip += 1
                continue

            txt_path = json_path.parent / "metrics_summary.txt"

            try:
                j_ok = patch_json(json_path, row, dry_run=dry_run)
                t_ok = patch_txt(txt_path, row, dry_run=dry_run) if txt_path.exists() else False

                status = []
                if j_ok: status.append("json")
                if t_ok: status.append("txt")
                print(f"  [OK]  {case_name}  ({', '.join(status) or 'nothing updated'})")
                total_ok += 1
            except Exception as exc:
                print(f"  [ERROR] {case_name}: {exc}")
                total_err += 1

    print(f"\n{'='*60}")
    print(f"Done.  OK={total_ok}  Skipped={total_skip}  Errors={total_err}")
    if dry_run:
        print("(dry run — no files were changed)")


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv or "-n" in sys.argv
    run(dry_run=dry)
