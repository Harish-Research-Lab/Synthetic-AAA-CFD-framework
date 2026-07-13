import numpy as np
import json
from pathlib import Path
import pandas as pd
from scipy.spatial import ConvexHull
from typing import List
from data_bound_with_patient_data import AgeGroups, OutlierDetector

def generate_convex_hull_metadata(
    data_path: str, 
    output_path: str, 
    manual_outliers: List[int] = [163, 109, 71, 78, 42, 40, 72]
):
    # Read data
    df = pd.read_excel(data_path, header=None).iloc[10:268]
    
    # Extract ages and genders
    ages = pd.to_numeric(df.iloc[:, 7], errors='coerce')
    genders = df.iloc[:, 8]
    patient_ids = df.index + 11
    
    # Define parameters and outlier methods
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
    
    outlier_methods = ['no_outliers', 'zscore', 'iqr', 'mahalanobis', 'dbscan', 'manual']
    
    # Initialize metadata list
    convex_hull_metadata = []
    
    # Iterate through parameter comparisons
    for param1_key, param2_key in parameter_pairs:
        # Get parameter data and clean
        data1 = pd.to_numeric(df.iloc[:, parameters[param1_key]['col']], errors='coerce')
        data2 = pd.to_numeric(df.iloc[:, parameters[param2_key]['col']], errors='coerce')
        valid_mask = ~(np.isnan(data1) | np.isnan(data2))
        
        # Filter valid data
        param1_values = data1[valid_mask]
        param2_values = data2[valid_mask]
        valid_ages = ages[valid_mask]
        valid_genders = genders[valid_mask]
        valid_ids = patient_ids[valid_mask]
        
        # Iterate through genders and age groups
        for gender in ['All', 'M', 'F']:
            for age_group in list(AgeGroups.GROUPS.keys()) + ['All']:
                for outlier_method in outlier_methods:
                    # Filter data based on gender and age
                    if gender != 'All':
                        gender_mask = valid_genders == gender
                    else:
                        gender_mask = np.ones(len(valid_genders), dtype=bool)
                    
                    if age_group != 'All':
                        age_limits = AgeGroups.GROUPS[age_group]
                        age_mask = (valid_ages >= age_limits['min']) & (valid_ages <= age_limits['max'])
                    else:
                        age_mask = np.ones(len(valid_ages), dtype=bool)
                    
                    # Combine masks
                    mask = gender_mask & age_mask
                    
                    x = param1_values[mask]
                    y = param2_values[mask]
                    ids = valid_ids[mask]
                    
                    # Skip if insufficient data
                    if len(x) < 3:
                        continue
                    
                    # Outlier detection
                    outlier_detector = OutlierDetector(manual_outliers)
                    regular_mask = np.ones(len(x), dtype=bool)
                    
                    if outlier_method != 'no_outliers':
                        outliers = outlier_detector.detect_outliers(x, y, ids, outlier_method)
                        outlier_mask = np.isin(ids, outliers[outlier_method])
                        regular_mask = ~outlier_mask
                    
                    # Get non-outlier points
                    points = np.column_stack((x[regular_mask], y[regular_mask]))
                    
                    # Create convex hull
                    if len(points) >= 3:
                        hull = ConvexHull(points)
                        hull_points = points[hull.vertices]
                        
                        # Create metadata entry
                        metadata_entry = {
                            'gender': gender,
                            'age_group': age_group,
                            'outlier_method': outlier_method,
                            'parameter_comparison': 
                                f"{parameters[param1_key]['name']} vs {parameters[param2_key]['name']}",
                            'group_size': len(points),
                            'convex_hull_points': hull_points.tolist()
                        }
                        
                        convex_hull_metadata.append(metadata_entry)
    
    # Save to JSON
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(convex_hull_metadata, f, indent=4)
    
    print(f"Convex hull metadata saved to {output_path}")

if __name__ == "__main__":
    # Define paths
    data_path = "data/input/aaa_data.xlsx"
    output_path = "data/processed/convex_hull_metadata.json"
    
    # Run metadata generation
    generate_convex_hull_metadata(data_path, output_path)