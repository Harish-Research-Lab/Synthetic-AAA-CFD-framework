import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import json
from typing import Dict, List, Optional, Tuple
import pandas as pd
import re

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

def filter_data(df: pd.DataFrame, gender: str, age_group: str) -> pd.DataFrame:
    ages = pd.to_numeric(df.iloc[:, 7], errors='coerce')
    age_groups = ages.apply(lambda x: AgeGroups.get_group(x) if not pd.isna(x) else 'unknown')
    
    gender_mask = (df.iloc[:, 8] == gender)
    
    if age_group == 'All':
        filtered_df = df[gender_mask]
    else:
        age_group_limits = AgeGroups.GROUPS[age_group]
        age_mask = (ages >= age_group_limits['min']) & (ages <= age_group_limits['max'])
        filtered_df = df[gender_mask & age_mask]
    
    return filtered_df

def load_geometry_params(case_dir: Path) -> Dict:
    params_file = case_dir / 'parameters' / 'geometry_params.json'
    if params_file.exists():
        with open(params_file, 'r') as f:
            return json.load(f)
    return None

def load_case_measurements(case_dir: Path, is_morphed: bool = False) -> Dict:
    """Load measurements from appropriate JSON file"""
    if is_morphed:
        params_file = case_dir / 'parameters' / 'validation_results.json'
        try:
            with open(params_file, 'r') as f:
                data = json.load(f)
                return {
                    'neck_diameter_1': data['measurements']['Neck 1'],
                    'neck_diameter_2': data['measurements']['Neck 2'],
                    'max_diameter': data['measurements']['Maximum Aneurysm'],
                    'distal_diameter': data['measurements']['Distal']
                }
        except (FileNotFoundError, KeyError):
            return None
    else:
        params_file = case_dir / 'parameters' / 'geometry_params.json'
        try:
            with open(params_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return None


def collect_case_data(ofcases_dir: Path, gender: str, age_group: str, custom_suffix: str = 'sim') -> Dict[str, List[Dict]]:
    case_data = {
        'statistical': [],
        'morphed': []
    }
    
    # Construct the nested folder path
    nested_folder = ofcases_dir / f"{gender}_{age_group}_{custom_suffix}_all_cases"
    
    if not nested_folder.exists():
        print(f"Warning: Folder not found: {nested_folder}")
        return case_data

    # Escape plus sign if present in age_group
    age_group_pattern = age_group.replace('+', r'\+')
    
    # Update patterns for base and morphed cases
    base_pattern = f"AAA_{gender}_{age_group_pattern}_stat_[0-9]+_{custom_suffix}$"
    morph_pattern = f"AAA_{gender}_{age_group_pattern}_stat_[0-9]+_{custom_suffix}_morph_[0-9]+"
    
    for case_dir in nested_folder.iterdir():
        if not case_dir.is_dir():
            continue
            
        case_name = case_dir.name

        stat_match = re.search(r'stat_(\d+)', case_name)
        if not stat_match:
            continue
            
        stat_num = int(stat_match.group(1))
        
        if re.match(morph_pattern, case_name):
            morph_match = re.search(r'morph_(\d+)', case_name)
            if morph_match:
                params = load_case_measurements(case_dir, is_morphed=True)
                if params:
                    params['stat_variant'] = stat_num
                    params['morph_variant'] = int(morph_match.group(1))
                    case_data['morphed'].append(params)
                        
        elif re.match(base_pattern, case_name): 
            params = load_case_measurements(case_dir, is_morphed=False)
            if params:
                params['stat_variant'] = stat_num
                case_data['statistical'].append(params)
    
    return case_data


# Modify is_point_inside_hull to return a clear bool
def is_point_inside_hull(point: np.ndarray, hull_points: np.ndarray) -> bool:
    """Test if point is inside convex hull using ray casting algorithm"""
    def is_left(p0, p1, p2):
        return ((p1[0] - p0[0]) * (p2[1] - p0[1]) - 
                (p2[0] - p0[0]) * (p1[1] - p0[1]))
    
    wn = 0  # winding number
    
    for i in range(len(hull_points)-1):
        if hull_points[i][1] <= point[1]:
            if hull_points[i+1][1] > point[1]:
                if is_left(hull_points[i], hull_points[i+1], point) > 0:
                    wn += 1
        else:
            if hull_points[i+1][1] <= point[1]:
                if is_left(hull_points[i], hull_points[i+1], point) < 0:
                    wn -= 1
    return wn != 0

def find_interior_cases(
    case_data: Dict[str, List[Dict]], 
    hull_points: np.ndarray,
    param1_key: str,
    param2_key: str,
    gender: str,
    age_group: str,
    outlier_method: str,
    custom_suffix: str = 'sim'  # Add custom_suffix parameter with default
) -> List[str]:
    """
    Find cases that lie inside the convex hull
    """
    interior_cases = []
    
    for p in case_data['morphed']:
        point = np.array([p[param1_key], p[param2_key]])
        if is_point_inside_hull(point, hull_points):
            case_name = f"AAA_{gender}_{age_group}_stat_{p['stat_variant']}_{custom_suffix}_morph_{p['morph_variant']}"
            interior_cases.append(case_name)
    
    return sorted(interior_cases)

def write_interior_report(interior_cases: List[str], output_file: Path) -> None:
    """
    Write report of cases that are interior to all parameter pair hulls
    
    Args:
        interior_cases: List of case names that are interior to all hulls
        output_file: Path to output file
    """
    with open(output_file, 'w') as f:
        f.write("Cases interior to all parameter pair convex hulls\n")
        f.write("=" * 45 + "\n\n")
        if interior_cases:
            f.write("Interior cases:\n")
            for case in interior_cases:
                f.write(f"- {case}\n")
            f.write(f"\nTotal interior cases: {len(interior_cases)}")
        else:
            f.write("No cases found that are interior to all parameter pair hulls")

def find_universal_interior_set(
    case_data: Dict[str, List[Dict]],
    hull_data: List[Dict],
    parameters: Dict,
    parameter_pairs: List[Tuple[str, str]], 
    gender: str,
    age_group: str,
    outlier_method: str,
    custom_suffix: str = 'sim'  # Add custom_suffix parameter
) -> List[str]:
    """
    Find cases that are interior to all parameter pair convex hulls
    """
    pair_interior_cases = []
    
    for param1_key, param2_key in parameter_pairs:
        matching_hull = next(
            (h for h in hull_data if 
             h['gender'] == gender and
             h['age_group'] == age_group and
             h['outlier_method'] == outlier_method and
             h['parameter_comparison'] == f"{parameters[param1_key]['name']} vs {parameters[param2_key]['name']}"),
            None
        )
        
        if matching_hull:
            hull_points = np.array(matching_hull['convex_hull_points'])
            hull_points = np.vstack((hull_points, hull_points[0]))
            
            interior_cases = find_interior_cases(
                case_data,
                hull_points,
                parameters[param1_key]['key'],
                parameters[param2_key]['key'],
                gender,
                age_group,
                outlier_method,
                custom_suffix  # Pass the custom_suffix
            )
            pair_interior_cases.append(set(interior_cases))
    
    if pair_interior_cases:
        universal_interior = set.intersection(*pair_interior_cases)
        return sorted(list(universal_interior))
    return []

def setup_plotting_style(scale_factor=1.0):
    """Configure plotting style with scaling"""
    plt.style.use('seaborn-white')
    base_font_size = 14 * scale_factor
    plt.rcParams.update({
        'font.family': 'serif',
        'font.size': base_font_size,
        'axes.labelsize': base_font_size * 1.2,
        'axes.titlesize': base_font_size * 1.4,
        'legend.fontsize': base_font_size,
        'axes.grid': False,
        'xtick.labelsize': base_font_size * 1.2,  # Added for tick labels
        'ytick.labelsize': base_font_size * 1.2   # Added for tick labels
    })

def plot_universal_interior_set(
    case_data: Dict[str, List[Dict]],
    param1: str,
    param2: str,
    param1_key: str,
    param2_key: str,
    gender: str,
    age_group: str,
    output_dir: Path,
    hull_data: List[Dict], 
    interior_cases: List[str],
    outlier_method: str = 'no_outliers',
    custom_suffix: str = 'sim',
    scale_factor: float = 0.65,  # Add scale_factor
    fixed_ranges: bool = True  # Add fixed_ranges
) -> None:
    fig = plt.figure(figsize=(6*scale_factor, 6*scale_factor))  # Match other plot dimensions
    
    # Define color scheme
    base_colors = plt.cm.Dark2(np.linspace(0, 1, 8))
    
    matching_hull = next(
        (h for h in hull_data if 
         h['gender'] == gender and
         h['age_group'] == age_group and
         h['outlier_method'] == outlier_method and
         h['parameter_comparison'] == f"{param1} vs {param2}"),
        None
    )
    
    ax = plt.gca()
    for spine in ax.spines.values():
        spine.set_linewidth(1)

    if matching_hull:
        hull_points = np.array(matching_hull['convex_hull_points'])
        hull_points = np.vstack((hull_points, hull_points[0]))
        plt.plot(hull_points[:, 0], hull_points[:, 1], 
                'r-', alpha=0.7, linewidth=1, 
                label=f'Patient Data Boundary (n={matching_hull["group_size"]})')
    
    interior_stats = set()
    for case in interior_cases:
        match = re.search(r'stat_(\d+)', case)
        if match:
            interior_stats.add(int(match.group(1)))
    
    for stat_num in interior_stats:
        morphed_points = [(p[param1_key], p[param2_key], p['morph_variant']) 
                         for p in case_data['morphed'] 
                         if p['stat_variant'] == stat_num and
                         f"AAA_{gender}_{age_group}_stat_{stat_num}_{custom_suffix}_morph_{p['morph_variant']}"
                         in interior_cases]
        
        if morphed_points:
            x, y, nums = zip(*morphed_points)
            color = base_colors[stat_num % len(base_colors)]
            
            plt.scatter(x, y, c=[color], alpha=0.6,
                       label=f'Stat {stat_num} Interior Points',
                       marker='^', s=30)

    # Configure axes ranges same as other plots
    if fixed_ranges:
        range_specs = {
            'Neck Diameter 1': {'min': 15, 'max': 35, 'step': 5},
            'Neck Diameter 2': {'min': 15, 'max': 40, 'step': 5}, 
            'Maximum Aneurysm Diameter': {'min': 30, 'max': 90, 'step': 10},
            'Distal Diameter': {'min': 10, 'max': 50, 'step': 5}
        }
        
        x_range = range_specs[param1]
        y_range = range_specs[param2]
        
        ax.set_xlim(x_range['min'], x_range['max'])
        ax.set_ylim(y_range['min'], y_range['max'])
        
        x_ticks = np.arange(x_range['min'], x_range['max'] + 1, x_range['step'])
        y_ticks = np.arange(y_range['min'], y_range['max'] + 1, y_range['step'])
        
        ax.set_xticks(x_ticks)
        ax.set_yticks(y_ticks)
        ax.tick_params(which='major', length=8, width=1, direction='out')

    plt.xlabel(f'{param1} (mm)')
    plt.ylabel(f'{param2} (mm)')
    
    plt.tight_layout()
    
    filename = f'universal_interior_{param1.lower().replace(" ", "_")}_vs_'
    filename += f'{param2.lower().replace(" ", "_")}_{gender}_{age_group}_{outlier_method}.png'
    plt.savefig(output_dir / filename, dpi=600, bbox_inches='tight')
    plt.close()

def plot_parameter_relationship_extended(
   case_data: Dict[str, List[Dict]],
   param1: str,
   param2: str, 
   param1_key: str,
   param2_key: str,
   gender: str,
   age_group: str,
   output_dir: Path,
   hull_data: List[Dict],
   outlier_method: str = 'no_outliers',
   scale_factor: float = 0.65,  # Add scale_factor parameter with default
   fixed_ranges: bool = True
) -> None:
   # Set figure size using scale factor
   fig = plt.figure(figsize=(6*scale_factor, 6*scale_factor))


   
   # Define color scheme 
   base_colors = plt.cm.Dark2(np.linspace(0, 1, 8))
   
   matching_hull = next(
       (h for h in hull_data if 
        h['gender'] == gender and
        h['age_group'] == age_group and
        h['outlier_method'] == outlier_method and
        h['parameter_comparison'] == f"{param1} vs {param2}"),
       None
   )
   
   if matching_hull:
       hull_points = np.array(matching_hull['convex_hull_points'])
       hull_points = np.vstack((hull_points, hull_points[0]))
       plt.plot(hull_points[:, 0], hull_points[:, 1], 
               'r-', alpha=0.7, linewidth=1, 
               label=f'Patient Data Boundary (n={matching_hull["group_size"]})')

   # Group data by statistical variant
   stat_data = {}
   for p in case_data['statistical']:
       stat_num = p['stat_variant']
       if stat_num not in stat_data:
           stat_data[stat_num] = {
               'stat': {'x': [], 'y': []},
               'morphed': {'x': [], 'y': [], 'nums': []}
           }
       stat_data[stat_num]['stat']['x'].append(p[param1_key])
       stat_data[stat_num]['stat']['y'].append(p[param2_key])

   # Add morphed data
   for p in case_data['morphed']:
       stat_num = p['stat_variant']
       if stat_num in stat_data:
           stat_data[stat_num]['morphed']['x'].append(p[param1_key])
           stat_data[stat_num]['morphed']['y'].append(p[param2_key])
           stat_data[stat_num]['morphed']['nums'].append(p['morph_variant'])

   # Plot points
   for i, (stat_num, data) in enumerate(sorted(stat_data.items(), key=lambda x: x[0])):
       color = base_colors[i % len(base_colors)]
       if data['morphed']['x']:
           plt.scatter(data['morphed']['x'], data['morphed']['y'],
                   c=[color], alpha=0.6,
                   label=f'Morphed (Stat {stat_num})',
                   marker='^', s=30)

   # Configure axes
   ax = plt.gca()
   for spine in ax.spines.values():
       spine.set_linewidth(1)

   if fixed_ranges:
       range_specs = {
           'Neck Diameter 1': {'min': 15, 'max': 35, 'step': 5},
           'Neck Diameter 2': {'min': 15, 'max': 40, 'step': 5},
           'Maximum Aneurysm Diameter': {'min': 30, 'max': 90, 'step': 10},
           'Distal Diameter': {'min': 10, 'max': 50, 'step': 5}
       }
       
       x_range = range_specs[param1]
       y_range = range_specs[param2]
       
       ax.set_xlim(x_range['min'], x_range['max'])
       ax.set_ylim(y_range['min'], y_range['max'])
       
       x_ticks = np.arange(x_range['min'], x_range['max'] + 1, x_range['step'])
       y_ticks = np.arange(y_range['min'], y_range['max'] + 1, y_range['step'])
       
   else:
       x_min, x_max = plt.xlim()
       y_min, y_max = plt.ylim()
       
       x_min = np.floor(x_min)
       x_max = np.ceil(x_max)
       y_min = np.floor(y_min) 
       y_max = np.ceil(y_max)
       
       plt.xlim(x_min, x_max)
       plt.ylim(y_min, y_max)
       
       x_ticks = np.arange(int(x_min), int(x_max) + 1, 5)
       y_ticks = np.arange(int(y_min), int(y_max) + 1, 5)

   ax.set_xticks(x_ticks)
   ax.set_yticks(y_ticks)
   ax.tick_params(which='major', length=8, width=1, direction='out')

   plt.xlabel(f'{param1} (mm)')
   plt.ylabel(f'{param2} (mm)')

   plt.tight_layout()
   
   filename = f'{param1.lower().replace(" ", "_")}_vs_'
   filename += f'{param2.lower().replace(" ", "_")}_{gender}_{age_group}_manual.png'
   plt.savefig(output_dir / filename, dpi=600, bbox_inches='tight')
   plt.close()

def create_standalone_legends(case_data: Dict[str, List[Dict]], universal_interior: List[str], output_dir: Path, gender: str, param_name: str, age_group: str):
    # Regular plot legend
    plt.figure(figsize=(12, 2))
    ax = plt.gca()
    ax.axis('off')

    base_colors = plt.cm.Dark2(np.linspace(0, 1, 8))
    handles = []

    stat_counts = {}
    for p in case_data['morphed']:
        stat_num = p['stat_variant']
        stat_counts[stat_num] = stat_counts.get(stat_num, 0) + 1

    for stat_num, count in stat_counts.items():
        color = base_colors[stat_num % len(base_colors)]
        handle = plt.scatter([], [], c=[color], alpha=0.6, marker='^', s=50,
                           label=f'Morphed Stat {stat_num} (n={count})')
        handles.append(handle)

    if handles:
        handles.append(plt.plot([], [], 'r-', alpha=0.7, linewidth=1,
                              label='Patient Data Boundary')[0])

    legend = plt.legend(handles=handles,
                       loc='center',
                       fontsize=10,
                       frameon=True,
                       framealpha=1,
                       fancybox=True,
                       shadow=True,
                       ncol=4)

    legend.get_frame().set_facecolor('white')
    age_suffix = age_group.replace("+", "plus")
    plt.savefig(output_dir / f'legend_regular_{param_name}_{gender}_{age_suffix}.png',
                dpi=300, bbox_inches='tight', transparent=True)
    plt.close()

    # Interior plot legend
    plt.figure(figsize=(12, 2))
    ax = plt.gca()
    ax.axis('off')

    interior_stat_counts = {}
    for case in universal_interior:
        stat_match = re.search(r'stat_(\d+)', case)
        if stat_match:
            stat_num = int(stat_match.group(1))
            interior_stat_counts[stat_num] = interior_stat_counts.get(stat_num, 0) + 1

    interior_handles = []
    for stat_num, count in sorted(interior_stat_counts.items()):
        color = base_colors[stat_num % len(base_colors)]
        handle = plt.scatter([], [], c=[color], alpha=0.6, marker='^', s=50,
                           label=f'Stat {stat_num} Interior Points (n={count})')
        interior_handles.append(handle)

    if interior_handles:
        interior_handles.append(plt.plot([], [], 'r-', alpha=0.7, linewidth=1,
                                       label='Patient Data Boundary')[0])

    legend = plt.legend(handles=interior_handles,
                       loc='center',
                       fontsize=10,
                       frameon=True,
                       framealpha=1,
                       fancybox=True,
                       shadow=True,
                       ncol=4)
    legend.get_frame().set_facecolor('white')
    plt.savefig(output_dir / f'legend_interior_{param_name}_{gender}_{age_suffix}.png',
                dpi=300, bbox_inches='tight', transparent=True)
    plt.close()

def generate_parameter_plots_extended(
    data_path: str,
    output_dir: str, 
    ofcases_dir: str,
    gender: str,
    age_group: str,
    hull_data_path: str,
    custom_suffix: str,
    scale_factor: float = 0.65, 
    fixed_ranges: bool = True
):
    setup_plotting_style(scale_factor)
    subfolder = f"{gender}_{age_group}_{custom_suffix}/manual_modified"
    output_path = Path(output_dir) / subfolder
    output_path.mkdir(parents=True, exist_ok=True)
    
    with open(hull_data_path) as f:
        hull_data = json.load(f)
        
    interior_file = output_path / "universal_interior_analysis.txt"
    
    case_data = collect_case_data(Path(ofcases_dir), gender, age_group, custom_suffix)
    
    parameters = {
        'neck_diameter_1': {'col': 9, 'name': 'Neck Diameter 1', 'key': 'neck_diameter_1'},
        'neck_diameter_2': {'col': 10, 'name': 'Neck Diameter 2', 'key': 'neck_diameter_2'}, 
        'max_diameter': {'col': 13, 'name': 'Maximum Aneurysm Diameter', 'key': 'max_diameter'},
        'distal_diameter': {'col': 14, 'name': 'Distal Diameter', 'key': 'distal_diameter'}
    }
    
    parameter_pairs = [
        ('neck_diameter_1', 'neck_diameter_2'),
        ('neck_diameter_2', 'max_diameter'), 
        ('max_diameter', 'distal_diameter')
    ]

    outlier_method = 'manual'
    
    universal_interior = find_universal_interior_set(
        case_data,
        hull_data,
        parameters,
        parameter_pairs,
        gender,
        age_group,
        outlier_method,
        custom_suffix
    )
    
    write_interior_report(universal_interior, 
                        output_path / f"universal_interior_{outlier_method}.txt")
    
    for param1_key, param2_key in parameter_pairs:

        create_standalone_legends(case_data, universal_interior, output_path, gender, parameters[param1_key]['name'], age_group)

        plot_parameter_relationship_extended(
            case_data,
            parameters[param1_key]['name'],
            parameters[param2_key]['name'],
            parameters[param1_key]['key'],
            parameters[param2_key]['key'],
            gender,
            age_group, 
            output_path,
            hull_data,
            outlier_method,
            scale_factor=scale_factor,  # Add these parameters
            fixed_ranges=fixed_ranges
        )

        plot_universal_interior_set(
            case_data,
            parameters[param1_key]['name'],
            parameters[param2_key]['name'],
            parameters[param1_key]['key'],
            parameters[param2_key]['key'],
            gender,
            age_group,
            output_path,
            hull_data,
            universal_interior,
            outlier_method,
            custom_suffix,
            scale_factor=scale_factor,  # Add these parameters
            fixed_ranges=fixed_ranges
        )
        
        print(f"Generated plot: {parameters[param2_key]['name']} vs "
              f"{parameters[param1_key]['name']} (manual)")

if __name__ == "__main__":
    generate_parameter_plots_extended(
        data_path="data/input/aaa_data.xlsx",
        output_dir="data/processed/bound_plots",
        ofcases_dir="data/output/ofCases",
        gender="M",
        age_group="80+",
        hull_data_path="data/processed/convex_hull_metadata.json",
        custom_suffix="prob_distribution"
    )