from distribution_with_patient_data import PatientDataAnalyzer, AgeGroups
import numpy as np
from scipy import stats
from pathlib import Path
from typing import Dict
import pandas as pd

def calculate_correlations(data1: np.ndarray, data2: np.ndarray) -> Dict[str, float]:
    """
    Calculate correlation coefficient and p-value for two parameters.
    """
    # Remove any NaN values
    mask = ~(np.isnan(data1) | np.isnan(data2))
    clean_data1 = data1[mask]
    clean_data2 = data2[mask]
    
    # Calculate Pearson correlation coefficient and p-value
    r_value, p_value = stats.pearsonr(clean_data1, clean_data2)
    
    # Calculate Spearman correlation coefficient and p-value
    rho, spearman_p = stats.spearmanr(clean_data1, clean_data2)
    
    return {
        'pearson_r': float(r_value),
        'pearson_p': float(p_value),
        'spearman_rho': float(rho),
        'spearman_p': float(spearman_p),
        'n_samples': len(clean_data1)
    }

def analyze_parameter_correlations(analyzer: PatientDataAnalyzer, gender: str, age_group: str) -> Dict:
    """
    Analyze correlations between parameter pairs using existing data analyzer.
    """
    param_pairs = [
        ('neck_diameter_1', 'neck_diameter_2'),
        ('neck_diameter_2', 'max_diameter'),
        ('max_diameter', 'distal_diameter')
    ]
    
    # Get patient data using existing analyzer method
    patient_data = analyzer.get_patient_data(gender, age_group)
    
    results = {}
    for param1, param2 in param_pairs:
        data1 = patient_data[param1]
        data2 = patient_data[param2]
        results[f"{analyzer.param_names[param1]}_vs_{analyzer.param_names[param2]}"] = calculate_correlations(data1, data2)
    
    return results

def generate_correlation_report(results: Dict, output_file: Path) -> None:
    """Generate a text report of correlation results"""
    with open(output_file, 'w') as f:
        f.write("Parameter Correlation Analysis\n")
        f.write("=" * 30 + "\n\n")
        
        for pair, stats in results.items():
            f.write(f"{pair}\n")
            f.write("-" * len(pair) + "\n")
            f.write(f"Number of samples: {stats['n_samples']}\n\n")
            
            f.write("Pearson Correlation:\n")
            f.write(f"r = {stats['pearson_r']:.3f}\n")
            f.write(f"p = {stats['pearson_p']:.3e}\n\n")
            
            f.write("Spearman Correlation:\n")
            f.write(f"rho = {stats['spearman_rho']:.3f}\n")
            f.write(f"p = {stats['spearman_p']:.3e}\n\n")

def main():
    print("Starting correlation analysis...")
    
    # Initialize analyzer using existing class
    analyzer = PatientDataAnalyzer(
        fitted_dist_file='data/processed/fitted_distributions.json',
        data_path='data/input/aaa_data.xlsx'
    )
    
    # Define analysis groups
    genders = ['All', 'M', 'F']
    age_groups = ['All'] + list(AgeGroups.GROUPS.keys())
    
    # Create base output directory
    base_output = Path('data/processed/correlation_analysis')
    base_output.mkdir(exist_ok=True, parents=True)
    
    # Generate reports for each combination
    for gender in genders:
        for age_group in age_groups:
            try:
                print(f"\nProcessing: Gender={gender}, Age Group={age_group}")
                
                # Create output directory for this demographic
                output_dir = base_output / f"{gender}_{age_group}"
                output_dir.mkdir(exist_ok=True)
                
                # Generate correlations
                results = analyze_parameter_correlations(analyzer, gender, age_group)
                
                # Save report
                report_file = output_dir / "correlation_report.txt"
                generate_correlation_report(results, report_file)
                print(f"Report saved to: {report_file}")
                
            except Exception as e:
                print(f"Skipping {gender}/{age_group} due to insufficient data: {str(e)}")
                continue
    
    print("\nCorrelation analysis complete!")

if __name__ == "__main__":
    main()