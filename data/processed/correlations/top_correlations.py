import numpy as np
import pandas as pd
from scipy.stats import pearsonr
from pathlib import Path

# Get the directory where this script is located
SCRIPT_DIR = Path(__file__).parent.resolve()

# Define parameter groups
anatomical_params = ['neck_diameter_1', 'neck_diameter_2', 'max_diameter', 'distal_diameter']
geometric_params = ['volume', 'surface_area', 'tortuosity',
                    'sphericity', 'convexity', 'average_radius']
hemodynamic_params = ['WSS_mean_cycle4', '95%_WSS_systolic', 'TAWSS_mean',
                      '%_area_TAWSS_below_0.4', 'OSI_mean', '%_area_OSI_above_0.3']

all_input_params = anatomical_params + geometric_params

def compute_correlations(df, input_params, output_params):
    """Compute all correlations between input and output parameters."""
    results = []

    for y_param in output_params:
        for x_param in input_params:
            valid_data = df[[y_param, x_param]].dropna()

            if len(valid_data) > 2:
                corr, p_val = pearsonr(valid_data[x_param], valid_data[y_param])
                results.append({
                    'Input Parameter': x_param,
                    'Output Parameter': y_param,
                    'r': corr,
                    'p-value': p_val,
                    '|r|': abs(corr)
                })

    return pd.DataFrame(results)

def get_significance_marker(p_val):
    """Return significance marker based on p-value."""
    if p_val < 0.001:
        return '***'
    elif p_val < 0.01:
        return '**'
    elif p_val < 0.05:
        return '*'
    else:
        return ''

def format_table(df_top, profile_name, n=5):
    """Format the top correlations as a readable table."""
    lines = []
    lines.append(f"\n{'='*80}")
    lines.append(f"TOP {n} STRONGEST CORRELATIONS - {profile_name.upper()} INLET PROFILE")
    lines.append(f"{'='*80}")
    lines.append(f"{'Rank':<6}{'Input Parameter':<22}{'Output Parameter':<25}{'r':>8}{'p-value':>12}{'Sig':>5}")
    lines.append(f"{'-'*80}")

    for i, row in df_top.head(n).iterrows():
        sig = get_significance_marker(row['p-value'])
        lines.append(f"{i+1:<6}{row['Input Parameter']:<22}{row['Output Parameter']:<25}{row['r']:>8.3f}{row['p-value']:>12.2e}{sig:>5}")

    lines.append(f"{'-'*80}")
    lines.append("Significance: * p<0.05, ** p<0.01, *** p<0.001")

    return '\n'.join(lines)

def main():
    # Define files with their display names
    profile_files = {
        'parabolic': SCRIPT_DIR / 'parabolic' / 'aaa_parameters_metrics_parabolic.xlsx',
        'plug': SCRIPT_DIR / 'plug' / 'aaa_parameters_metrics_plug.xlsx'
    }

    all_output = []

    for profile, filepath in profile_files.items():
        if not filepath.exists():
            print(f"Warning: File not found - {filepath}")
            continue

        df = pd.read_excel(filepath)

        # Compute all correlations
        corr_df = compute_correlations(df, all_input_params, hemodynamic_params)

        # Sort by absolute correlation value (strongest first)
        corr_df_sorted = corr_df.sort_values('|r|', ascending=False).reset_index(drop=True)

        # Format and print table
        table = format_table(corr_df_sorted, profile, n=5)
        print(table)
        all_output.append(table)

        # Also save detailed results to CSV
        corr_df_sorted.to_csv(
            SCRIPT_DIR / f'all_correlations_{profile}.csv',
            index=False
        )

    # Save combined text output
    with open(SCRIPT_DIR / 'top_correlations_summary.txt', 'w') as f:
        f.write('\n'.join(all_output))
        f.write('\n')

    print(f"\n{'='*80}")
    print("Results saved to:")
    print("  - top_correlations_summary.txt (formatted tables)")
    print("  - all_correlations_parabolic.csv (full results)")
    print("  - all_correlations_plug.csv (full results)")
    print(f"{'='*80}")

if __name__ == '__main__':
    main()