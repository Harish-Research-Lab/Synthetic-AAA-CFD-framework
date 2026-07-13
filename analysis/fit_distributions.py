import pandas as pd
import numpy as np
from scipy import stats
import json
from pathlib import Path
from typing import Dict, Any, List
from numpy.typing import ArrayLike

class AgeGroups:
    """Define age group categories"""
    GROUPS = {
        '<50': {'min': 0, 'max': 49},
        '50-59': {'min': 50, 'max': 59},
        '60-69': {'min': 60, 'max': 69},
        '70-79': {'min': 70, 'max': 79},
        '80+': {'min': 80, 'max': float('inf')}
    }
    
    @classmethod
    def get_group(cls, age: int) -> str:
        """Get age group for a given age"""
        for group, limits in cls.GROUPS.items():
            if limits['min'] <= age <= limits['max']:
                return group
        return 'unknown'

def convert_params_to_list(params: ArrayLike) -> List[float]:
    """Convert distribution parameters to list of floats"""
    if isinstance(params, (tuple, np.ndarray)):
        return [float(p) for p in params]
    return [float(params)]

def fit_distribution(data: np.ndarray) -> Dict[str, Any]:
    """
    Fit statistical distributions to data and select best fit.
    
    Args:
        data: Array of measurements
        
    Returns:
        Dictionary containing best fit distribution and parameters
    """
    if len(data) < 10:
        return None
    
    # Define distributions to test
    distributions = [
        ('norm', stats.norm),
        ('lognorm', stats.lognorm),
        ('gamma', stats.gamma),
        ('weibull_min', stats.weibull_min)
    ]
    
    best_fit = {'sse': float('inf')}
    
    for dist_name, dist in distributions:
        try:
            # Fit distribution
            params = dist.fit(data)
            fitted_dist = dist(*params)
            
            # Calculate PDF for goodness of fit
            hist, bin_edges = np.histogram(data, bins='auto', density=True)
            bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
            pdf = fitted_dist.pdf(bin_centers)
            
            # Calculate goodness of fit using sum of squared errors
            sse = np.sum((hist - pdf) ** 2)
            
            # Calculate additional goodness of fit metrics
            ks_statistic, ks_pvalue = stats.kstest(data, dist_name, params)
            
            if sse < best_fit['sse']:
                best_fit = {
                    'distribution': dist_name,
                    'parameters': convert_params_to_list(params),
                    'sse': float(sse),
                    'ks_statistic': float(ks_statistic),
                    'ks_pvalue': float(ks_pvalue),
                    'range': [float(np.min(data)), float(np.max(data))],
                    'mean': float(np.mean(data)),
                    'std': float(np.std(data)),
                    'n_samples': len(data),
                    'median': float(np.median(data)),
                    'skewness': float(stats.skew(data)),
                    'kurtosis': float(stats.kurtosis(data)),
                    'percentiles': {
                        '25': float(np.percentile(data, 25)),
                        '75': float(np.percentile(data, 75))
                    }
                }
            
        except Exception as e:
            print(f"Failed to fit {dist_name}: {str(e)}")
    
    return best_fit

def fit_distributions(data_path: str, output_path: str):
    """
    Fit statistical distributions to AAA geometric parameters by demographics.
    
    Args:
        data_path: Path to Excel file containing AAA measurements
        output_path: Path to save fitted distribution parameters
    """
    # Define parameters to analyze
    parameters = {
        'neck_diameter_1': {'index': 9, 'name': 'Proximal Neck Diameter'},
        'neck_diameter_2': {'index': 10, 'name': 'Distal Neck Diameter'},
        'max_diameter': {'index': 13, 'name': 'Maximum Aneurysm Diameter'},
        'distal_diameter': {'index': 14, 'name': 'Distal Diameter'}
    }
    
    # Load data
    print(f"Loading data from {data_path}")
    df = pd.read_excel(data_path, header=None).iloc[10:268]
    
    # Extract gender and age columns
    gender_col = 8
    age_col = 7
    
    # Convert age to numeric and get age groups
    ages = pd.to_numeric(df.iloc[:, age_col], errors='coerce')
    age_groups = ages.apply(lambda x: AgeGroups.get_group(x) if not pd.isna(x) else 'unknown')
    
    # Initialize results dictionary
    fitted_params = {
        'demographics': {},
        'metadata': {
            'total_samples': len(df),
            'parameters_analyzed': list(parameters.keys())
        }
    }
    
    # Analyze population demographics
    gender_counts = df.iloc[:, gender_col].value_counts().to_dict()
    age_group_counts = age_groups.value_counts().to_dict()
    fitted_params['metadata']['demographics'] = {
        'gender_distribution': gender_counts,
        'age_distribution': age_group_counts
    }
    
    # Fit distributions for different demographic combinations
    genders = ['All', 'M', 'F']
    age_categories = ['All'] + list(AgeGroups.GROUPS.keys())
    
    for gender in genders:
        fitted_params['demographics'][gender] = {}
        print(f"\nProcessing gender: {gender}")
        
        for age_group in age_categories:
            print(f"  Processing age group: {age_group}")
            fitted_params['demographics'][gender][age_group] = {}
            
            # Create masks for demographic filtering
            if gender == 'All':
                gender_mask = slice(None)
            else:
                gender_mask = (df.iloc[:, gender_col] == gender)
            
            if age_group == 'All':
                age_mask = slice(None)
            else:
                age_group_limits = AgeGroups.GROUPS[age_group]
                age_mask = (ages >= age_group_limits['min']) & (ages <= age_group_limits['max'])
            
            # Combine masks
            if gender == 'All' and age_group == 'All':
                filtered_data = df
            elif gender == 'All':
                filtered_data = df[age_mask]
            elif age_group == 'All':
                filtered_data = df[gender_mask]
            else:
                filtered_data = df[gender_mask & age_mask]
            
            # Skip if insufficient data
            if len(filtered_data) < 10:
                print(f"    Insufficient data for {gender}, {age_group}: {len(filtered_data)} samples")
                continue
            
            # Fit distributions for each parameter
            for param_key, param_info in parameters.items():
                param_data = pd.to_numeric(filtered_data.iloc[:, param_info['index']], 
                                         errors='coerce').dropna()
                
                best_fit = fit_distribution(param_data)
                
                if best_fit is not None:
                    fitted_params['demographics'][gender][age_group][param_key] = best_fit
                    print(f"    {param_info['name']}: {best_fit['distribution']} "
                          f"(n={best_fit['n_samples']})")
    
    # Save results to JSON file
    with open(output_path, 'w') as f:
        json.dump(fitted_params, f, indent=4)
    
    print(f"\nFitted parameters saved to {output_path}")
    
    # Print summary statistics
    print("\nSummary Statistics:")
    print(f"Total samples: {fitted_params['metadata']['total_samples']}")
    print("\nGender distribution:")
    for gender, count in fitted_params['metadata']['demographics']['gender_distribution'].items():
        print(f"  {gender}: {count}")
    print("\nAge group distribution:")
    for age_group, count in fitted_params['metadata']['demographics']['age_distribution'].items():
        print(f"  {age_group}: {count}")

if __name__ == "__main__":
    # Create data directories if they don't exist
    Path("data/processed").mkdir(parents=True, exist_ok=True)
    
    # Fit distributions and save results
    fit_distributions(
        data_path="data/input/aaa_data.xlsx",
        output_path="data/processed/fitted_distributions.json"
    )