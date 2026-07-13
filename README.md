# Synthetic Aorta CFD Framework

A framework for generating a **synthetic virtual population** of Abdominal Aortic Aneurysm (AAA) geometries, setting them up as **OpenFOAM** computational fluid dynamics (CFD) cases, and extracting **hemodynamic biomarkers and geometric descriptors** from the results.

This is the public code release accompanying:

> V. Nandurdikar *et al.*, *"Virtual Population to Re-assess AAA Risk Using Neck Geometry and Shape Compactness Alongside Maximum Diameter"*, **Royal Society Open Science** (2026).

## Pipeline overview

The framework implements a three-stage pipeline:

1. **Synthetic case generation** — sample geometric parameters from patient-derived statistical distributions, build a parametric AAA surface, apply spherical morphing for anatomical diversity, validate each geometry against a patient-data convex hull, and write a ready-to-run OpenFOAM case.
2. **CFD simulation** — run the generated OpenFOAM cases (locally or on an HPC cluster) to solve pulsatile blood flow.
3. **Biomarker / descriptor extraction** — post-process the CFD results with ParaView to extract wall shear stress (WSS), time-averaged WSS (TAWSS), oscillatory shear index (OSI), and related hemodynamic biomarkers, alongside geometric descriptors.

## Repository structure

```
synthetic-aorta-cfd-framework/
├── main.py                     # Entry point: generation + OpenFOAM case setup
├── config.py                   # Configuration (demographics, morphing, vessel settings)
├── requirements.txt            # Python dependencies
├── src/
│   ├── vesselGen/              # Parametric vessel geometry generation
│   ├── vesselMorph/            # Spherical morphing + geometry validation
│   ├── vesselStats/            # Statistical parameter sampling
│   ├── ofCaseGen/              # OpenFOAM case generation (mesh, BCs, U file)
│   └── visualization/          # Geometry / velocity visualization
├── analysis/                   # Statistical & convex-hull boundary analysis scripts
└── data/
    ├── input/
    │   ├── U/                  # Inlet velocity waveform data
    │   ├── shm/                # snappyHexMesh point definitions
    │   ├── of_base_case/       # OpenFOAM base case template + ParaView extraction scripts
    │   └── aaa_data.xlsx       # Patient-derived measurements (statistical basis)
    └── processed/              # Fitted distributions + convex-hull metadata (JSON)
```

> **Note on data.** Generated geometries (`data/input/geometry/`) and CFD results (`data/output/`) are **not** included in this repository because of their size; they are produced by running the pipeline. See *Reproducing the dataset* below.

## Installation

Requires **Python 3.11** and, for stages 2–3, **OpenFOAM** and **ParaView**.

```bash
git clone https://github.com/VijayN10/synthetic-aorta-cfd-framework.git
cd synthetic-aorta-cfd-framework

python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

OpenFOAM and ParaView are installed separately (they are not Python packages). The framework was developed against OpenFOAM with the ParaView build bundled alongside it.

## Stage 1 — Generate the synthetic population and OpenFOAM cases

Configure the run in `config.py`:

```python
demographics = Demographics(
    gender='F',          # 'M' or 'F'
    age_group='70-79',   # '50-59', '60-69', '70-79', '80-89'
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

This samples parameters from the fitted distributions, generates base and morphed AAA geometries, validates each against the patient-data convex hull, and writes an OpenFOAM case per geometry under `data/output/ofCases/`. Cases are named:

```
AAA_{gender}_{age_group}_stat_{stat_variant}_morph_{morph_variant}
```

Each case directory contains the OpenFOAM structure (`0/`, `constant/`, `system/`), STL geometry, generated inlet velocity (`U`) boundary condition, parameter records, and validation results.

### Interactive geometry designer (optional)

To place anatomical points visually instead of editing `config.py`:

```bash
python -m src.vesselGen.geometry_designer
```

## Stage 2 — Run the CFD simulations

The generated cases are standard OpenFOAM cases. Run them locally or submit to a cluster. A template job script and mesh/solve helpers are provided in `data/input/of_base_case/` (e.g. `aorta_jobscript`). Typical flow per case: `blockMesh` → `snappyHexMesh` → solve → post-process.

## Stage 3 — Extract hemodynamic biomarkers and descriptors

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

## Statistical & boundary analysis

The `analysis/` directory contains the scripts used to fit distributions to patient data, build the convex-hull bounds, identify physiologically plausible "interior" cases among the morphed population, and produce the correlation/distribution figures. Example:

```bash
python -m analysis.data_bound_with_morphed_data_manual \
    --data_path data/input/aaa_data.xlsx \
    --output_dir data/processed/bound_plots \
    --ofcases_dir data/output/ofCases \
    --gender F --age_group 70-79 \
    --hull_data_path data/processed/convex_hull_metadata.json
```

## Reproducing the dataset

1. Set the target demographic and counts in `config.py`.
2. `python main.py` to generate geometries + OpenFOAM cases.
3. Run the cases (Stage 2).
4. Extract biomarkers (Stage 3) and run `analysis/` scripts for population-level statistics.

## Data availability

The generated virtual population and CFD results are archived separately. *(This statement will be finalized with the Zenodo DOI once archiving is complete.)*

## License

Released under the MIT License. See [LICENSE](LICENSE).

## Citation

If you use this framework, please cite the paper and the software (see [CITATION.cff](CITATION.cff)).

## Contact

Vijay Nandurdikar — vijay.nandurdikar@postgrad.manchester.ac.uk
