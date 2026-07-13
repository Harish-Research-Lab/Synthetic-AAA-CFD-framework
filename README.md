# Synthetic Aorta CFD Framework

A framework for generating a **synthetic virtual population** of Abdominal Aortic Aneurysm (AAA) geometries, setting them up as **OpenFOAM** computational fluid dynamics (CFD) cases, and extracting **hemodynamic biomarkers and geometric descriptors** from the results.

This is the public code release accompanying:

> V. Nandurdikar *et al.*, *"Virtual Population to Re-assess AAA Risk Using Neck Geometry and Shape Compactness Alongside Maximum Diameter"*, **Royal Society Open Science** (2026).

## Pipeline overview

The workflow follows the two-phase design described in the paper (Algorithm 1): a **statistical modelling** phase that learns the anatomy of the source cohort, and a **generation** phase that produces and screens synthetic geometries before CFD. In practice it runs as five stages, each with its own script(s):

0. **Statistical modelling** — from the patient measurements (`data/input/aaa_data.xlsx`), fit per-parameter probability distributions (`fit_distributions.py`) and build the patient-data convex hulls over diameter pairs (`convex_hull_creator.py`). These produce two JSON files that everything downstream consumes.
1. **Synthetic case generation** — `main.py` samples target diameters from the fitted distributions, builds a parametric AAA surface, applies spherical morphing for anatomical diversity, validates each geometry against **per-parameter distributions and geometric constraints**, and writes a ready-to-run OpenFOAM case per geometry.
2. **Population-bounds (convex-hull) selection** — `data_bound_with_morphed_data_manual.py` tests the *generated* population against the convex hulls and extracts the **universal interior set**: the geometries that fall inside the patient-data hull for **all** diameter pairs simultaneously. This is the joint-plausibility filter that selects which cases proceed to CFD (in the paper, 400 generated → 182 selected).
3. **CFD simulation** — run the selected OpenFOAM cases (locally or on HPC) to solve pulsatile blood flow.
4. **Biomarker / descriptor extraction** — post-process the CFD results with ParaView to extract wall shear stress (WSS), time-averaged WSS (TAWSS), oscillatory shear index (OSI) and related biomarkers, alongside geometric descriptors, then run the correlation/figure scripts.

> **Important — where the convex-hull check happens.** The morph validation *inside* `main.py` (Stage 1) is a marginal check: each diameter is tested independently against its own fitted distribution and allowed range. The **joint** convex-hull plausibility test (the "universal interior set") is a **separate downstream step** (Stage 2), matching §2(b)(v) *population bounds analysis* in the paper. Running `main.py` alone does **not** apply the hull filter.

## End-to-end run order

Stages 1–2 (and the interior-case packaging) all read the target demographic from `config.py`, so you can run them as one command:

```bash
python run_pipeline.py    # main.py -> hull selection -> interior-case zip
```

`run_pipeline.py` is a thin orchestrator that runs the three pre-CFD steps in order and stops if any fails; each step is still runnable on its own (below). It does **not** run the CFD solve (Stage 3), which is external. The individual steps:

| Step | Command | Reads | Writes |
|---|---|---|---|
| 0a. Fit distributions | `python analysis/fit_distributions.py` | `data/input/aaa_data.xlsx` | `data/processed/fitted_distributions.json` |
| 0b. Build convex hulls | `python analysis/convex_hull_creator.py` | `data/input/aaa_data.xlsx` | `data/processed/convex_hull_metadata.json` |
| 1. Generate population + cases | `python main.py` | `fitted_distributions.json`, `data/input/{U,shm}`, base case | `data/output/ofCases/…`, `data/input/geometry/…` |
| 2. Universal-interior selection | `python analysis/data_bound_with_morphed_data_manual.py` | `data/output/ofCases/…`, `convex_hull_metadata.json` | `data/processed/bound_plots/…` (+ interior reports) |
| 2b. Package interior cases | `python analysis/zip_it.py` | interior report, `data/output/ofCases/…` | `…_interior_cases.zip`, `…_all_cases.zip` |
| 3. CFD | `blockMesh` → `snappyHexMesh` → solve (per case) | selected `ofCases/…` | CFD fields in each case |
| 4. Post-process + figures | `pvpython` scripts, then `analysis/` + `data/processed/*/` scripts | CFD results, xlsx/JSON | biomarker tables, figures |

> The two JSON files from Stage 0 are **already included** in `data/processed/`, so you can run `main.py` immediately. Re-run steps 0a/0b only if you change `aaa_data.xlsx`, the demographic stratification, or the outlier list.

> **Run analysis scripts from the repository root, in script-file form** (`python analysis/<script>.py`), as shown above — **not** `python -m analysis.<script>`. Several scripts use sibling imports (e.g. `from data_bound_with_patient_data import …`) that only resolve when the script's own directory is on the path, and all of them use paths relative to the repo root.

## Repository structure

```
synthetic-aorta-cfd-framework/
├── run_pipeline.py             # One-command driver: generation -> selection -> zip
├── main.py                     # Entry point: generation + OpenFOAM case setup
├── config.py                   # Configuration (demographics, morphing, vessel settings)
├── requirements.txt            # Python dependencies
├── src/
│   ├── vesselGen/              # Parametric vessel geometry generation
│   ├── vesselMorph/            # Spherical morphing + geometry validation (marginal)
│   ├── vesselStats/            # Statistical parameter sampling
│   ├── ofCaseGen/              # OpenFOAM case generation (mesh, BCs, U file)
│   └── visualization/          # Geometry / velocity visualization
├── analysis/                   # Distribution fitting, convex-hull bounds & interior
│                               #   selection, correlation/distribution figure scripts
└── data/
    ├── input/
    │   ├── U/                  # Inlet velocity waveform + U boundary-condition templates
    │   ├── shm/                # snappyHexMesh point definitions
    │   ├── of_base_case/       # OpenFOAM base case template + ParaView extraction scripts
    │   └── aaa_data.xlsx       # Patient-derived measurements (statistical basis)
    └── processed/              # Fitted distributions + convex-hull metadata (JSON),
                                #   plus figure-reproduction data (see data/processed/README.md)
```

> **Note on data.** Generated geometries (`data/input/geometry/`) and CFD results (`data/output/`) are **not** included in this repository because of their size; they are produced by running the pipeline.

## Installation

Requires **Python 3.11** and, for Stages 3–4, **OpenFOAM** (developed against OpenFOAM v9) and **ParaView**.

```bash
git clone https://github.com/VijayN10/synthetic-aorta-cfd-framework.git
cd synthetic-aorta-cfd-framework

python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

OpenFOAM and ParaView are installed separately (they are not Python packages). ParaView post-processing scripts run under ParaView's bundled `pvpython`, not this environment.

## Stage 0 — Statistical modelling (prerequisite)

These two steps learn the anatomy of the source cohort. Both read only `data/input/aaa_data.xlsx` and write to `data/processed/`. The outputs ship with the repo, so this stage is optional unless you change the input data.

```bash
python analysis/fit_distributions.py      # -> data/processed/fitted_distributions.json
python analysis/convex_hull_creator.py    # -> data/processed/convex_hull_metadata.json
```

`fit_distributions.py` fits normal, lognormal, gamma and Weibull distributions to each of the four diameters (proximal neck, distal neck, maximum, distal), per gender × age group, and keeps the best fit by SSE. `convex_hull_creator.py` builds convex hulls over the three diameter pairs — (neck 1, neck 2), (neck 2, maximum), (maximum, distal) — after excluding the manual outlier patients (IDs 40, 42, 71, 72, 78, 109, 163).

## Stage 1 — Generate the synthetic population and OpenFOAM cases

Configure the run in `config.py`:

```python
demographics = Demographics(
    gender='F',          # 'M' or 'F'
    age_group='70-79',   # '50-59', '60-69', '70-79', '80+'
    stat_variant=10,     # number of statistical variations
    random_seed=42,      # for reproducibility
)

morphing_settings = MorphingSettings(
    enable_morphing=True,
    num_variations=10,   # morphed variations per statistical variation
)
```

Then run:

```bash
python main.py
```

This samples parameters from the fitted distributions, generates base and morphed AAA geometries, and validates **each morph against its per-parameter marginal distributions and geometric constraints** (see `src/vesselMorph/geometry_validator.py`). Geometries that fail are rejected and re-attempted. It then writes an OpenFOAM case per surviving geometry under `data/output/ofCases/`, named:

```
AAA_{gender}_{age_group}_stat_{stat_variant}_morph_{morph_variant}
```

Each case directory contains the OpenFOAM structure (`0/`, `constant/`, `system/`), STL geometry, generated inlet velocity (`U`) boundary condition, parameter records, and validation results. Note that the joint convex-hull filter is **not** applied here — that is Stage 2.

### Interactive geometry designer (optional)

To place anatomical points visually instead of editing `config.py`:

```bash
python -m src.vesselGen.geometry_designer
```

## Stage 2 — Population-bounds selection (the convex-hull check)

Once a population exists under `data/output/ofCases/`, select the joint-plausible subset:

```bash
python analysis/data_bound_with_morphed_data_manual.py
```

This reads the generated cases and `data/processed/convex_hull_metadata.json`, computes the **universal interior set** (geometries inside the patient-data hull for all three diameter pairs at once), writes an interior-cases report, and produces the population-bounds plots under `data/processed/bound_plots/`. The interior set is the list of cases that should proceed to CFD.

> **Configuring the analysis scripts.** Most scripts in `analysis/` take their inputs from hardcoded paths in their `if __name__ == "__main__":` block (gender, age group, input/output directories) rather than command-line flags. To run a different demographic, edit that block at the bottom of the script. (The one exception is `geom_vs_age_box_plot.py`, which accepts an optional base directory as a command-line argument.)

### Packaging the interior cases for CFD

Once the interior report exists, bundle the CFD-ready set:

```bash
python analysis/zip_it.py
```

Like Stage 2, this reads the demographic from `config.py`. It parses the universal-interior report and writes two archives into `data/output/ofCases/`: `{gender}_{age_group}_{suffix}_interior_cases.zip` (the interior cases — your CFD-ready set, copied) and `{gender}_{age_group}_{suffix}_all_cases.zip` (all generated cases, moved). Transfer the `_interior_cases.zip` to wherever you run OpenFOAM.

## Stage 3 — Run the CFD simulations

The generated cases are standard OpenFOAM cases. Run them locally or submit to a cluster. A template job script and mesh/solve helpers are provided in `data/input/of_base_case/` (e.g. `aorta_jobscript`). Typical flow per case: `blockMesh` → `snappyHexMesh` → solve → post-process.

### Inlet velocity profile: plug vs parabolic

The paper reports two inlet boundary conditions, and these are selected by **which U file the case uses**, not by a config flag:

- **Plug (flat) inlet** — the default. `src/ofCaseGen/generate_u_file.py` assembles `0/U` from `data/input/U/U_top.txt` + `U_bottom.txt`, giving a `uniformFixedValue` inlet (the same time-varying velocity applied uniformly across the inlet face). This is what `main.py` produces.
- **Parabolic inlet** — use `data/input/U/U_parabolicTimeVaryingInlet` as the case `0/U`. It applies a `codedFixedValue` profile *v(r) = v_max · (1 − (r/R)²)* across the inlet.

To run the parabolic set, substitute `U_parabolicTimeVaryingInlet` for the generated `0/U` in each case before meshing/solving. Downstream results for the two profiles were kept in separate `parabolic/` and `plug/` folders, which is what the `plug`/`parabolic` keys in the correlation scripts refer to.

## Stage 4 — Extract hemodynamic biomarkers and descriptors

Post-processing uses ParaView's `pvpython`. The extraction scripts live in `data/input/of_base_case/` and are deployed with each case:

| Script | Output |
|---|---|
| `paraTawss.py` | Time-averaged wall shear stress (TAWSS) fields |
| `paraOsi.py` | Oscillatory shear index (OSI) fields |
| `paraTawssCyclePlot.py` / `paraOsiCyclePlot.py` | Per-cycle TAWSS / OSI plots |
| `paraWssTimePlot.py` | WSS time series |
| `paraGeomWssStream.py` | Geometry + WSS streamline visualization |
| `extract_wss_percentiles_paraview.py` | WSS percentile extraction |

Shell wrappers (`*.sh`, `postprocess.sh`, `collectAndZipPostProcessing.sh`) drive these over a batch of cases.

## Statistical & figure analysis

Beyond the pipeline stages above, `analysis/` and `data/processed/*/` contain the scripts that reproduce the paper's figures — patient/morphed distribution comparisons, Q–Q plots, parameter-space convex-hull plots, and the geometry–biomarker correlations. `data/processed/README.md` maps each paper figure to its folder and generating script. As with Stage 2, per-run settings (demographic, paths) are edited in each script's `__main__` block.

## Reproducing the dataset

1. (Optional) `python analysis/fit_distributions.py` and `python analysis/convex_hull_creator.py` if you changed `aaa_data.xlsx`.
2. Set the target demographic and counts in `config.py`, then `python main.py` to generate geometries + OpenFOAM cases.
3. `python analysis/data_bound_with_morphed_data_manual.py` to select the universal interior set for CFD.
4. Run the selected cases (Stage 3), choosing the plug or parabolic inlet.
5. Extract biomarkers (Stage 4) and run the correlation/figure scripts for population-level statistics.

## Data availability

The generated virtual population and CFD results are archived separately. *(This statement will be finalized with the Zenodo DOI once archiving is complete.)*

## License

Released under the MIT License. See [LICENSE](LICENSE).

## Citation

If you use this framework, please cite the paper and the software (see [CITATION.cff](CITATION.cff)).

## Contact

Vijay Nandurdikar — vijay.nandurdikar@postgrad.manchester.ac.uk

Ajay Harish — ajay.harish@manchester.ac.uk
