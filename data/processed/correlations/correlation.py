import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import pearsonr
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()

anatomical_params  = ['neck_diameter_1', 'neck_diameter_2', 'max_diameter', 'distal_diameter']
geometric_params   = ['volume', 'surface_area', 'tortuosity',
                      'sphericity', 'convexity', 'average_radius']
hemodynamic_params = ['WSS_mean_cycle4', '95%_WSS_systolic', 'TAWSS_mean',
                      '%_area_TAWSS_below_0.4', 'OSI_mean', '%_area_OSI_above_0.3']

param_combinations = [
    (anatomical_params,                    hemodynamic_params, "anatomical_hemodynamic"),
    (geometric_params,                     hemodynamic_params, "geometric_hemodynamic"),
    (anatomical_params + geometric_params, hemodynamic_params, "all_parameters_hemodynamic"),
]

profile_files = {
    'parabolic': (SCRIPT_DIR / 'parabolic' / 'aaa_parameters_metrics_parabolic.xlsx',
                  SCRIPT_DIR / 'parabolic'),
    'plug':      (SCRIPT_DIR / 'plug'      / 'aaa_parameters_metrics_plug.xlsx',
                  SCRIPT_DIR / 'plug'),
}

for profile, (xlsx_path, out_dir) in profile_files.items():
    if not xlsx_path.exists():
        print(f"Warning: {xlsx_path} not found, skipping {profile}.")
        continue

    df = pd.read_excel(xlsx_path)
    print(f"\nProcessing {profile} ({len(df)} rows)...")

    for params_x, params_y, filename in param_combinations:
        correlation_matrix = np.zeros((len(params_y), len(params_x)))
        p_values           = np.zeros((len(params_y), len(params_x)))

        for i, y_param in enumerate(params_y):
            for j, x_param in enumerate(params_x):
                valid_data = df[[y_param, x_param]].dropna()
                if len(valid_data) > 2:
                    corr, p_val = pearsonr(valid_data[x_param], valid_data[y_param])
                    correlation_matrix[i, j] = corr
                    p_values[i, j]           = p_val

        plt.figure(figsize=(12, 8))
        ax = sns.heatmap(correlation_matrix,
                         annot=True, fmt='.2f', cmap='RdBu_r',
                         vmin=-1, vmax=1,
                         xticklabels=params_x, yticklabels=params_y)

        for i in range(len(params_y)):
            for j in range(len(params_x)):
                if p_values[i, j] < 0.001:
                    ax.text(j+0.5, i+0.85, '***', ha='center', va='center', color='black')
                elif p_values[i, j] < 0.01:
                    ax.text(j+0.5, i+0.85, '**',  ha='center', va='center', color='black')
                elif p_values[i, j] < 0.05:
                    ax.text(j+0.5, i+0.85, '*',   ha='center', va='center', color='black')

        plt.yticks(rotation=0)
        plt.xticks(rotation=45)
        plt.title(f'Influence of {filename.replace("_", " ").title()} Parameters on Metrics'
                  f' ({profile.capitalize()})')
        plt.tight_layout()
        out_name = f"{filename}_correlation.png"
        plt.savefig(out_dir / out_name, dpi=300)
        plt.close()
        print(f"  Saved {profile}/{out_name}")

print("\nCorrelation analysis complete!")
