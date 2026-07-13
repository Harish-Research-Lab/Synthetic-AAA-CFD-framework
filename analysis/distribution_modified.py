import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import json
from scipy import stats
import pandas as pd
import re
from typing import Dict, List, Optional, Tuple, Literal

from distribution_with_patient_data_modified import ModifiedPatientDataAnalyzer

from scipy.stats import entropy
from scipy.integrate import quad

# Configuration for analysis
ANALYSIS_CONFIG = {
    'gender': 'F',
    'age_group': '70-79',
    'custom_suffix': 'prob_distribution'
}

class ComparisonAnalyzer:
    def __init__(self, base_dir: Path, fitted_dist_file: str, data_path: str):
        self.base_dir = base_dir
        self.fitted_dist_file = fitted_dist_file
        self.patient_analyzer = ModifiedPatientDataAnalyzer(fitted_dist_file, data_path)
        
    def collect_case_measurements(self, case_dir: Path, validation_name: str) -> Optional[float]:
        validation_file = case_dir / 'parameters' / 'validation_results.json'
        if validation_file.exists():
            with open(validation_file, 'r') as f:
                data = json.load(f)
                return data['measurements'].get(validation_name)
        return None

    def get_case_measurements(self, folder_name: str, validation_name: str) -> List[float]:
        measurements = []
        folder_path = self.base_dir / folder_name
        
        if not folder_path.exists():
            print(f"Warning: Folder not found: {folder_path}")
            return measurements
            
        for case_dir in folder_path.glob("*"):
            if case_dir.is_dir():
                measurement = self.collect_case_measurements(case_dir, validation_name)
                if measurement is not None:
                    measurements.append(measurement)
        
        return measurements

    def plot_combined_distribution(
        self,
        param_data: np.ndarray,
        param_name: str,
        validation_name: str,
        all_cases_data: List[float],
        interior_cases_data: Optional[List[float]] = None,
        scale_factor: float = 0.5
    ):
        """Plot distributions comparing patient data, all cases, and optionally interior cases"""
        save_dir = Path('data/processed/distribution_plots/multi_comparison_modified')
        save_dir.mkdir(exist_ok=True, parents=True)
        
        self.patient_analyzer.setup_style(scale_factor)
        fig = plt.figure(figsize=(4*scale_factor, 3*scale_factor))
        
        ax = plt.gca()
        for spine in ax.spines.values():
            spine.set_linewidth(0.5)

        # Set up histogram bins using global range
        global_range = self.patient_analyzer.global_ranges[param_name]
        n_bins = 20
        bins = np.linspace(global_range['min'], global_range['max'], n_bins)
        
        # Plot histograms with reduced alpha for better visibility
        plt.hist(param_data, bins=bins, density=True, alpha=0.3, color='lightblue', label='Patient Data')
        plt.hist(all_cases_data, bins=bins, density=True, alpha=0.3, color='lightgreen', label='All Cases')
        if interior_cases_data:
            plt.hist(interior_cases_data, bins=bins, density=True, alpha=0.3, color='lightcoral', label='Interior Cases')
        
        # Fit and plot distributions
        x_range = np.linspace(global_range['min'], global_range['max'], 100)
        
        # Patient distribution
        patient_dist = self.fit_distribution(param_data)
        patient_dist_func = self.get_distribution_function(patient_dist['distribution'], patient_dist['parameters'])
        plt.plot(x_range, patient_dist_func.pdf(x_range), 'b-', lw=0.3)
        
        # All cases distribution
        all_cases_dist = self.fit_distribution(all_cases_data)
        all_cases_dist_func = self.get_distribution_function(all_cases_dist['distribution'], all_cases_dist['parameters'])
        plt.plot(x_range, all_cases_dist_func.pdf(x_range), 'g-', lw=0.3)
        
        # Interior cases distribution if provided
        if interior_cases_data:
            interior_dist = self.fit_distribution(interior_cases_data)
            interior_dist_func = self.get_distribution_function(interior_dist['distribution'], interior_dist['parameters'])
            plt.plot(x_range, interior_dist_func.pdf(x_range), 'r-', lw=0.3)
        
        # Set axis ranges and ticks
        x_min, x_max = global_range['min'], global_range['max']
        ax.set_xlim(x_min, x_max)
        major_ticks = np.arange(int(x_min), int(x_max) + 1, 5)
        ax.set_xticks(major_ticks)
        ax.tick_params(which='major', length=4, width=0.5, direction='out')

        # Set fixed y-ranges
        y_ranges = {
            'neck_diameter_1': {'min': 0, 'max': 0.3, 'step': 0.05},
            'neck_diameter_2': {'min': 0, 'max': 0.3, 'step': 0.05}, 
            'max_diameter': {'min': 0, 'max': 0.15, 'step': 0.025},
            'distal_diameter': {'min': 0, 'max': 0.2, 'step': 0.05}
        }
        y_range = y_ranges[param_name]
        ax.set_ylim(y_range['min'], y_range['max'])
        y_ticks = np.arange(y_range['min'], y_range['max'] + y_range['step'], y_range['step'])
        ax.set_yticks(y_ticks)
        
        plt.xlabel(f'{self.patient_analyzer.param_names[param_name]} (mm)')
        plt.ylabel('Probability Density')
        plt.tight_layout()
        
        # Create standalone legend
        self.create_standalone_legend(save_dir, param_name, bool(interior_cases_data))
        
        # Save plot
        comparison_type = 'three_way' if interior_cases_data else 'two_way'
        filename = (f'{param_name}_{validation_name.lower()}_'
                   f'{ANALYSIS_CONFIG["gender"]}_{ANALYSIS_CONFIG["age_group"]}_'
                   f'{ANALYSIS_CONFIG["custom_suffix"]}_{comparison_type}_fixed.png')
        plt.savefig(save_dir / filename, dpi=600, bbox_inches='tight')
        plt.close()

        # Generate statistics report
        self.generate_statistics_report(
            save_dir,
            param_name,
            validation_name,
            comparison_type,
            {
                'Patient Data': (param_data, patient_dist),
                'All Cases': (all_cases_data, all_cases_dist),
                'Interior Cases': (interior_cases_data, interior_dist) if interior_cases_data else None
            }
        )

    def calculate_kl_divergence(self, dist1, dist2, range_min: float, range_max: float, n_points: int = 1000) -> float:
        """
        Calculate Kullback-Leibler divergence between two probability distributions.
        
        Args:
            dist1: First probability distribution (reference/patient distribution)
            dist2: Second probability distribution (comparison distribution)
            range_min: Minimum value for calculation range
            range_max: Maximum value for calculation range
            n_points: Number of points for numerical integration
            
        Returns:
            float: KL divergence value
        """
        # Create evaluation points
        x = np.linspace(range_min, range_max, n_points)
        
        # Calculate PDFs
        p = dist1.pdf(x)
        q = dist2.pdf(x)
        
        # Add small epsilon to prevent division by zero
        epsilon = 1e-10
        p = p + epsilon
        q = q + epsilon
        
        # Normalize PDFs to ensure they integrate to 1
        p = p / np.trapz(p, x)
        q = q / np.trapz(q, x)
        
        # Calculate KL divergence
        kl_div = entropy(p, q, base=2)  # Using log base 2 for interpretation in bits
        
        return kl_div

    def generate_statistics_report(
        self,
        save_dir: Path,
        param_name: str,
        validation_name: str,
        comparison_type: str,
        data_dict: Dict[str, Optional[Tuple[np.ndarray, Dict]]]
    ):
        """Generate a detailed statistics report for the distributions including KL divergence"""
        filename = (f'{param_name}_{validation_name.lower()}_'
                   f'{ANALYSIS_CONFIG["gender"]}_{ANALYSIS_CONFIG["age_group"]}_'
                   f'{ANALYSIS_CONFIG["custom_suffix"]}_{comparison_type}_stats.txt')
        
        with open(save_dir / filename, 'w') as f:
            f.write(f"Statistics Report for {self.patient_analyzer.param_names[param_name]}\n")
            f.write(f"Validation Point: {validation_name}\n")
            f.write("=" * 50 + "\n\n")
            
            # Get patient distribution for KL divergence calculation
            patient_data, patient_dist = data_dict['Patient Data']
            patient_dist_func = self.get_distribution_function(
                patient_dist['distribution'], 
                patient_dist['parameters']
            )
            
            # Calculate global range for KL divergence
            global_min = float('inf')
            global_max = float('-inf')
            
            # Find global min and max across all valid data
            for _, data_info in data_dict.items():
                if data_info is not None:
                    data_array = data_info[0]  # Get the data array from the tuple
                    if len(data_array) > 0:  # Check if array is not empty
                        global_min = min(global_min, np.min(data_array))
                        global_max = max(global_max, np.max(data_array))
            
            for data_type, data_info in data_dict.items():
                if data_info is not None and isinstance(data_info, tuple):
                    data, dist_info = data_info
                    if data is not None and dist_info is not None:
                        f.write(f"{data_type}:\n")
                        f.write("-" * 20 + "\n")
                        f.write(f"Distribution: {dist_info['distribution']}\n")
                        f.write(f"Mean: {dist_info['mean']:.1f} mm\n")
                        f.write(f"Std: {dist_info['std']:.1f} mm\n")
                        f.write(f"Sample Size: {len(data)}\n")
                        f.write(f"Range: [{np.min(data):.1f}, {np.max(data):.1f}] mm\n")
                        
                        # Calculate and report KL divergence for non-patient distributions
                        if data_type != 'Patient Data':
                            comparison_dist = self.get_distribution_function(
                                dist_info['distribution'],
                                dist_info['parameters']
                            )
                            kl_div = self.calculate_kl_divergence(
                                patient_dist_func,
                                comparison_dist,
                                global_min,
                                global_max
                            )
                            f.write(f"KL Divergence from Patient Distribution: {kl_div:.4f} bits\n")
                        
                        f.write("\n")
            
            # Add interpretation guide for KL divergence
            f.write("\nKL Divergence Interpretation Guide:\n")
            f.write("-" * 30 + "\n")
            f.write("- Values close to 0 indicate very similar distributions\n")
            f.write("- Values < 0.5 suggest minor differences\n")
            f.write("- Values 0.5-1.0 indicate moderate differences\n")
            f.write("- Values > 1.0 suggest substantial differences\n")
            f.write("\nNote: KL divergence is measured in bits and represents the information loss\n")
            f.write("when using the comparison distribution to approximate the patient distribution.\n")


    @staticmethod
    def create_standalone_legend(save_dir: Path, param_name: str, include_interior: bool = False):
        plt.figure(figsize=(12, 2))
        ax = plt.gca()
        ax.axis('off')
        
        handles = [
            plt.Rectangle((0, 0), 1, 1, fc='lightblue', alpha=0.3, label='Patient Data'),
            plt.Line2D([0], [0], color='blue', lw=2, label='Patient Distribution'),
            plt.Rectangle((0, 0), 1, 1, fc='lightgreen', alpha=0.3, label='All Cases'),
            plt.Line2D([0], [0], color='green', lw=2, label='All Cases Distribution')
        ]
        
        if include_interior:
            handles.extend([
                plt.Rectangle((0, 0), 1, 1, fc='lightcoral', alpha=0.3, label='Interior Cases'),
                plt.Line2D([0], [0], color='red', lw=2, label='Interior Distribution')
            ])
        
        legend = plt.legend(handles=handles,
                          loc='center',
                          ncol=6 if include_interior else 4,
                          fontsize=10,
                          frameon=True,
                          framealpha=1,
                          fancybox=True,
                          shadow=True)
        
        legend.get_frame().set_facecolor('white')
        filename = f'legend_{param_name}_{"three_way" if include_interior else "two_way"}.png'
        plt.savefig(save_dir / filename, dpi=600, bbox_inches='tight', transparent=True)
        plt.close()

    @staticmethod
    def fit_distribution(data: np.ndarray) -> Dict:
        """Fit best distribution to data"""
        if len(data) < 10:
            raise ValueError(f"Insufficient data points: {len(data)} < 10")
            
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
                
                if sse < best_fit['sse']:
                    best_fit = {
                        'distribution': dist_name,
                        'parameters': [float(p) for p in params],
                        'sse': float(sse),
                        'mean': float(np.mean(data)),
                        'std': float(np.std(data)),
                        'range': [float(np.min(data)), float(np.max(data))]
                    }
                    
            except Exception as e:
                print(f"Failed to fit {dist_name}: {str(e)}")
                continue
        
        if best_fit['sse'] == float('inf'):
            raise ValueError("Failed to fit any distribution")
            
        return best_fit

    @staticmethod
    def get_distribution_function(dist_name: str, params: list):
        """Get scipy distribution function based on name and parameters"""
        if dist_name == 'norm':
            return stats.norm(*params)
        elif dist_name == 'lognorm':
            return stats.lognorm(*params)
        elif dist_name == 'gamma':
            return stats.gamma(*params)
        elif dist_name == 'weibull_min':
            return stats.weibull_min(*params)
        else:
            raise ValueError(f"Unknown distribution: {dist_name}")

    def analyze_distributions(self):
        """Analyze and plot distributions for all parameters"""
        gender = ANALYSIS_CONFIG['gender']
        age_group = ANALYSIS_CONFIG['age_group']
        suffix = ANALYSIS_CONFIG['custom_suffix']
        
        # Get patient data
        patient_data = self.patient_analyzer.get_patient_data(gender, age_group)
        
        # Define parameter mapping
        param_mapping = {
            'neck_diameter_1': ['Inlet', 'Neck 1'],
            'neck_diameter_2': ['Neck 2'],
            'max_diameter': ['Maximum Aneurysm'],
            'distal_diameter': ['Distal']
        }
        
        for param_name, validation_names in param_mapping.items():
            for validation_name in validation_names:
                # Get measurements for all cases and interior cases
                all_cases_folder = f"{gender}_{age_group}_{suffix}_all_cases"
                interior_cases_folder = f"{gender}_{age_group}_{suffix}_interior_cases"
                
                all_cases_data = self.get_case_measurements(all_cases_folder, validation_name)
                interior_cases_data = self.get_case_measurements(interior_cases_folder, validation_name)
                
                if not all_cases_data:
                    print(f"No data found for {validation_name} in all cases")
                    continue
                
                # Create two-way comparison (patient vs all cases)
                self.plot_combined_distribution(
                    patient_data[param_name],
                    param_name,
                    validation_name,
                    all_cases_data
                )
                
                # Create three-way comparison if interior cases exist
                if interior_cases_data:
                    self.plot_combined_distribution(
                        patient_data[param_name],
                        param_name,
                        validation_name,
                        all_cases_data,
                        interior_cases_data
                    )
                else:
                    print(f"No interior cases data found for {validation_name}")

if __name__ == "__main__":
    analyzer = ComparisonAnalyzer(
        base_dir=Path('data/output/ofCases'),
        fitted_dist_file='data/processed/fitted_distributions.json',
        data_path='data/input/aaa_data.xlsx'
    )

    print(f"Analyzing {ANALYSIS_CONFIG['gender']}, Age {ANALYSIS_CONFIG['age_group']}")
    print("\nGenerating distribution comparisons...")
    analyzer.analyze_distributions()
    print("Done!")