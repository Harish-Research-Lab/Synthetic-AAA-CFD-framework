import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import pandas as pd
from typing import Dict, List, Set, Tuple
from scipy.spatial import ConvexHull

def get_age_grouped_data_by_gender(df: pd.DataFrame, gender: str, param1_idx: int, param2_idx: int) -> Dict[str, Dict]:
    """Get data grouped by age groups for specific gender"""
    age_grouped_data = {}
    
    if gender == 'All':
        gender_mask = slice(None)
    else:
        gender_mask = (df.iloc[:, 8] == gender)
    
    ages = pd.to_numeric(df.iloc[:, 7], errors='coerce')
    patient_ids = df.index + 11
    
    age_groups = {
        '50-59': {'min': 50, 'max': 59},
        '60-69': {'min': 60, 'max': 69},
        '70-79': {'min': 70, 'max': 79},
        '80+': {'min': 80, 'max': float('inf')}
    }
    
    for age_group, limits in age_groups.items():
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

def get_axis_ranges(df: pd.DataFrame, param1: dict, param2: dict) -> Dict[str, Dict[str, Tuple[float, float]]]:
    """Get x and y axis ranges for all gender combinations"""
    ranges = {}
    for gender in ['All', 'M', 'F']:
        data = get_age_grouped_data_by_gender(df, gender, param1['col'], param2['col'])
        if data:
            # Combine all x and y values
            all_x = np.concatenate([group_data['x'] for group_data in data.values()])
            all_y = np.concatenate([group_data['y'] for group_data in data.values()])
            
            # Add padding to ranges
            padding = 0.05  # 5% padding
            x_range = (np.min(all_x) * (1 - padding), np.max(all_x) * (1 + padding))
            y_range = (np.min(all_y) * (1 - padding), np.max(all_y) * (1 + padding))
            
            ranges[gender] = {'x': x_range, 'y': y_range}
    
    # Use 'All' ranges as default for any missing gender data
    default_ranges = ranges.get('All', {'x': (0, 100), 'y': (0, 100)})
    
    # Compute global ranges across all genders
    all_x_mins = [r['x'][0] for r in ranges.values()]
    all_x_maxs = [r['x'][1] for r in ranges.values()]
    all_y_mins = [r['y'][0] for r in ranges.values()]
    all_y_maxs = [r['y'][1] for r in ranges.values()]
    
    global_ranges = {
        'x': (min(all_x_mins), max(all_x_maxs)),
        'y': (min(all_y_mins), max(all_y_maxs))
    }
    
    # Set ranges for any missing genders and add global ranges
    for gender in ['All', 'M', 'F']:
        if gender not in ranges:
            ranges[gender] = default_ranges
    
    ranges['global'] = global_ranges
    return ranges

def setup_plotting_style(scale_factor=1.0):
    """Configure plotting style with scaling"""
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

def create_standalone_legend(data: Dict[str, Dict], manual_outliers: List[int], output_dir: Path, gender: str):
    """Create a standalone legend figure for age groups with point counts"""
    plt.figure(figsize=(12, 2))
    
    ax = plt.gca()
    ax.axis('off')
    
    age_colors = plt.cm.Dark2(np.linspace(0, 1, 5))
    colors = {
        '50-59': age_colors[0],
        '60-69': age_colors[1],  
        '70-79': age_colors[2],
        '80+': age_colors[3]
    }
    handles = []
    
    for group_name, group_data in data.items():
        x, y, ids = group_data['x'], group_data['y'], group_data['ids']
        color = colors[group_name]
        
        outlier_mask = np.isin(ids, manual_outliers)
        regular_mask = ~outlier_mask

        n_points = len(x[regular_mask])
        n_outliers = np.sum(outlier_mask)
        
        regular = plt.scatter([], [], c=[color], alpha=0.6, marker='o', s=50,
                            label=f'{group_name} (n={n_points})')
        handles.append(regular)
        
        outlier = plt.scatter([], [], c=[color], alpha=0.6, marker='s', s=50,
                            label=f'{group_name} outliers (n={n_outliers})')
        handles.append(outlier)

    legend = plt.legend(handles=handles, 
                       loc='center',
                       fontsize=10,
                       frameon=True,
                       framealpha=1,
                       fancybox=True,
                       shadow=True,
                       ncol=4)

    legend.get_frame().set_facecolor('white')
    
    gender_suffix = "" if gender == "All" else f"_{gender}"
    plt.savefig(output_dir / f'combined_legend{gender_suffix}.png',
                dpi=600,
                bbox_inches='tight',
                transparent=True)
    plt.close()

def plot_parameter_relationship_modified(
    df: pd.DataFrame,
    param1: dict,  
    param2: dict,
    age_group: str,
    output_dir: Path,
    manual_outliers: List[int],
    axis_ranges: Dict[str, Dict[str, Tuple[float, float]]],
    show_all_groups: bool = True,
    scale_factor: float = 2.0,
    gender: str = 'All',
    use_global_ranges: bool = True,
    fixed_ranges: bool = False
):
    """Create modified parameter relationship plot with integer ticks"""
    fig = plt.figure(figsize=(6*scale_factor, 6*scale_factor))
    
    age_colors = plt.cm.Dark2(np.linspace(0, 1, 5))
    colors = {
        '50-59': age_colors[0],
        '60-69': age_colors[1],  
        '70-79': age_colors[2],
        '80+': age_colors[3]
    }
    
    if show_all_groups:
        data = get_age_grouped_data_by_gender(df, gender, param1['col'], param2['col'])
        create_standalone_legend(data, manual_outliers, output_dir, gender)
    else:
        all_data = get_age_grouped_data_by_gender(df, gender, param1['col'], param2['col'])
        data = {age_group: all_data[age_group]} if age_group in all_data else {}

    if not data:
        print(f"No data available for {gender}, {age_group}")
        plt.close()
        return

    for group_name, group_data in data.items():
        x, y, ids = group_data['x'], group_data['y'], group_data['ids']
        color = colors[group_name]
        
        outlier_mask = np.isin(ids, manual_outliers)
        regular_mask = ~outlier_mask

        n_points = len(x[regular_mask])
        n_outliers = np.sum(outlier_mask)

        marker_size = 50 * scale_factor
        
        plt.scatter(x[regular_mask], y[regular_mask],
                   c=[color], alpha=0.6, marker='o', s=marker_size,
                   label=f'{group_name} (n={n_points})')
        
        if np.any(outlier_mask):
            plt.scatter(x[outlier_mask], y[outlier_mask],
                      c=[color], alpha=0.6, marker='s', s=marker_size,
                      label=f'{group_name} outliers (n={n_outliers})')
        
        regular_points = np.column_stack((x[regular_mask], y[regular_mask]))
        if len(regular_points) >= 3:
            hull = ConvexHull(regular_points)
            hull_points = regular_points[hull.vertices]
            hull_points = np.vstack((hull_points, hull_points[0]))
            plt.plot(hull_points[:, 0], hull_points[:, 1],
                    '-', color=color, alpha=0.3, linewidth=2)

    # Set consistent axis ranges based on global or gender-specific ranges
    ranges = axis_ranges['global'] if use_global_ranges else axis_ranges[gender]
    
    # Round the ranges to integers and set ticks
    x_min = np.floor(ranges['x'][0])
    x_max = np.ceil(ranges['x'][1])
    y_min = np.floor(ranges['y'][0])
    y_max = np.ceil(ranges['y'][1])
    
    ax = plt.gca()

    if fixed_ranges:
        # Fixed ranges for each parameter
        range_specs = {
            'Neck Diameter 1': {'min': 15, 'max': 35, 'step': 5},
            'Neck Diameter 2': {'min': 15, 'max': 40, 'step': 5},
            'Maximum Aneurysm Diameter': {'min': 30, 'max': 90, 'step': 10},
            'Distal Diameter': {'min': 10, 'max': 50, 'step': 5}
        }
        
        x_range = range_specs[param1["name"]]
        y_range = range_specs[param2["name"]]
        
        ax.set_xlim(x_range['min'], x_range['max'])
        ax.set_ylim(y_range['min'], y_range['max'])
        
        x_ticks = np.arange(x_range['min'], x_range['max'] + 1, x_range['step'])
        y_ticks = np.arange(y_range['min'], y_range['max'] + 1, y_range['step'])
    else:
        # Dynamic ranges based on data
        ranges = axis_ranges['global'] if use_global_ranges else axis_ranges[gender]
        
        x_min = np.floor(ranges['x'][0])
        x_max = np.ceil(ranges['x'][1])
        y_min = np.floor(ranges['y'][0])
        y_max = np.ceil(ranges['y'][1])
        
        ax.set_xlim(x_min, x_max)
        ax.set_ylim(y_min, y_max)
        
        x_ticks = np.arange(int(x_min), int(x_max) + 1, 5)
        y_ticks = np.arange(int(y_min), int(y_max) + 1, 5)
    
    
    ax.set_xticks(x_ticks)
    ax.set_yticks(y_ticks)

    # Add minor ticks between major ticks
    ax.tick_params(which='major', length=8, width=1, direction='out')
    # ax.tick_params(which='minor', length=4, width=1, direction='out')
    
    # # Add minor ticks
    # x_minor_ticks = np.arange(int(x_min), int(x_max) + 1, 1)
    # y_minor_ticks = np.arange(int(y_min), int(y_max) + 1, 1)
    
    # ax.set_xticks(x_minor_ticks, minor=True)
    # ax.set_yticks(y_minor_ticks, minor=True)

    plt.xlabel(f'{param1["name"]} (mm)')
    plt.ylabel(f'{param2["name"]} (mm)')
    
    if not show_all_groups:
        plt.legend(loc='upper right',
                  fontsize=10,
                  frameon=True,
                  framealpha=0.5,
                  fancybox=True,
                  shadow=False)

    plt.tight_layout()
    
    # Add range indicator to filename
    range_suffix = 'global' if use_global_ranges else 'gender'
    
    filename = f'{param1["name"].lower().replace(" ", "_")}_vs_'
    filename += f'{param2["name"].lower().replace(" ", "_")}'
    if not show_all_groups:
        filename += f'_{age_group.replace("+", "plus")}'
    filename += f'_{gender}_{range_suffix}_ranges_manual_modified.png'
    
    plt.savefig(output_dir / filename, dpi=600, bbox_inches='tight')
    plt.close()

def generate_modified_plots(
    data_path: str, 
    output_base_dir: str, 
    manual_outliers: List[int], 
    scale_factor: float = 2.0,
    use_global_ranges: bool = True,
    fixed_ranges: bool = False
):
    """Generate modified plots with consistent axis ranges"""
    output_dir = Path(output_base_dir) / 'Manual_modified_plots'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    setup_plotting_style()
    
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
    
    for param1_key, param2_key in parameter_pairs:
        axis_ranges = get_axis_ranges(df, parameters[param1_key], parameters[param2_key])
        
        for gender in ['All', 'M', 'F']:
            plot_parameter_relationship_modified(
                df,
                parameters[param1_key],
                parameters[param2_key],
                'All',
                output_dir,
                manual_outliers,
                axis_ranges,
                show_all_groups=True,
                scale_factor=scale_factor,
                gender=gender,
                use_global_ranges=use_global_ranges,
                fixed_ranges=fixed_ranges
            )
            
            for age_group in ['50-59', '60-69', '70-79', '80+']:
                plot_parameter_relationship_modified(
                    df,
                    parameters[param1_key],
                    parameters[param2_key],
                    age_group,
                    output_dir,
                    manual_outliers,
                    axis_ranges,
                    show_all_groups=False,
                    scale_factor=scale_factor,
                    gender=gender,
                    use_global_ranges=use_global_ranges,
                    fixed_ranges=fixed_ranges
                )

def plot_parameter_relationship_hulls_only(
    df: pd.DataFrame,
    param1: dict,  
    param2: dict,
    output_dir: Path,
    manual_outliers: List[int],
    axis_ranges: Dict[str, Dict[str, Tuple[float, float]]],
    scale_factor: float = 0.65,
    gender: str = 'All',
    fixed_ranges: bool = True
):
    """Create plots showing only convex hulls for age groups"""
    fig = plt.figure(figsize=(6*scale_factor, 6*scale_factor))
    
    age_colors = plt.cm.Dark2(np.linspace(0, 1, 5))
    colors = {
        '50-59': age_colors[0],
        '60-69': age_colors[1],  
        '70-79': age_colors[2],
        '80+': age_colors[3]
    }
    
    data = get_age_grouped_data_by_gender(df, gender, param1['col'], param2['col'])
    
    if not data:
        plt.close()
        return

    # Plot only convex hulls for each age group
    for group_name, group_data in data.items():
        x, y, ids = group_data['x'], group_data['y'], group_data['ids']
        color = colors[group_name]
        
        # Remove outliers
        regular_mask = ~np.isin(ids, manual_outliers)
        regular_points = np.column_stack((x[regular_mask], y[regular_mask]))
        
        if len(regular_points) >= 3:
            hull = ConvexHull(regular_points)
            hull_points = regular_points[hull.vertices]
            hull_points = np.vstack((hull_points, hull_points[0]))
            plt.plot(hull_points[:, 0], hull_points[:, 1],
                    '-', color=color, alpha=0.8, linewidth=2,
                    label=f'{group_name}')

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
        
        x_range = range_specs[param1["name"]]
        y_range = range_specs[param2["name"]]
        
        ax.set_xlim(x_range['min'], x_range['max'])
        ax.set_ylim(y_range['min'], y_range['max'])
        
        x_ticks = np.arange(x_range['min'], x_range['max'] + 1, x_range['step'])
        y_ticks = np.arange(y_range['min'], y_range['max'] + 1, y_range['step'])
        
        ax.set_xticks(x_ticks)
        ax.set_yticks(y_ticks)
        ax.tick_params(which='major', length=8, width=1, direction='out')

    plt.xlabel(f'{param1["name"]} (mm)')
    plt.ylabel(f'{param2["name"]} (mm)')
    
    # plt.legend(loc='upper right',
    #           fontsize=10,
    #           frameon=True,
    #           framealpha=0.5)

    plt.tight_layout()
    
    filename = f'{param1["name"].lower().replace(" ", "_")}_vs_'
    filename += f'{param2["name"].lower().replace(" ", "_")}'
    filename += f'_{gender}_hulls_only.png'
    
    plt.savefig(output_dir / 'hulls_only' / filename, dpi=600, bbox_inches='tight')
    plt.close()

def create_hull_only_legend(output_dir: Path, scale_factor: float = 0.65):
    """Create standalone legend image for hull-only plots"""
    plt.figure(figsize=(8*scale_factor, 1*scale_factor))
    ax = plt.gca()
    ax.axis('off')
    
    age_colors = plt.cm.Dark2(np.linspace(0, 1, 5))
    handles = []
    
    age_groups = ['50-59', '60-69', '70-79', '80+']
    for i, group in enumerate(age_groups):
        line = plt.plot([], [], 
                       '-', 
                       color=age_colors[i],
                       alpha=0.8,
                       linewidth=2,
                       label=group)[0]
        handles.append(line)

    legend = plt.legend(handles=handles,
                       loc='center',
                       ncol=4,
                       fontsize=10*scale_factor,
                       frameon=True,
                       framealpha=1,
                       fancybox=True,
                       shadow=True)
    
    legend.get_frame().set_facecolor('white')
    
    plt.savefig(output_dir / 'hulls_only' / 'legend.png',
                dpi=600,
                bbox_inches='tight',
                transparent=True)
    plt.close()

# Add this to the main generate_modified_plots function:
def generate_hull_only_plots(data_path: str, output_base_dir: str, manual_outliers: List[int]):
    output_dir = Path(output_base_dir) / 'Manual_modified_plots'
    (output_dir / 'hulls_only').mkdir(parents=True, exist_ok=True)

    # Create legend once
    create_hull_only_legend(output_dir)
    
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
    
    for param1_key, param2_key in parameter_pairs:
        axis_ranges = get_axis_ranges(df, parameters[param1_key], parameters[param2_key])
        
        for gender in ['All', 'M', 'F']:
            plot_parameter_relationship_hulls_only(
                df,
                parameters[param1_key],
                parameters[param2_key],
                output_dir,
                manual_outliers,
                axis_ranges,
                scale_factor=0.65,
                gender=gender
            )


if __name__ == "__main__":
    # Define paths and outliers
    data_path = "data/input/aaa_data.xlsx"
    output_base_dir = "data/processed/parameter_plots"
    manual_outliers = [163, 109, 71, 78, 42, 40, 72]
    
    # Generate plots with fixed ranges
    generate_modified_plots(data_path, output_base_dir, manual_outliers, 
                      scale_factor=0.65, fixed_ranges=True, use_global_ranges=True)
    
    generate_hull_only_plots(data_path, output_base_dir, manual_outliers)