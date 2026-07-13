import numpy as np
import matplotlib.pyplot as plt
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


class QQPlotAnalyzer:
    def __init__(self, fitted_dist_file: str, data_path: str):
        self.fitted_dist_file = fitted_dist_file
        self.df = pd.read_excel(data_path, header=None).iloc[10:268]
        self.setup_parameters()

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

    def create_standalone_legend(self, output_dir: Path, gender: str, param_name: str):
        plt.figure(figsize=(6, 1))
        ax = plt.gca()
        ax.axis('off')

        handles = [
            plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='blue',
                       markersize=4, alpha=0.6, label='Sample Quantiles'),
            plt.Line2D([0], [0], color='red', lw=1.5, linestyle='--', label='Reference Line')
        ]

        legend = plt.legend(handles=handles,
                            loc='center',
                            ncol=2,
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

    def plot_qq(self, param_data, dist_info, display_name, gender,
                age_group, param_name, save_dir, scale_factor):
        self.setup_style(scale_factor)
        fig = plt.figure(figsize=(4 * scale_factor, 3 * scale_factor))

        ax = plt.gca()
        for spine in ax.spines.values():
            spine.set_linewidth(0.5)

        sorted_data = np.sort(param_data.values)
        n = len(sorted_data)

        # Plotting positions (Hazen formula)
        probabilities = (np.arange(1, n + 1) - 0.5) / n

        # Theoretical quantiles from the fitted distribution
        fitted_dist = self.get_distribution_function(
            dist_info['distribution'], dist_info['parameters'])
        theoretical_quantiles = fitted_dist.ppf(probabilities)

        # Scatter plot of quantiles
        ax.scatter(theoretical_quantiles, sorted_data, s=3 * scale_factor,
                   color='blue', alpha=0.6, linewidths=0, zorder=2)

        # Reference line (y = x)
        q_min = min(theoretical_quantiles.min(), sorted_data.min())
        q_max = max(theoretical_quantiles.max(), sorted_data.max())
        ax.plot([q_min, q_max], [q_min, q_max], 'r--', lw=0.3, zorder=1)

        ax.set_xlabel(f'Theoretical Quantiles (mm)')
        ax.set_ylabel(f'Sample Quantiles (mm)')

        ax.tick_params(which='major', length=4, width=0.5, direction='out')

        plt.tight_layout()

        self.create_standalone_legend(save_dir, gender, param_name)
        filename = f'{param_name}_{gender}_{age_group}_qq.png'
        plt.savefig(save_dir / filename, dpi=600, bbox_inches='tight')
        plt.close()

    def plot_qq_distributions(self, gender: str, age_group: str, scale_factor: float = 0.5):
        fitted_dists = self.load_fitted_distribution(gender, age_group)
        patient_data = self.get_patient_data(gender, age_group)
        save_dir = Path(__file__).resolve().parent / 'processed/distribution_plots/qq_plots'
        save_dir.mkdir(exist_ok=True, parents=True)

        for param_name, data in patient_data.items():
            dist_info = fitted_dists.get(param_name) if fitted_dists else None
            if len(data) < 10 or dist_info is None:
                print(f"  Skipping {param_name} for {gender}/{age_group}: "
                      f"insufficient data or no fitted distribution")
                continue

            self.plot_qq(
                data, dist_info, self.param_names[param_name],
                gender, age_group, param_name, save_dir, scale_factor
            )


if __name__ == "__main__":
    script_dir = Path(__file__).resolve().parent
    analyzer = QQPlotAnalyzer(
        fitted_dist_file=str(script_dir / 'processed/fitted_distributions.json'),
        data_path=str(script_dir / 'input/aaa_data.xlsx')
    )

    genders = ['All', 'M', 'F']
    age_groups = ['All'] + list(AgeGroups.GROUPS.keys())

    for gender in genders:
        for age_group in age_groups:
            try:
                print(f"Processing: Gender={gender}, Age Group={age_group}")
                analyzer.plot_qq_distributions(gender, age_group)
            except Exception as e:
                print(f"Skipping {gender}/{age_group}: {e}")
                continue
