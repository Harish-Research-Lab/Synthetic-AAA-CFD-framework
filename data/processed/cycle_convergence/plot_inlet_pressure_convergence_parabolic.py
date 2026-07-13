"""
Inlet pressure convergence diagnostic.

Extracts area-averaged (cell-mean) pressure at the inlet patch across all
saved time steps from an OpenFOAM pisoFoam run and produces two figures:

  Figure 1 – Continuous waveform: full 4-cycle time series with vertical
             dashed lines at cycle boundaries and cycle labels.

  Figure 2 – Overlaid cycles: all 4 cycles folded onto the same phase axis
             so cycle-to-cycle drift is immediately visible.

The max relative variation between cycles 3 and 4 is computed and printed
to support a quantitative statement in the reviewer response.

Usage
-----
  python plot_inlet_pressure_convergence.py

All paths are hard-coded; edit the constants below if needed.
"""

import os
import re
import subprocess
import numpy as np
import matplotlib
matplotlib.use("Agg")   # headless backend — no display required on HPC
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

# ---------------------------------------------------------------------------
# Publication style  (matches scientific_plot_scaler / thesis template)
# ---------------------------------------------------------------------------
plt.style.use("classic")
plt.rcParams.update({
    "font.family":        "serif",
    "font.serif":         ["Times New Roman", "Times", "DejaVu Serif"],
    "font.size":          11,
    "axes.labelsize":     11,
    "axes.titlesize":     11,
    "legend.fontsize":    9.9,
    "xtick.labelsize":    10,
    "ytick.labelsize":    10,
    "lines.linewidth":    2.0,
    "axes.linewidth":     0.8,
    "xtick.direction":    "in",
    "ytick.direction":    "in",
    "xtick.minor.visible": True,
    "ytick.minor.visible": True,
    "xtick.top":          True,
    "ytick.right":        True,
    "figure.dpi":         300,
    "savefig.dpi":        300,
})

# ---------------------------------------------------------------------------
# Paths and simulation parameters
# ---------------------------------------------------------------------------

CASE_DIR = (
    "/mnt/iusers01/mace01/q21422vn/scratch/ofGenCase/parabolic/paper1/"
    "AAA_M_60-69_stat_10_prob_distribution_parabolic_morph_4_Umod"
)
OUTPUT_DIR = (
    "/mnt/iusers01/mace01/q21422vn/myPhD/Vijay-Nandurdikar-PhD/Aorta/"
    "ofCaseGen/Method_4/data/output/postProcess/cycle"
)

CYCLE_PERIOD   = 0.95        # seconds
N_CYCLES       = 4
RHO            = 1060.0      # kg/m³  (blood density — converts kinematic p to Pa)
T_START_PLOT   = 0.0         # exclude t=0 IC if desired (set to 0.05 to skip t=0)

# Inlet patch info (from constant/polyMesh/boundary)
INLET_START_FACE = 3_867_315
INLET_N_FACES    = 1_544

# Pressure internalField in p files starts at line 22 (1-indexed),
# immediately after the '(' on line 21.  Count of cells on line 20.
P_DATA_SKIP_ROWS = 21        # lines to skip before data
P_N_CELLS        = 1_286_599

# Owner file: data starts at line 21 (after count on line 19, '(' on line 20)
OWNER_DATA_LINE_OFFSET = 20  # 0-indexed line of first owner value

# ---------------------------------------------------------------------------
# Step 1: read inlet face owner cells from constant/polyMesh/owner
# ---------------------------------------------------------------------------

def read_inlet_owner_cells(case_dir, start_face, n_faces, data_offset):
    """Return 1-D integer array of owner cell indices for inlet patch faces."""
    owner_file = os.path.join(case_dir, "constant", "polyMesh", "owner")

    # data_offset is the 0-indexed line of the first face entry (face index 0).
    # Face indices start_face .. start_face+n_faces-1 are at 1-indexed lines:
    first_line = data_offset + start_face + 1          # 1-indexed
    last_line  = data_offset + start_face + n_faces    # 1-indexed (inclusive)

    result = subprocess.run(
        ["sed", "-n", f"{first_line},{last_line}p", owner_file],
        capture_output=True, text=True, check=True,
    )
    cells = np.fromstring(result.stdout, dtype=np.int64, sep="\n")
    assert len(cells) == n_faces, (
        f"Expected {n_faces} owner cells, got {len(cells)}"
    )
    return cells


# ---------------------------------------------------------------------------
# Step 2: parse a single pressure field file
# ---------------------------------------------------------------------------

def read_internal_pressure(p_file, skip_rows, n_cells):
    """Return internalField as a float64 array of length n_cells."""
    with open(p_file, "r") as fh:
        content = fh.read()

    # Handle uniform internalField (e.g. initial condition: "internalField uniform 0;")
    uniform_match = re.search(r"internalField\s+uniform\s+([\d\.\-eE+]+)\s*;", content)
    if uniform_match:
        return np.full(n_cells, float(uniform_match.group(1)), dtype=np.float64)

    # Locate nonuniform internalField block
    match = re.search(r"internalField\s+nonuniform\s+List<scalar>\s+\d+\s+\(", content)
    if match is None:
        raise ValueError(f"internalField not found in {p_file}")
    data_start = match.end()   # character index right after '('

    # End of data is the matching ')'
    data_end = content.index("\n)", data_start)

    data = np.fromstring(content[data_start:data_end], dtype=np.float64, sep="\n")
    if len(data) != n_cells:
        raise ValueError(
            f"{p_file}: expected {n_cells} values, got {len(data)}"
        )
    return data


# ---------------------------------------------------------------------------
# Step 3: collect time series
# ---------------------------------------------------------------------------

def collect_inlet_pressure(case_dir, inlet_cells, rho,
                            p_data_skip, n_cells, t_start=0.0):
    """
    Walk all numeric time directories in case_dir in chronological order,
    read pressure, extract inlet cell values, return (times, mean_Pa arrays).
    """
    time_dirs = []
    for entry in os.scandir(case_dir):
        if not entry.is_dir():
            continue
        try:
            t = float(entry.name)
        except ValueError:
            continue
        if t < t_start:
            continue
        p_file = os.path.join(entry.path, "p")
        if os.path.isfile(p_file):
            time_dirs.append((t, p_file))

    time_dirs.sort(key=lambda x: x[0])
    n_steps = len(time_dirs)
    print(f"Found {n_steps} time directories with pressure data.")

    times        = np.empty(n_steps)
    inlet_p_mean = np.empty(n_steps)

    for i, (t, p_file) in enumerate(time_dirs):
        p_internal = read_internal_pressure(p_file, p_data_skip, n_cells)
        inlet_vals = p_internal[inlet_cells]
        inlet_p_mean[i] = inlet_vals.mean() * rho    # Pa
        times[i] = t
        if (i + 1) % 10 == 0 or i == n_steps - 1:
            print(f"  Processed {i+1}/{n_steps}  (t={t:.2f} s, "
                  f"p_inlet={inlet_p_mean[i]:.1f} Pa)")

    return times, inlet_p_mean


# ---------------------------------------------------------------------------
# Step 4: plotting helpers
# ---------------------------------------------------------------------------

def cycle_index(t, period):
    """Return 1-based cycle number for time t (cycles start at t=0)."""
    return int(t / period) + 1  # 1-based


def split_into_cycles(times, pressures, period, n_cycles):
    """
    Split (times, pressures) into a list of (phase, pressure) arrays,
    one per cycle.  Phase = time within cycle (0 to period).
    """
    cycles = []
    for c in range(n_cycles):
        t0 = c * period
        t1 = (c + 1) * period
        mask = (times >= t0 - 1e-9) & (times < t1 + 1e-9)
        phase = (times[mask] - t0)
        cycles.append((phase, pressures[mask]))
    return cycles


# ---------------------------------------------------------------------------
# Step 5: main
# ---------------------------------------------------------------------------

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("Reading inlet owner cells …")
    inlet_cells = read_inlet_owner_cells(
        CASE_DIR, INLET_START_FACE, INLET_N_FACES, OWNER_DATA_LINE_OFFSET
    )
    print(f"  {len(inlet_cells)} inlet cells identified.")

    print("\nCollecting inlet pressure time series …")
    times, p_inlet = collect_inlet_pressure(
        CASE_DIR, inlet_cells, RHO,
        P_DATA_SKIP_ROWS, P_N_CELLS, t_start=T_START_PLOT
    )

    # ---- quantitative cycle-to-cycle variation ----
    cycles = split_into_cycles(times, p_inlet, CYCLE_PERIOD, N_CYCLES)

    # Interpolate cycle 3 and 4 onto cycle 4's phase grid for comparison
    phase3, p3 = cycles[2]
    phase4, p4 = cycles[3]
    p3_on_4 = np.interp(phase4, phase3, p3)
    delta = np.abs(p4 - p3_on_4)
    mean_range = 0.5 * (p3.max() - p3.min() + p4.max() - p4.min())
    max_var_abs = delta.max()
    max_var_pct = 100.0 * max_var_abs / mean_range if mean_range > 0 else np.nan

    print(f"\nCycle-to-cycle variation (cycle 3 vs 4):")
    print(f"  Max absolute difference : {max_var_abs:.2f} Pa")
    print(f"  Max relative difference : {max_var_pct:.2f} %  "
          f"(relative to mean waveform amplitude)")

    # Distinct, colorblind-friendly palette — each cycle clearly different
    # Cycle 1: light gray  (faint — first transient, least important)
    # Cycle 2: steel blue  (transitional)
    # Cycle 3: orange      (nearly converged)
    # Cycle 4: dark red    (converged — most prominent)
    cycle_colors = ["#aaaaaa", "#4393c3", "#d95f02", "#b2182b"]
    cycle_lw     = [1.2,       1.5,       1.8,       2.2      ]
    cycle_ls     = ["--",      "-.",       ":",       "-"      ]
    cycle_alpha  = [0.7,       0.8,       0.9,       1.0      ]

    # =====================================================================
    # Figure 1: Continuous time series
    # =====================================================================
    fig1, ax1 = plt.subplots(figsize=(5.0, 4.2))

    ax1.plot(times, p_inlet, color="#2166ac", linewidth=1.6)

    for c in range(N_CYCLES):
        ax1.axvline(c * CYCLE_PERIOD, color="#555555", linestyle="--",
                    linewidth=0.7, alpha=0.6)
    ax1.axvline(N_CYCLES * CYCLE_PERIOD, color="#555555", linestyle="--",
                linewidth=0.7, alpha=0.6)

    ax1.set_xlabel("Time (s)")
    ax1.set_ylabel("Area-averaged inlet pressure (Pa)")
    ax1.xaxis.set_minor_locator(mticker.AutoMinorLocator())
    ax1.yaxis.set_minor_locator(mticker.AutoMinorLocator())
    ax1.set_xlim(times[0], times[-1])
    ax1.grid(True, which="major", linestyle=":", alpha=0.35, color="#999999")

    # Cycle labels just above the axes
    for c in range(N_CYCLES):
        t_mid = (c + 0.5) * CYCLE_PERIOD
        ax1.text(t_mid, 1.02, f"Cycle {c + 1}",
                 ha="center", va="bottom", fontsize=9,
                 color=cycle_colors[c] if cycle_colors[c] != "#aaaaaa" else "#666666",
                 transform=ax1.get_xaxis_transform())

    fig1.tight_layout(rect=[0, 0, 1, 0.96])
    out1 = os.path.join(OUTPUT_DIR, "inlet_pressure_continuous.pdf")
    fig1.savefig(out1, bbox_inches="tight")
    fig1.savefig(out1.replace(".pdf", ".png"), bbox_inches="tight")
    print(f"\nFigure 1 saved → {out1}")

    ZOOM_LO, ZOOM_HI = 0.20, 0.60   # phase range with most visible deviation

    def _plot_overlaid(ax, xlim, show_annotation=False):
        """Plot all four cycles onto ax; optionally annotate variation."""
        for c, (phase, p_c) in enumerate(cycles):
            ax.plot(phase, p_c,
                    color=cycle_colors[c],
                    linestyle=cycle_ls[c],
                    linewidth=cycle_lw[c],
                    alpha=cycle_alpha[c],
                    label=f"Cycle {c + 1}")
        ax.set_xlim(*xlim)
        ax.xaxis.set_minor_locator(mticker.AutoMinorLocator())
        ax.yaxis.set_minor_locator(mticker.AutoMinorLocator())
        ax.grid(True, which="major", linestyle=":", alpha=0.35, color="#999999")
        ax.legend(loc="upper right", framealpha=0.95, edgecolor="#cccccc")

    # =====================================================================
    # Figure 2: Full overlaid cycles
    # =====================================================================
    fig2, ax2 = plt.subplots(figsize=(5.0, 4.2))
    _plot_overlaid(ax2, (0, CYCLE_PERIOD), show_annotation=True)
    ax2.set_xlabel("Phase within cardiac cycle (s)")
    ax2.set_ylabel("Area-averaged inlet pressure (Pa)")
    fig2.tight_layout()
    out2 = os.path.join(OUTPUT_DIR, "inlet_pressure_overlaid_cycles.pdf")
    fig2.savefig(out2, bbox_inches="tight")
    fig2.savefig(out2.replace(".pdf", ".png"), bbox_inches="tight")
    print(f"\nFigure 2 saved → {out2}")

    # =====================================================================
    # Figure 3: Zoomed phase 0.20–0.60 s
    # =====================================================================
    # y-limits: full span of all cycle data in the zoom window + 10 % margin
    all_y_zoom = np.concatenate([
        p_c[(phase >= ZOOM_LO) & (phase <= ZOOM_HI)]
        for phase, p_c in cycles
    ])
    y_margin = 0.10 * (all_y_zoom.max() - all_y_zoom.min())

    fig3, ax3 = plt.subplots(figsize=(5.0, 4.2))
    _plot_overlaid(ax3, (ZOOM_LO, ZOOM_HI), show_annotation=False)
    ax3.set_ylim(all_y_zoom.min() - y_margin, all_y_zoom.max() + y_margin)
    ax3.set_xlabel("Phase within cardiac cycle (s)")
    ax3.set_ylabel("Area-averaged inlet pressure (Pa)")
    # ax3.set_title(f"Zoomed view: phase {ZOOM_LO}–{ZOOM_HI} s")
    fig3.tight_layout()
    out3 = os.path.join(OUTPUT_DIR, "inlet_pressure_overlaid_zoomed.pdf")
    fig3.savefig(out3, bbox_inches="tight")
    fig3.savefig(out3.replace(".pdf", ".png"), bbox_inches="tight")
    print(f"Figure 3 saved → {out3}")

    # Save numeric data
    np_out = os.path.join(OUTPUT_DIR, "inlet_pressure_timeseries.csv")
    np.savetxt(
        np_out,
        np.column_stack([times, p_inlet]),
        delimiter=",",
        header="time_s,inlet_p_Pa",
        comments="",
    )
    print(f"Numeric data saved → {np_out}")


if __name__ == "__main__":
    main()
