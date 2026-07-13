import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import json
from scipy import stats
import pandas as pd
from typing import Dict, Optional

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

class PatientDataAnalyzer:
    def __init__(self, fitted_dist_file: str, data_path: str):
        self.fitted_dist_file = fitted_dist_file
        self.df = pd.read_excel(data_path, header=None).iloc[10:268]
        self.setup_parameters()
        self.setup_style()
        
    def setup_parameters(self):
        self.param_indices = {
            'neck_diameter_1': 9,
            'neck_diameter_2': 10,
            'max_diameter': 13,
            'distal_diameter': 14
        }
        
        self.param_names = {
            'neck_diameter_1': 'Neck Diameter 1',
            'neck_diameter_2': 'Neck Diameter 2', 
            'max_diameter': 'Maximum Aneurysm Diameter',
            'distal_diameter': 'Distal Diameter'
        }
        
    def setup_style(self):
        sns.set_theme(style="white")
        plt.rcParams.update({
            'font.family': 'serif',
            'font.size': 10,
            'axes.labelsize': 12,
            'axes.titlesize': 14
        })

    def load_fitted_distribution(self, gender: str, age_group: str) -> Dict:
        with open(self.fitted_dist_file, 'r') as f:
            data = json.load(f)
        try:
            return data['demographics'][gender][age_group]
        except KeyError as e:
            print(f"Error: Could not find distribution for gender={gender}, age_group={age_group}")
            raise

    @staticmethod
    def get_distribution_function(dist_name: str, params: list):
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

    def get_patient_data(self, gender: str, age_group: str) -> Dict[str, np.ndarray]:
        param_data = {}
        
        gender_mask = slice(None) if gender == 'All' else (self.df.iloc[:, 8] == gender)
        
        if age_group == 'All':
            age_mask = slice(None)
        else:
            age_limits = AgeGroups.GROUPS[age_group]
            ages = pd.to_numeric(self.df.iloc[:, 7], errors='coerce')
            age_mask = (ages >= age_limits['min']) & (ages <= age_limits['max'])
        
        for param_name, idx in self.param_indices.items():
            if gender == 'All' and age_group == 'All':
                data = self.df.iloc[:, idx]
            elif gender == 'All':
                data = self.df[age_mask].iloc[:, idx]
            elif age_group == 'All':
                data = self.df[gender_mask].iloc[:, idx]
            else:
                data = self.df[gender_mask & age_mask].iloc[:, idx]
            
            param_data[param_name] = pd.to_numeric(data, errors='coerce').dropna()
        
        return param_data

    def plot_patient_distributions(self, gender: str, age_group: str):
        fitted_dists = self.load_fitted_distribution(gender, age_group)
        patient_data = self.get_patient_data(gender, age_group)
        
        for param_name, data in patient_data.items():
            if param_name not in fitted_dists:
                continue
                
            dist_info = fitted_dists[param_name]
            self.plot_distribution(
                data,
                dist_info,
                self.param_names[param_name],
                gender,
                age_group,
                param_name
            )

    def plot_distribution(self, param_data, dist_info, display_name, gender, age_group, param_name):
        fig, ax = plt.subplots(figsize=(12, 7))
        
        # Calculate bins using Sturges' formula
        n_bins = int(np.sqrt(len(param_data)))
        
        # Plot histogram
        n, bins, patches = ax.hist(param_data, bins=n_bins, density=True, alpha=0.4,
                                 color='lightblue', label='Patient Data')
        
        # Plot fitted distribution
        x_range = np.linspace(dist_info['range'][0], dist_info['range'][1], 100)
        orig_dist = self.get_distribution_function(dist_info['distribution'], 
                                                 dist_info['parameters'])
        ax.plot(x_range, orig_dist.pdf(x_range), 'b-', lw=2, 
                label='Fitted Distribution')
        
        # Add statistics
        stats_text = (
            f"Distribution: {dist_info['distribution']}\n"
            f"Mean: {dist_info['mean']:.1f} mm\n"
            f"Std: {dist_info['std']:.1f} mm\n"
            f"Sample Size: {len(param_data)}\n\n"
            f"Range:\n"
            f"Min: {dist_info['range'][0]:.1f} mm\n"
            f"Max: {dist_info['range'][1]:.1f} mm\n\n"
            f"Percentiles:\n"
            f"25th: {dist_info['percentiles']['25']:.1f} mm\n"
            f"75th: {dist_info['percentiles']['75']:.1f} mm"
        )
        
        ax.text(0.95, 0.95, stats_text, transform=ax.transAxes,
                bbox=dict(facecolor='white', alpha=0.8, edgecolor='gray'),
                verticalalignment='top', horizontalalignment='right',
                fontsize=9)
        
        ax.set_xlabel('Diameter (mm)')
        ax.set_ylabel('Probability Density')
        
        title = f'{display_name} Distribution\n'
        title += 'All Population' if gender == 'All' else f'Gender: {gender}'
        title += f', Age Group: {age_group}'
        ax.set_title(title)
        
        box = ax.get_position()
        ax.set_position([box.x0, box.y0, box.width * 0.8, box.height])
        ax.legend(loc='center left', bbox_to_anchor=(1, 0.5),
                 fontsize=8, framealpha=0.8)
        
        plt.tight_layout()
        
        save_dir = Path('data/processed/distribution_plots/patient_histograms')
        save_dir.mkdir(exist_ok=True, parents=True)
        plt.savefig(save_dir / f'{param_name}_{gender}_{age_group}_distribution.png',
                    dpi=300, bbox_inches='tight')
        plt.close()

# Example usage:
if __name__ == "__main__":
    analyzer = PatientDataAnalyzer(
        fitted_dist_file='data/processed/fitted_distributions.json',
        data_path='data/input/aaa_data.xlsx'
    )

    print("Generating patient data histograms...")
    
    # Generate for all gender/age group combinations
    genders = ['All', 'M', 'F']
    age_groups = ['All'] + list(AgeGroups.GROUPS.keys())
    
    for gender in genders:
        for age_group in age_groups:
            try:
                print(f"Processing: Gender={gender}, Age Group={age_group}")
                analyzer.plot_patient_distributions(gender, age_group)
            except Exception as e:
                print(f"Skipping {gender}/{age_group} due to insufficient data")
                continue
    
    print("Done!")