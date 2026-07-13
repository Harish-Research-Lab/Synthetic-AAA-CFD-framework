import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import json
from scipy import stats
import pandas as pd
from typing import Dict, Optional

class AgeGroups:
    GROUPS = {
        '<50': {'min': 0, 'max': 49},
        '50-59': {'min': 50, 'max': 59},
        '60-69': {'min': 60, 'max': 69},
        '70-79': {'min': 70, 'max': 79},
        '80+': {'min': 80, 'max': float('inf')}
    }
    
    @classmethod
    def get_group(cls, age: int) -> str:
        for group, limits in cls.GROUPS.items():
            if limits['min'] <= age <= limits['max']:
                return group
        return 'unknown'


class ModifiedPatientDataAnalyzer:
    def __init__(self, fitted_dist_file: str, data_path: str):
        self.fitted_dist_file = fitted_dist_file
        self.df = pd.read_excel(data_path, header=None).iloc[10:268]
        self.setup_parameters()
        self.setup_style()
        self.global_ranges = self.compute_global_ranges()
        
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
        
    def setup_style(self, scale_factor=0.5):
        plt.style.use('seaborn-white')
        base_font_size = 10 * scale_factor
        plt.rcParams.update({
            'font.family': 'serif',
            'font.size': base_font_size,
            'axes.labelsize': base_font_size * 1.2,
            'axes.titlesize': base_font_size * 1.4,
            'legend.fontsize': base_font_size,
            'axes.grid': False
        })

    def compute_global_ranges(self) -> Dict[str, Dict[str, tuple]]:
        ranges = {}
        for param_name, idx in self.param_indices.items():
            data = pd.to_numeric(self.df.iloc[:, idx], errors='coerce').dropna()
            padding = 0.05
            min_val = data.min() * (1 - padding)
            max_val = data.max() * (1 + padding)
            min_val = np.floor(min_val / 5) * 5
            max_val = np.ceil(max_val / 5) * 5
            ranges[param_name] = {'min': min_val, 'max': max_val}
        return ranges

    def load_fitted_distribution(self, gender: str, age_group: str) -> Optional[Dict]:
        try:
            with open(self.fitted_dist_file, 'r') as f:
                data = json.load(f)
            return data['demographics'][gender][age_group]
        except (KeyError, FileNotFoundError):
            return None

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

    def create_standalone_legend(self, output_dir: Path, gender: str, param_name: str, has_fitted: bool):
        plt.figure(figsize=(6, 1))
        ax = plt.gca()
        ax.axis('off')

        handles = []
        handles.append(plt.Rectangle((0, 0), 1, 1, fc='lightblue', alpha=0.4, label='Patient Data'))
        if has_fitted:
            handles.append(plt.Line2D([0], [0], color='blue', lw=2, label='Fitted Distribution'))

        legend = plt.legend(handles=handles,
                          loc='center',
                          ncol=2 if has_fitted else 1,
                          fontsize=8,
                          frameon=True,
                          framealpha=1,
                          fancybox=True,
                          shadow=True)

        legend.get_frame().set_facecolor('white')
        plt.savefig(output_dir / f'legend_{param_name}_{gender}.png',
                   dpi=600,
                   bbox_inches='tight',
                   transparent=True)
        plt.close()

    def plot_patient_distributions(self, gender: str, age_group: str, scale_factor: float = 0.5, fixed_y_ranges: bool = True):
        fitted_dists = self.load_fitted_distribution(gender, age_group)
        patient_data = self.get_patient_data(gender, age_group)
        save_dir = Path('data/processed/distribution_plots/patient_histograms_modified')
        save_dir.mkdir(exist_ok=True, parents=True)
        
        for param_name, data in patient_data.items():
            if len(data) > 0:
                dist_info = fitted_dists.get(param_name) if fitted_dists else None
                self.plot_distribution(
                    data, dist_info, self.param_names[param_name],
                    gender, age_group, param_name, save_dir,
                    scale_factor, fixed_y_ranges
                )

    def plot_distribution(self, param_data, dist_info, display_name, gender,
                        age_group, param_name, save_dir, scale_factor, fixed_y_ranges=True):
        self.setup_style(scale_factor)
        fig = plt.figure(figsize=(4*scale_factor, 3*scale_factor))
        
        ax = plt.gca()
        for spine in ax.spines.values():
            spine.set_linewidth(0.5)
        
        global_range = self.global_ranges[param_name]
        n_bins = 20
        bins = np.linspace(global_range['min'], global_range['max'], n_bins)
        
        plt.hist(param_data, bins=bins, density=True, alpha=0.4, color='lightblue')
        
        if dist_info:
            x_range = np.linspace(dist_info['range'][0], dist_info['range'][1], 100)
            orig_dist = self.get_distribution_function(dist_info['distribution'], dist_info['parameters'])
            plt.plot(x_range, orig_dist.pdf(x_range), 'b-', lw=0.3)
        
        x_min, x_max = global_range['min'], global_range['max']
        ax.set_xlim(x_min, x_max)
        major_ticks = np.arange(int(x_min), int(x_max) + 1, 5)
        ax.set_xticks(major_ticks)
        ax.tick_params(which='major', length=4, width=0.5, direction='out')

        if fixed_y_ranges:
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
        
        plt.xlabel(f'{self.param_names[param_name]} (mm)')
        plt.ylabel('Probability Density')
        plt.tight_layout()
        
        self.create_standalone_legend(save_dir, gender, param_name, dist_info is not None)
        filename = f'{param_name}_{gender}_{age_group}_distribution{"_fixed" if fixed_y_ranges else ""}.png'
        plt.savefig(save_dir / filename, dpi=600, bbox_inches='tight')
        plt.close()

if __name__ == "__main__":
    analyzer = ModifiedPatientDataAnalyzer(
        fitted_dist_file='data/processed/fitted_distributions.json',
        data_path='data/input/aaa_data.xlsx'
    )
    
    genders = ['All', 'M', 'F']
    age_groups = ['All'] + list(AgeGroups.GROUPS.keys())
    
    for gender in genders:
        for age_group in age_groups:
            try:
                print(f"Processing: Gender={gender}, Age Group={age_group}")
                analyzer.plot_patient_distributions(gender, age_group,fixed_y_ranges=True)
            except Exception as e:
                print(f"Skipping {gender}/{age_group} due to insufficient data")
                continue