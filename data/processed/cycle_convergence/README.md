# Cycle (periodic) convergence results

Processed inlet-pressure results demonstrating that the pulsatile simulations reach a
periodically converged state — successive cardiac cycles collapse onto one another. These
are the figures and time series underlying the paper's cycle-convergence check for the
representative case **AAA, male, 60–69, stat-10, morph-4** (parabolic inlet, corrected `U`).

## Contents

- `inlet_pressure_timeseries.csv` — area-averaged inlet pressure (Pa) vs. time, extracted
  from the solver field files over all four cardiac cycles (`t = 0 … 3.8 s`).
- `inlet_pressure_continuous.png` / `.pdf` — the full continuous pressure trace across all cycles.
- `inlet_pressure_overlaid_cycles.png` / `.pdf` — the four cycles folded onto a common phase axis to show cycle-to-cycle repeatability.
- `inlet_pressure_overlaid_zoomed.png` / `.pdf` — zoomed view of the overlaid cycles highlighting the residual difference between cycles 3 and 4.

The `overlaid_cycles` and `overlaid_zoomed` figures are the two used in the paper.

## Scripts

- `plot_inlet_pressure_convergence_parabolic.py` — generates the figures/CSV above from the
  raw OpenFOAM case (parabolic inlet, the paper case).
- `plot_inlet_pressure_convergence_plug.py` — the equivalent for the plug (flat) inlet
  boundary condition.

> **Note:** these scripts read a full OpenFOAM case directory (mesh + per-timestep field
> files) whose path is hard-coded near the top of each script (`CASE_DIR`). That raw CFD
> output is **not** part of this release (it is hundreds of GB). The scripts are included as
> a record of how the released figures and `inlet_pressure_timeseries.csv` were produced; to
> re-run them you would point `CASE_DIR` at your own OpenFOAM case. The CSV and figures here
> are the finished products and need no raw data to view.

Requires the packages in the repository-root `requirements.txt` (numpy, matplotlib).
