# Example OpenFOAM cases

Four representative synthetic Abdominal Aortic Aneurysm (AAA) cases, one per
demographic studied in the paper, provided as ready-to-run OpenFOAM setups so
readers can inspect a complete case or reproduce the CFD workflow end to end.

These are produced by the pipeline in this repository; see the top-level [`README.md`](../../../README.md)
for the full generation

| Case folder | Gender | Age group | Inlet profile |
| --- | --- | --- | --- |
| `AAA_M_60-69_stat_10_parabolic_morph_4` | Male | 60–69 | parabolic |
| `AAA_M_70-79_stat_1_parabolic_morph_1`  | Male | 70–79 | parabolic |
| `AAA_M_80+_stat_2_parabolic_morph_2`    | Male | 80+   | parabolic |
| `AAA_F_70-79_stat_2_parabolic_morph_8`  | Female | 70–79 | parabolic |

Folder naming: `AAA_{gender}_{age_group}_stat_{statistical_variant}_{suffix}_morph_{morph_variant}`.

## Case structure

Each case is a standard OpenFOAM case directory:

```
AAA_.../
├── 0/                       # Initial & boundary conditions (U, p)
├── constant/
│   ├── transportProperties  # Newtonian blood, nu = 3.5e-6 m^2/s
│   ├── turbulenceProperties
│   └── triSurface/          # wall.stl, inlet.stl, outlet.stl (geometry)
├── system/                  # blockMeshDict, snappyHexMeshDict, controlDict,
│                            #   fvSchemes, fvSolution, surfaceFeaturesDict, ...
├── parameters/
│   ├── geometry_params.json # Neck 1/2, max, distal diameters (mm)
│   ├── config.json          # Demographics + vessel/morphing settings
│   └── validation_results.json
├── visualizations/          # Base vs morphed geometry views, velocity profile,
│                            #   geometry_metrics.json, metrics_summary.txt
├── *.py / *.sh              # ParaView post-processing (TAWSS, OSI, WSS) + wrappers
├── aorta_jobscript          # Example HPC submission script
└── foam.foam                # Open in ParaView
```

## Solver settings

Transient pulsatile flow with `pisoFoam` (OpenFOAM v9). Blood is modelled as
Newtonian with kinematic viscosity `nu = 3.5e-6 m^2/s`. The run covers 4 cardiac
cycles (`endTime = 3.8 s`, `deltaT = 1e-4 s`, `writeInterval = 0.05 s`).

## How to run a case

Each case ships with `aorta_jobscript`, a SLURM script that runs the full
mesh → solve sequence in parallel (32 cores). On a cluster, just submit it from
inside the case directory:

```bash
cd AAA_M_70-79_stat_1_parabolic_morph_1
sbatch aorta_jobscript
```

The jobscript (`openfoam/9-foss-2021a`) performs, in order: `surfaceFeatures`,
`blockMesh`, parallel `snappyHexMesh` (via `decomposePar` → `reconstructParMesh`),
`checkMesh`, a `transformPoints "scale=(0.001 0.001 0.001)"` step that converts the
geometry from mm to m, then parallel `pisoFoam` (`decomposePar` → solve →
`reconstructPar`). Edit the `#SBATCH` header and `numberOfSubdomains` if you run on
a different core count.

To run serially on a workstation, drop the parallel wrappers:

```bash
cd AAA_M_70-79_stat_1_parabolic_morph_1
surfaceFeatures
blockMesh
snappyHexMesh -overwrite
checkMesh
transformPoints "scale=(0.001 0.001 0.001)"   # mm -> m; required before the solve
pisoFoam
```

Post-process wall shear stress biomarkers (TAWSS, OSI, WSS percentiles) with the
bundled ParaView scripts via `pvpython`, driven by `postprocess.sh` /
`collectAndZipPostProcessing.sh`. See the top-level README (Stage 4) for details.
