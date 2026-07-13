import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.spatial import ConvexHull
from pathlib import Path
from typing import Dict, List, Set, Tuple
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import DBSCAN
from scipy.stats import chi2

class OutlierDetector:
    """Class for detecting outliers using various methods"""
    
    def __init__(self, manual_outlier_ids: List[int] = None):
        self.manual_outlier_ids = set(manual_outlier_ids or [])
    
    @staticmethod
    def modified_zscore(x: np.ndarray, y: np.ndarray, threshold: float = 3.5) -> Set[int]:
        def mad(data: np.ndarray) -> float:
            median = np.median(data)
            mad_value = np.median(np.abs(data - median))
            return mad_value
        
        x_median = np.median(x)
        y_median = np.median(y)
        x_mad = mad(x)
        y_mad = mad(y)
        
        x_mod_z = 0.6745 * (x - x_median) / x_mad if x_mad > 0 else 0
        y_mod_z = 0.6745 * (y - y_median) / y_mad if y_mad > 0 else 0
        
        outlier_indices = set(np.where(
            (np.abs(x_mod_z) > threshold) | (np.abs(y_mod_z) > threshold)
        )[0])
        
        return outlier_indices
    
    @staticmethod
    def iqr_method(x: np.ndarray, y: np.ndarray, k: float = 1.5) -> Set[int]:
        def get_iqr_bounds(data: np.ndarray) -> Tuple[float, float]:
            q1, q3 = np.percentile(data, [25, 75])
            iqr = q3 - q1
            lower = q1 - k * iqr
            upper = q3 + k * iqr
            return lower, upper
        
        x_lower, x_upper = get_iqr_bounds(x)
        y_lower, y_upper = get_iqr_bounds(y)
        
        outlier_indices = set(np.where(
            (x < x_lower) | (x > x_upper) | (y < y_lower) | (y > y_upper)
        )[0])
        
        return outlier_indices
    
    @staticmethod
    def mahalanobis_distance(x: np.ndarray, y: np.ndarray, threshold_quantile: float = 0.975) -> Set[int]:
        data = np.column_stack((x, y))
        scaler = StandardScaler()
        scaled_data = scaler.fit_transform(data)
        
        mean = np.mean(scaled_data, axis=0)
        cov = np.cov(scaled_data.T)
        
        inv_covmat = np.linalg.inv(cov)
        diff = scaled_data - mean
        distances = np.sqrt(np.sum(np.dot(diff, inv_covmat) * diff, axis=1))
        
        threshold = np.sqrt(chi2.ppf(threshold_quantile, df=2))
        
        outlier_indices = set(np.where(distances > threshold)[0])
        
        return outlier_indices
    
    @staticmethod
    def dbscan_method(x: np.ndarray, y: np.ndarray, eps: float = None, min_samples: int = 5) -> Set[int]:
        data = np.column_stack((x, y))
        scaler = StandardScaler()
        scaled_data = scaler.fit_transform(data)
        
        # Adjust min_samples for small datasets
        n_samples = len(x)
        min_samples = min(min_samples, max(2, n_samples // 4))
        
        if eps is None:
            from sklearn.neighbors import NearestNeighbors
            neigh = NearestNeighbors(n_neighbors=min_samples)
            neigh.fit(scaled_data)
            distances = neigh.kneighbors(scaled_data)[0]
            eps = np.mean(distances[:, -1])
        
        dbscan = DBSCAN(eps=eps, min_samples=min_samples)
        labels = dbscan.fit_predict(scaled_data)
        
        return set(np.where(labels == -1)[0])
    
    def detect_outliers(self, 
                       x: np.ndarray, 
                       y: np.ndarray, 
                       patient_ids: np.ndarray,
                       method: str = 'all') -> Dict[str, List[int]]:
        outliers = {}
        
        if method in ['manual', 'all'] and self.manual_outlier_ids:
            manual_indices = set(np.where(np.isin(patient_ids, list(self.manual_outlier_ids)))[0])
            outliers['manual'] = [patient_ids[i] for i in manual_indices]
        
        if method in ['zscore', 'all']:
            indices = self.modified_zscore(x, y)
            outliers['zscore'] = [patient_ids[i] for i in indices]
        
        if method in ['iqr', 'all']:
            indices = self.iqr_method(x, y)
            outliers['iqr'] = [patient_ids[i] for i in indices]
        
        if method in ['mahalanobis', 'all']:
            indices = self.mahalanobis_distance(x, y)
            outliers['mahalanobis'] = [patient_ids[i] for i in indices]
        
        if method in ['dbscan', 'all']:
            indices = self.dbscan_method(x, y)
            outliers['dbscan'] = [patient_ids[i] for i in indices]
        
        return outliers

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

def get_age_grouped_data(df: pd.DataFrame, gender: str, param1_idx: int, param2_idx: int) -> Dict[str, Dict]:
    age_grouped_data = {}
    
    if gender == 'All':
        gender_mask = slice(None)
    else:
        gender_mask = (df.iloc[:, 8] == gender)
    
    ages = pd.to_numeric(df.iloc[:, 7], errors='coerce')
    patient_ids = df.index + 11
    
    for age_group, limits in AgeGroups.GROUPS.items():
        age_mask = (ages >= limits['min']) & (ages <= limits['max'])
        
        if gender == 'All':
            mask = age_mask
        else:
            mask = gender_mask & age_mask
            
        data1 = pd.to_numeric(df[mask].iloc[:, param1_idx], errors='coerce')
        data2 = pd.to_numeric(df[mask].iloc[:, param2_idx], errors='coerce')
        group_ids = patient_ids[mask]
        
        valid_mask = ~(np.isnan(data1) | np.isnan(data2))
        data1 = data1[valid_mask].values
        data2 = data2[valid_mask].values
        group_ids = group_ids[valid_mask].values
        
        if len(data1) > 0:
            age_grouped_data[age_group] = {
                'x': data1,
                'y': data2,
                'ids': group_ids,
                'n': len(data1)
            }
    
    return age_grouped_data

def plot_age_grouped_parameters_with_outliers(
    df: pd.DataFrame,
    param1: dict,
    param2: dict,
    gender: str,
    output_dir: Path,
    outlier_method: str = None,
    manual_outliers: List[int] = None
) -> None:
    plt.figure(figsize=(12, 10))
    plt.style.use('seaborn-whitegrid')
    
    colors = plt.cm.Dark2(np.linspace(0, 1, len(AgeGroups.GROUPS)))
    age_grouped_data = get_age_grouped_data(df, gender, param1['col'], param2['col'])
    
    all_points_x = []
    all_points_y = []
    all_ids = []
    all_regular_points_x = []
    all_regular_points_y = []
    
    # Initialize outlier detector if method specified
    outlier_detector = OutlierDetector(manual_outliers) if outlier_method else None
    
    # Plot each age group
    for i, (age_group, data) in enumerate(age_grouped_data.items()):
        x, y, ids = data['x'], data['y'], data['ids']
        regular_mask = np.ones(len(x), dtype=bool)  # Default all points as regular
        
        # Detect outliers if method specified
        if outlier_detector and len(x) >= 3:
            outliers = outlier_detector.detect_outliers(x, y, ids, outlier_method)
            for method, outlier_ids in outliers.items():
                outlier_mask = np.isin(ids, outlier_ids)
                regular_mask = ~outlier_mask
        
        # Plot all points (including outliers)
        plt.scatter(x, y, c=[colors[i]], alpha=0.6,
                   label=f'{age_group} (n={len(x)})',
                   marker='o', s=50)
        
        # Add patient ID annotations
        for x_val, y_val, pid in zip(x, y, ids):
            plt.annotate(f'{int(pid)}', (x_val, y_val),
                        xytext=(5, 5),
                        textcoords='offset points',
                        fontsize=8,
                        alpha=0.7)
        
        # Plot convex hull for non-outlier points only
        regular_points = np.column_stack((x[regular_mask], y[regular_mask]))
        if len(regular_points) >= 3:
            hull = ConvexHull(regular_points)
            for simplex in hull.simplices:
                plt.plot(regular_points[simplex, 0], regular_points[simplex, 1],
                        '-', color=colors[i],
                        alpha=0.3, linewidth=2)
        
        all_points_x.extend(x)
        all_points_y.extend(y)
        all_ids.extend(ids)
        all_regular_points_x.extend(x[regular_mask])
        all_regular_points_y.extend(y[regular_mask])
    
    # # Plot overall convex hull for non-outlier points only
    # if len(all_regular_points_x) >= 3:
    #     all_regular_points = np.column_stack((all_regular_points_x, all_regular_points_y))
    #     hull = ConvexHull(all_regular_points)
    #     for simplex in hull.simplices:
    #         plt.plot(all_regular_points[simplex, 0], all_regular_points[simplex, 1],
    #                 '-', color='black', alpha=0.2, linewidth=2)
    
    plt.xlabel(f'{param1["name"]} (mm)')
    plt.ylabel(f'{param2["name"]} (mm)')
    title = f'{param2["name"]} vs {param1["name"]}\n'
    title += 'All Population' if gender == 'All' else f'Gender: {gender}'
    if outlier_method:
        title += f'\nOutlier Detection: {outlier_method.upper()}'
    plt.title(title)
    
    plt.legend(bbox_to_anchor=(1.05, 1),
              loc='upper left',
              borderaxespad=0)
    
    # Add statistics
    stats_text = f'Total Patients: {len(all_points_x)}\n'
    stats_text += f'Mean {param1["name"]}: {np.mean(all_points_x):.1f}mm\n'
    stats_text += f'Mean {param2["name"]}: {np.mean(all_points_y):.1f}mm\n\n'
    stats_text += 'Age Group Statistics:\n'
    for age_group, data in age_grouped_data.items():
        stats_text += f'{age_group}: {data["n"]} patients\n'
    
    plt.text(1.05, 0.5, stats_text,
            transform=plt.gca().transAxes,
            bbox=dict(facecolor='white',
                     alpha=0.8,
                     edgecolor='gray',
                     boxstyle='round,pad=0.5'))
    
    plt.tight_layout()
    
    method_suffix = f'_{outlier_method}' if outlier_method else ''
    filename = f'{param1["name"].lower().replace(" ", "_")}_vs_{param2["name"].lower().replace(" ", "_")}_{gender}{method_suffix}.png'
    plt.savefig(output_dir / filename, dpi=300, bbox_inches='tight')
    plt.close()

def get_gender_data_for_age_group(df: pd.DataFrame, age_group: str, param1_idx: int, param2_idx: int) -> Dict[str, Dict]:
    """Get data for males and females within a specific age group with patient IDs"""
    gender_grouped_data = {}
    
    ages = pd.to_numeric(df.iloc[:, 7], errors='coerce')
    patient_ids = df.index + 11
    
    if age_group == 'All':
        age_mask = slice(None)
    else:
        limits = AgeGroups.GROUPS[age_group]
        age_mask = (ages >= limits['min']) & (ages <= limits['max'])
    
    for gender in ['M', 'F']:
        gender_mask = (df.iloc[:, 8] == gender)
        if age_group == 'All':
            mask = gender_mask
        else:
            mask = gender_mask & age_mask
            
        data1 = pd.to_numeric(df[mask].iloc[:, param1_idx], errors='coerce')
        data2 = pd.to_numeric(df[mask].iloc[:, param2_idx], errors='coerce')
        group_ids = patient_ids[mask]
        
        valid_mask = ~(np.isnan(data1) | np.isnan(data2))
        data1 = data1[valid_mask].values
        data2 = data2[valid_mask].values
        group_ids = group_ids[valid_mask].values
        
        if len(data1) > 0:
            gender_grouped_data[gender] = {
                'x': data1,
                'y': data2,
                'ids': group_ids,
                'n': len(data1)
            }
    
    return gender_grouped_data

def get_gender_comparison_stats(gender_data: Dict[str, Dict], param1_name: str, param2_name: str) -> str:
    """Generate statistics text for gender comparison plots"""
    all_x = []
    all_y = []
    
    stats_text = 'Overall Statistics:\n'
    
    for gender, data in gender_data.items():
        all_x.extend(data['x'])
        all_y.extend(data['y'])
        
        gender_label = 'Male' if gender == 'M' else 'Female'
        stats_text += f'\n{gender_label}:\n'
        stats_text += f'  n = {data["n"]}\n'
        stats_text += f'  Mean {param1_name}: {np.mean(data["x"]):.1f}mm\n'
        stats_text += f'  Mean {param2_name}: {np.mean(data["y"]):.1f}mm\n'
    
    stats_text = f'Total Patients: {len(all_x)}\n'
    stats_text += f'Overall Mean {param1_name}: {np.mean(all_x):.1f}mm\n'
    stats_text += f'Overall Mean {param2_name}: {np.mean(all_y):.1f}mm\n'
    
    return stats_text

def plot_gender_comparison_with_outliers(
    df: pd.DataFrame,
    param1: dict,
    param2: dict,
    age_group: str,
    output_dir: Path,
    outlier_method: str = None,
    manual_outliers: List[int] = None
) -> None:
    plt.figure(figsize=(12, 10))
    plt.style.use('seaborn-whitegrid')
    
    gender_colors = {
        'M': plt.cm.Dark2(0),
        'F': plt.cm.Dark2(1)
    }
    
    gender_data = get_gender_data_for_age_group(df, age_group, param1['col'], param2['col'])
    
    all_points_x = []
    all_points_y = []
    all_ids = []
    
    outlier_detector = OutlierDetector(manual_outliers) if outlier_method else None
    
    for gender, data in gender_data.items():
        x, y, ids = data['x'], data['y'], data['ids']
        regular_mask = np.ones(len(x), dtype=bool)
        
        if outlier_detector and len(x) >= 3:
            outliers = outlier_detector.detect_outliers(x, y, ids, outlier_method)
            for method, outlier_ids in outliers.items():
                outlier_mask = np.isin(ids, outlier_ids)
                regular_mask = ~outlier_mask
        
        gender_label = 'Male' if gender == 'M' else 'Female'
        plt.scatter(x, y, c=[gender_colors[gender]], alpha=0.6,
                   label=f'{gender_label} (n={len(x)})',
                   marker='o' if gender == 'M' else '^', s=50)
        
        for x_val, y_val, pid in zip(x, y, ids):
            plt.annotate(f'{int(pid)}', (x_val, y_val),
                        xytext=(5, 5),
                        textcoords='offset points',
                        fontsize=8,
                        alpha=0.7)
        
        regular_points = np.column_stack((x[regular_mask], y[regular_mask]))
        if len(regular_points) >= 3:
            hull = ConvexHull(regular_points)
            for simplex in hull.simplices:
                plt.plot(regular_points[simplex, 0], regular_points[simplex, 1],
                        '-', color=gender_colors[gender],
                        alpha=0.3, linewidth=2)
        
        all_points_x.extend(x)
        all_points_y.extend(y)
        all_ids.extend(ids)
    
    plt.xlabel(f'{param1["name"]} (mm)')
    plt.ylabel(f'{param2["name"]} (mm)')
    title = f'{param2["name"]} vs {param1["name"]}\nAge Group: {age_group}'
    if outlier_method:
        title += f'\nOutlier Detection: {outlier_method.upper()}'
    plt.title(title)
    
    plt.legend(bbox_to_anchor=(1.05, 1),
              loc='upper left',
              borderaxespad=0)
    
    stats_text = get_gender_comparison_stats(gender_data, param1["name"], param2["name"])
    plt.text(1.05, 0.5, stats_text,
            transform=plt.gca().transAxes,
            bbox=dict(facecolor='white',
                     alpha=0.8,
                     edgecolor='gray',
                     boxstyle='round,pad=0.5'))
    
    plt.tight_layout()
    method_suffix = f'_{outlier_method}' if outlier_method else ''
    filename = f'{param1["name"].lower().replace(" ", "_")}_vs_{param2["name"].lower().replace(" ", "_")}_{age_group.replace("+", "plus")}{method_suffix}.png'
    plt.savefig(output_dir / filename, dpi=300, bbox_inches='tight')
    plt.close()

def generate_plots_with_outliers(data_path: str, output_base_dir: str):
    base_path = Path(output_base_dir)
    
    # Create directories for each analysis type and outlier method
    outlier_methods = ['zscore', 'iqr', 'mahalanobis', 'dbscan', 'no_outliers']
    for method in outlier_methods:
        (base_path / 'age_groups' / method).mkdir(parents=True, exist_ok=True)
        (base_path / 'gender_comparison' / method).mkdir(parents=True, exist_ok=True)
    
    df = pd.read_excel(data_path, header=None).iloc[10:268]
    parameters = {
        'neck_diameter_1': {'col': 9, 'name': 'Neck Diameter 1'},
        'neck_diameter_2': {'col': 10, 'name': 'Neck Diameter 2'},
        'max_diameter': {'col': 13, 'name': 'Maximum Aneurysm Diameter'},
        'distal_diameter': {'col': 14, 'name': 'Distal Diameter'}
    }
    
    parameter_pairs = [
        ('neck_diameter_1', 'neck_diameter_2'),
        ('neck_diameter_2', 'max_diameter'),
        ('max_diameter', 'distal_diameter')
    ]
    
    # Generate age group plots
    for gender in ['All', 'M', 'F']:
        for param1_key, param2_key in parameter_pairs:
            # Generate plot without outlier detection
            plot_age_grouped_parameters_with_outliers(
                df,
                parameters[param1_key],
                parameters[param2_key],
                gender,
                base_path / 'age_groups' / 'no_outliers'
            )
            
            # Generate plots with outlier detection methods
            for method in outlier_methods[:-1]:
                plot_age_grouped_parameters_with_outliers(
                    df,
                    parameters[param1_key],
                    parameters[param2_key],
                    gender,
                    base_path / 'age_groups' / method,
                    outlier_method=method
                )
    
    # Generate gender comparison plots
    for age_group in list(AgeGroups.GROUPS.keys()) + ['All']:
        for param1_key, param2_key in parameter_pairs:
            # Generate plot without outlier detection
            plot_gender_comparison_with_outliers(
                df,
                parameters[param1_key],
                parameters[param2_key],
                age_group,
                base_path / 'gender_comparison' / 'no_outliers'
            )
            
            # Generate plots with outlier detection methods
            for method in outlier_methods[:-1]:
                plot_gender_comparison_with_outliers(
                    df,
                    parameters[param1_key],
                    parameters[param2_key],
                    age_group,
                    base_path / 'gender_comparison' / method,
                    outlier_method=method
                )

def generate_outlier_summary(data_path: str, output_dir: str):
    """Generate summary reports of outliers detected by different methods"""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    df = pd.read_excel(data_path, header=None).iloc[10:268]
    
    parameters = {
        'neck_diameter_1': {'col': 9, 'name': 'Neck Diameter 1'},
        'neck_diameter_2': {'col': 10, 'name': 'Neck Diameter 2'},
        'max_diameter': {'col': 13, 'name': 'Maximum Aneurysm Diameter'},
        'distal_diameter': {'col': 14, 'name': 'Distal Diameter'}
    }
    
    parameter_pairs = [
        ('neck_diameter_1', 'neck_diameter_2'),
        ('neck_diameter_2', 'max_diameter'),
        ('max_diameter', 'distal_diameter')
    ]
    
    # Initialize outlier detector
    detector = OutlierDetector()
    
    print("\nGenerating outlier summary reports...")
    
    # Create summary report for each parameter pair
    for param1_key, param2_key in parameter_pairs:
        print(f"\nAnalyzing {param1_key} vs {param2_key}")
        
        report_lines = [
            f"Outlier Analysis Report: {parameters[param2_key]['name']} vs {parameters[param1_key]['name']}",
            "=" * 80,
            ""
        ]
        
        for gender in ['All', 'M', 'F']:
            report_lines.extend([
                f"Gender: {gender}",
                "-" * 40
            ])
            
            # Get data for this gender
            if gender == 'All':
                gender_mask = slice(None)
            else:
                gender_mask = (df.iloc[:, 8] == gender)
            
            data1 = pd.to_numeric(df[gender_mask].iloc[:, parameters[param1_key]['col']], errors='coerce')
            data2 = pd.to_numeric(df[gender_mask].iloc[:, parameters[param2_key]['col']], errors='coerce')
            patient_ids = df[gender_mask].index + 11
            
            # Remove NaN values
            valid_mask = ~(np.isnan(data1) | np.isnan(data2))
            data1 = data1[valid_mask].values
            data2 = data2[valid_mask].values
            patient_ids = patient_ids[valid_mask].values
            
            if len(data1) >= 3:  # Need at least 3 points for meaningful outlier detection
                # Detect outliers using all methods
                outliers = detector.detect_outliers(data1, data2, patient_ids, 'all')
                
                # Report findings for each method
                for method, outlier_ids in outliers.items():
                    report_lines.extend([
                        f"\n{method.upper()} Method:",
                        f"Number of outliers detected: {len(outlier_ids)}",
                        "Patient IDs: " + ", ".join(map(str, sorted(outlier_ids)))
                    ])
                
                # Find points detected by multiple methods
                all_outliers = set()
                for ids in outliers.values():
                    all_outliers.update(ids)
                
                report_lines.extend([
                    "\nSummary:",
                    f"Total unique outliers: {len(all_outliers)}",
                    "Patients detected by multiple methods:"
                ])
                
                for patient_id in sorted(all_outliers):
                    methods = [method for method, ids in outliers.items() if patient_id in ids]
                    if len(methods) > 1:
                        report_lines.append(f"Patient {patient_id}: {', '.join(methods)}")
            
            report_lines.extend(["", ""])
        
        # Save report
        report_name = f"outlier_report_{param1_key}_vs_{param2_key}.txt"
        with open(output_path / report_name, 'w') as f:
            f.write('\n'.join(report_lines))

def generate_manual_outlier_plots(data_path: str, output_base_dir: str, manual_outliers: List[int]):
    base_path = Path(output_base_dir)
    
    # Create directory for manual outliers
    (base_path / 'age_groups' / 'manual').mkdir(parents=True, exist_ok=True)
    (base_path / 'gender_comparison' / 'manual').mkdir(parents=True, exist_ok=True)
    
    df = pd.read_excel(data_path, header=None).iloc[10:268]
    parameters = {
        'neck_diameter_1': {'col': 9, 'name': 'Neck Diameter 1'},
        'neck_diameter_2': {'col': 10, 'name': 'Neck Diameter 2'},
        'max_diameter': {'col': 13, 'name': 'Maximum Aneurysm Diameter'},
        'distal_diameter': {'col': 14, 'name': 'Distal Diameter'}
    }
    
    parameter_pairs = [
        ('neck_diameter_1', 'neck_diameter_2'),
        ('neck_diameter_2', 'max_diameter'),
        ('max_diameter', 'distal_diameter')
    ]
    
    # Generate age group plots
    for gender in ['All', 'M', 'F']:
        for param1_key, param2_key in parameter_pairs:
            plot_age_grouped_parameters_with_outliers(
                df,
                parameters[param1_key],
                parameters[param2_key],
                gender,
                base_path / 'age_groups' / 'manual',
                outlier_method='manual',
                manual_outliers=manual_outliers
            )
    
    # Generate gender comparison plots
    for age_group in list(AgeGroups.GROUPS.keys()) + ['All']:
        for param1_key, param2_key in parameter_pairs:
            plot_gender_comparison_with_outliers(
                df,
                parameters[param1_key],
                parameters[param2_key],
                age_group,
                base_path / 'gender_comparison' / 'manual',
                outlier_method='manual',
                manual_outliers=manual_outliers
            )


def plot_clean_convex_hulls(
    df: pd.DataFrame,
    param1: dict,
    param2: dict,
    output_dir: Path,
    plot_type: str = 'age_groups',
    group: str = 'All'
) -> None:
    plt.figure(figsize=(10, 8))
    plt.style.use('seaborn-whitegrid')
    
    age_colors = plt.cm.Dark2(np.linspace(0, 1, len(AgeGroups.GROUPS)))
    gender_colors = {
        'M': plt.cm.Dark2(0),
        'F': plt.cm.Dark2(1)
    }
    
    if plot_type == 'age_groups':
        data = get_age_grouped_data(df, group, param1['col'], param2['col'])
        colors = age_colors
    else:
        data = get_gender_data_for_age_group(df, group, param1['col'], param2['col'])
        colors = gender_colors
    
    for i, (group_name, group_data) in enumerate(data.items()):
        x, y = group_data['x'], group_data['y']
        
        if len(x) >= 3:
            points = np.column_stack((x, y))
            hull = ConvexHull(points)
            hull_points = points[hull.vertices]
            hull_points = np.vstack((hull_points, hull_points[0]))
            
            color = colors[group_name] if isinstance(colors, dict) else colors[i]
            plt.fill(hull_points[:, 0], hull_points[:, 1],
                    color=color, alpha=0.3,
                    label=f'{group_name} (n={len(x)})')
            
            plt.plot(hull_points[:, 0], hull_points[:, 1],
                    '-', color=color, alpha=0.8, linewidth=2)
    
    plt.xlabel(f'{param1["name"]} (mm)')
    plt.ylabel(f'{param2["name"]} (mm)')
    
    if plot_type == 'age_groups':
        title = f'{param2["name"]} vs {param1["name"]}\n'
        title += 'All Population' if group == 'All' else f'Gender: {group}'
    else:
        title = f'{param2["name"]} vs {param1["name"]}\nAge Group: {group}'
    plt.title(title)
    
    plt.legend(bbox_to_anchor=(1.05, 1),
              loc='upper left',
              borderaxespad=0)
    
    plt.tight_layout()
    
    filename = f'clean_{param1["name"].lower().replace(" ", "_")}_vs_'
    filename += f'{param2["name"].lower().replace(" ", "_")}_{group}.png'
    plt.savefig(output_dir / filename, dpi=300, bbox_inches='tight')
    plt.close()


def generate_clean_plots(data_path: str, output_base_dir: str):
    """Generate all clean visualization plots"""
    base_path = Path(output_base_dir) / 'clean_plots'
    base_path.mkdir(parents=True, exist_ok=True)
    
    (base_path / 'age_groups').mkdir(exist_ok=True)
    (base_path / 'gender_comparison').mkdir(exist_ok=True)
    
    df = pd.read_excel(data_path, header=None).iloc[10:268]
    parameters = {
        'neck_diameter_1': {'col': 9, 'name': 'Neck Diameter 1'},
        'neck_diameter_2': {'col': 10, 'name': 'Neck Diameter 2'},
        'max_diameter': {'col': 13, 'name': 'Maximum Aneurysm Diameter'},
        'distal_diameter': {'col': 14, 'name': 'Distal Diameter'}
    }
    
    parameter_pairs = [
        ('neck_diameter_1', 'neck_diameter_2'),
        ('neck_diameter_2', 'max_diameter'),
        ('max_diameter', 'distal_diameter')
    ]
    
    # Generate age group plots
    for gender in ['All', 'M', 'F']:
        for param1_key, param2_key in parameter_pairs:
            plot_clean_convex_hulls(
                df,
                parameters[param1_key],
                parameters[param2_key],
                base_path / 'age_groups',
                'age_groups',
                gender
            )
    
    # Generate gender comparison plots
    for age_group in list(AgeGroups.GROUPS.keys()) + ['All']:
        for param1_key, param2_key in parameter_pairs:
            plot_clean_convex_hulls(
                df,
                parameters[param1_key],
                parameters[param2_key],
                base_path / 'gender_comparison',
                'gender_comparison',
                age_group
            )

def plot_clean_convex_hulls_with_outliers(
    df: pd.DataFrame,
    param1: dict,
    param2: dict,
    output_dir: Path,
    plot_type: str = 'age_groups',
    group: str = 'All',
    outlier_method: str = None,
    manual_outliers: List[int] = None
) -> None:
    plt.figure(figsize=(10, 8))
    plt.style.use('seaborn-whitegrid')
    
    age_colors = plt.cm.Dark2(np.linspace(0, 1, len(AgeGroups.GROUPS)))
    gender_colors = {
        'M': plt.cm.Dark2(0),
        'F': plt.cm.Dark2(1)
    }
    
    if plot_type == 'age_groups':
        data = get_age_grouped_data(df, group, param1['col'], param2['col'])
        colors = age_colors
    else:
        data = get_gender_data_for_age_group(df, group, param1['col'], param2['col'])
        colors = gender_colors
    
    # Initialize outlier detector if method specified
    outlier_detector = OutlierDetector(manual_outliers) if (outlier_method or manual_outliers) else None
    
    for i, (group_name, group_data) in enumerate(data.items()):
        x, y, ids = group_data['x'], group_data['y'], group_data['ids']
        regular_mask = np.ones(len(x), dtype=bool)
        
        # Detect outliers if method specified
        if outlier_detector and len(x) >= 3:
            outliers = outlier_detector.detect_outliers(x, y, ids, outlier_method or 'manual')
            for method, outlier_ids in outliers.items():
                outlier_mask = np.isin(ids, outlier_ids)
                regular_mask = ~outlier_mask
        
        # Get non-outlier points
        regular_points = np.column_stack((x[regular_mask], y[regular_mask]))
        
        if len(regular_points) >= 3:
            hull = ConvexHull(regular_points)
            hull_points = regular_points[hull.vertices]
            hull_points = np.vstack((hull_points, hull_points[0]))
            
            color = colors[group_name] if isinstance(colors, dict) else colors[i]
            plt.fill(hull_points[:, 0], hull_points[:, 1],
                    color=color, alpha=0.3,
                    label=f'{group_name} (n={len(regular_points)})')
            
            plt.plot(hull_points[:, 0], hull_points[:, 1],
                    '-', color=color, alpha=0.8, linewidth=2)
    
    plt.xlabel(f'{param1["name"]} (mm)')
    plt.ylabel(f'{param2["name"]} (mm)')
    
    if plot_type == 'age_groups':
        title = f'{param2["name"]} vs {param1["name"]}\n'
        title += 'All Population' if group == 'All' else f'Gender: {group}'
    else:
        title = f'{param2["name"]} vs {param1["name"]}\nAge Group: {group}'
        
    if outlier_method:
        title += f'\nOutlier Detection: {outlier_method.upper()}'
    elif manual_outliers:
        title += '\nManual Outliers Removed'
    
    plt.title(title)
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', borderaxespad=0)
    plt.tight_layout()
    
    method_suffix = f'_{outlier_method}' if outlier_method else '_manual' if manual_outliers else ''
    filename = f'clean_{param1["name"].lower().replace(" ", "_")}_vs_'
    filename += f'{param2["name"].lower().replace(" ", "_")}_{group}{method_suffix}.png'
    plt.savefig(output_dir / filename, dpi=300, bbox_inches='tight')
    plt.close()

def generate_clean_plots_with_outliers(data_path: str, output_base_dir: str, manual_outliers: List[int] = None):
    """Generate clean visualization plots for all outlier detection methods"""
    base_path = Path(output_base_dir) / 'clean_plots'
    
    # Create directories for each outlier method
    outlier_methods = ['zscore', 'iqr', 'mahalanobis', 'dbscan', 'manual', 'no_outliers']
    for method in outlier_methods:
        (base_path / 'age_groups' / method).mkdir(parents=True, exist_ok=True)
        (base_path / 'gender_comparison' / method).mkdir(parents=True, exist_ok=True)
    
    df = pd.read_excel(data_path, header=None).iloc[10:268]
    parameters = {
        'neck_diameter_1': {'col': 9, 'name': 'Neck Diameter 1'},
        'neck_diameter_2': {'col': 10, 'name': 'Neck Diameter 2'},
        'max_diameter': {'col': 13, 'name': 'Maximum Aneurysm Diameter'},
        'distal_diameter': {'col': 14, 'name': 'Distal Diameter'}
    }
    
    parameter_pairs = [
        ('neck_diameter_1', 'neck_diameter_2'),
        ('neck_diameter_2', 'max_diameter'),
        ('max_diameter', 'distal_diameter')
    ]
    
    # Generate plots for each outlier method
    for method in outlier_methods[:-1]:  # Exclude 'no_outliers'
        print(f"\nGenerating clean plots with {method} outlier detection...")
        
        # Age group plots
        for gender in ['All', 'M', 'F']:
            for param1_key, param2_key in parameter_pairs:
                if method == 'manual':
                    plot_clean_convex_hulls_with_outliers(
                        df, parameters[param1_key], parameters[param2_key],
                        base_path / 'age_groups' / method,
                        'age_groups', gender,
                        manual_outliers=manual_outliers
                    )
                else:
                    plot_clean_convex_hulls_with_outliers(
                        df, parameters[param1_key], parameters[param2_key],
                        base_path / 'age_groups' / method,
                        'age_groups', gender,
                        outlier_method=method
                    )
        
        # Gender comparison plots
        for age_group in list(AgeGroups.GROUPS.keys()) + ['All']:
            for param1_key, param2_key in parameter_pairs:
                if method == 'manual':
                    plot_clean_convex_hulls_with_outliers(
                        df, parameters[param1_key], parameters[param2_key],
                        base_path / 'gender_comparison' / method,
                        'gender_comparison', age_group,
                        manual_outliers=manual_outliers
                    )
                else:
                    plot_clean_convex_hulls_with_outliers(
                        df, parameters[param1_key], parameters[param2_key],
                        base_path / 'gender_comparison' / method,
                        'gender_comparison', age_group,
                        outlier_method=method
                    )
    
    # Generate plots without outlier detection
    print("\nGenerating clean plots without outlier detection...")
    for gender in ['All', 'M', 'F']:
        for param1_key, param2_key in parameter_pairs:
            plot_clean_convex_hulls_with_outliers(
                df, parameters[param1_key], parameters[param2_key],
                base_path / 'age_groups' / 'no_outliers',
                'age_groups', gender
            )
    
    for age_group in list(AgeGroups.GROUPS.keys()) + ['All']:
        for param1_key, param2_key in parameter_pairs:
            plot_clean_convex_hulls_with_outliers(
                df, parameters[param1_key], parameters[param2_key],
                base_path / 'gender_comparison' / 'no_outliers',
                'gender_comparison', age_group
            )

if __name__ == "__main__":
    print("Starting comprehensive patient data visualization with outlier detection...")
    
    # Define paths
    data_path = "data/input/aaa_data.xlsx"
    output_base_dir = "data/processed/parameter_plots"
    report_dir = "data/processed/outlier_reports"

    # Define your manual outliers
    manual_outliers = [163, 109,
                       71,
                       78,
                       42,40,72]  # Replace with actual outlier IDs
    
    # Generate plots with different outlier detection methods
    generate_plots_with_outliers(data_path, output_base_dir)
    
    # Generate outlier summary reports
    generate_outlier_summary(data_path, report_dir)

    # Generate only manual outlier plots
    generate_manual_outlier_plots(data_path, output_base_dir, manual_outliers)

    # Generate clean plots with all outlier detection methods
    generate_clean_plots_with_outliers(data_path, output_base_dir, manual_outliers)
    
    print("\nVisualization complete. Outputs saved to:")
    print(f"- Plots: {output_base_dir}")
    print(f"- Outlier reports: {report_dir}")
    print("\nGenerated visualizations include:")
    print("1. Base plots without outlier detection")
    print("2. Plots with outliers detected using:")
    print("   - Modified Z-score method")
    print("   - IQR method")
    print("   - Mahalanobis distance")
    print("   - DBSCAN clustering")
    print("3. Detailed outlier analysis reports")