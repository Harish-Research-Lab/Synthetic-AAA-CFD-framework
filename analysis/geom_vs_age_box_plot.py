import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import os
import re
import json
import sys

def find_ofcases_directory():
    """
    Automatically find the ofCases directory regardless of where the script is run from.
    """
    # Get the directory where this script is located
    script_dir = Path(__file__).parent.absolute()
    
    # Try to find ofCases directory by searching upwards from script location
    current_dir = script_dir
    for _ in range(5):  # Try up to 5 levels up
        # First try: direct path to output/ofCases relative to current dir
        ofcases_path = current_dir / "output" / "ofCases"
        if ofcases_path.exists():
            return ofcases_path
        
        # Second try: data/output/ofCases relative to current dir
        ofcases_path = current_dir / "data" / "output" / "ofCases"
        if ofcases_path.exists():
            return ofcases_path
            
        # Move up one directory
        current_dir = current_dir.parent

    # If not found, try absolute path (specific to your project)
    absolute_path = Path("/Users/user/Desktop/Vijay-Nandurdikar-PhD/Aorta/ofCaseGen/Method_4/data/output/ofCases")
    if absolute_path.exists():
        return absolute_path
        
    return None

def load_patient_data(data_path=None):
    """
    Load patient data from Excel file and extract geometry parameters.
    """
    # If no path specified, try to find it
    if data_path is None:
        script_dir = Path(__file__).parent.absolute()
        for _ in range(5):  # Try up to 5 levels up
            # Try different possible locations
            potential_paths = [
                script_dir / "input" / "aaa_data.xlsx",
                script_dir / "data" / "input" / "aaa_data.xlsx",
                script_dir.parent / "data" / "input" / "aaa_data.xlsx"
            ]
            
            for path in potential_paths:
                if path.exists():
                    data_path = path
                    break
                    
            if data_path:
                break
                
            # Move up one directory
            script_dir = script_dir.parent
            
        # If still not found, use absolute path
        if not data_path:
            data_path = Path("/Users/user/Desktop/Vijay-Nandurdikar-PhD/Aorta/ofCaseGen/Method_4/data/input/aaa_data.xlsx")
    
    # Check if the file exists
    if not os.path.exists(data_path):
        print(f"Patient data file not found: {data_path}")
        return pd.DataFrame()
        
    print(f"Loading patient data from: {data_path}")
    
    # Read the Excel file
    df = pd.read_excel(data_path, header=None).iloc[10:268]
    
    # Extract relevant columns
    ages = pd.to_numeric(df.iloc[:, 7], errors='coerce')
    genders = df.iloc[:, 8]
    neck_diameter_1 = pd.to_numeric(df.iloc[:, 9], errors='coerce')
    neck_diameter_2 = pd.to_numeric(df.iloc[:, 10], errors='coerce')
    max_diameter = pd.to_numeric(df.iloc[:, 13], errors='coerce')
    distal_diameter = pd.to_numeric(df.iloc[:, 14], errors='coerce')
    
    # Create DataFrame with extracted data
    patient_data = pd.DataFrame({
        'Age': ages,
        'Gender': genders,
        'Neck_Diameter_1': neck_diameter_1,
        'Neck_Diameter_2': neck_diameter_2, 
        'Max_Diameter': max_diameter,
        'Distal_Diameter': distal_diameter
    })
    
    # Define age groups
    bins = [0, 49, 59, 69, 79, 100]
    labels = ['<50', '50-59', '60-69', '70-79', '80+']
    patient_data['Age_Group'] = pd.cut(patient_data['Age'], bins=bins, labels=labels, right=True)
    
    # Drop rows with missing values
    patient_data = patient_data.dropna(subset=['Age', 'Gender', 'Max_Diameter'])
    
    # Filter data for males only
    patient_data = patient_data[patient_data['Gender'] == 'M']
    
    # Filter to include only the required age groups (60-69, 70-79, 80+)
    patient_data = patient_data[patient_data['Age_Group'].isin(['60-69', '70-79', '80+'])]
    
    return patient_data

def load_virtual_data(base_dir=None, case_type="all"):
    """
    Load virtual (generated) data from unzipped directories.
    
    Args:
        base_dir: Base directory containing the case folders
        case_type: Type of cases to load ("all", "interior", or "both")
    """
    # If no base_dir is specified, try to find it
    if base_dir is None:
        base_dir = find_ofcases_directory()
        if base_dir is None:
            print("Could not find the ofCases directory.")
            return pd.DataFrame()
    
    # Convert to Path object if it's a string
    base_dir = Path(base_dir)
    
    # Initialize empty data list
    data_list = []
    
    print(f"Base directory: {base_dir}")
    print(f"Directory exists: {os.path.exists(base_dir)}")
    
    # Pattern for case directories - specifically for males (M)
    dir_pattern = r"M_([0-9\+\-]+)_prob_distribution_(interior|all)_cases"
    
    # Look for directories matching the pattern
    matching_dirs = []
    for item in os.listdir(base_dir):
        item_path = os.path.join(base_dir, item)
        if os.path.isdir(item_path):
            match = re.match(dir_pattern, item)
            if match:
                # Add only if age group is one of the ones we want
                age_group = match.group(1)
                if age_group in ['60-69', '70-79', '80+']:
                    case_subtype = match.group(2)  # interior or all
                    matching_dirs.append((item, match, case_subtype))
    
    print(f"Matching directories found: {len(matching_dirs)}")
    for dir_name, _, subtype in matching_dirs:
        print(f"  - {dir_name} ({subtype})")
    
    # If no matching directories, try to look one level deeper
    if not matching_dirs:
        print("No matching directories found. Checking one level deeper...")
        for subdir in os.listdir(base_dir):
            subdir_path = os.path.join(base_dir, subdir)
            if os.path.isdir(subdir_path):
                for item in os.listdir(subdir_path):
                    item_path = os.path.join(subdir_path, item)
                    if os.path.isdir(item_path):
                        match = re.match(dir_pattern, item)
                        if match:
                            age_group = match.group(1)
                            if age_group in ['60-69', '70-79', '80+']:
                                case_subtype = match.group(2)  # interior or all
                                matching_dirs.append((os.path.join(subdir, item), match, case_subtype))
    
    if not matching_dirs:
        print("Still no matching directories found. Please check your directory structure.")
        return pd.DataFrame()
        
    # Process each matching directory
    for dir_info in matching_dirs:
        dir_name, match, subtype = dir_info
        dir_path = os.path.join(base_dir, dir_name)
        
        # Skip if not the type we want
        if case_type != "both" and case_type != subtype:
            print(f"Skipping {dir_name} (not the desired case type)")
            continue
            
        age_group = match.group(1)
        gender = "M"  # We're filtering for males only
        
        print(f"Processing {dir_name} ({subtype})...")
        
        # Loop through all case subdirectories
        for item in os.listdir(dir_path):
            morphed_case_path = os.path.join(dir_path, item)
            if not os.path.isdir(morphed_case_path) or not item.startswith("AAA_"):
                continue
                
            # Extract morph case info
            case_match = re.match(r"AAA_([MF])_([0-9\+\-]+)_stat_(\d+)_prob_distribution(_morph_(\d+))?", item)
            if not case_match:
                continue
                
            stat_variant = case_match.group(3)
            is_morphed = case_match.group(4) is not None
            morph_variant = case_match.group(5) if is_morphed else None
            
            # Get parameters from files
            params_file = os.path.join(morphed_case_path, 'parameters', 'geometry_params.json')
            validation_file = os.path.join(morphed_case_path, 'parameters', 'validation_results.json')
            
            if os.path.exists(params_file):
                try:
                    with open(params_file, 'r') as f:
                        params = json.load(f)
                    
                    # For morphed cases, try to get measurements from validation file
                    if is_morphed and os.path.exists(validation_file):
                        try:
                            with open(validation_file, 'r') as f:
                                validation = json.load(f)
                                measurements = validation.get('measurements', {})
                                
                                # Add to data list with measurements from validation
                                data_list.append({
                                    'Gender': gender,
                                    'Age_Group': age_group,
                                    'Stat_Variant': stat_variant,
                                    'Morph_Variant': morph_variant,
                                    'Neck_Diameter_1': measurements.get('Neck 1', params.get('neck_diameter_1')),
                                    'Neck_Diameter_2': measurements.get('Neck 2', params.get('neck_diameter_2')),
                                    'Max_Diameter': measurements.get('Maximum Aneurysm', params.get('max_diameter')),
                                    'Distal_Diameter': measurements.get('Distal', params.get('distal_diameter')),
                                    'Type': f'Virtual ({subtype})'
                                })
                        except Exception as e:
                            print(f"    Error processing validation file: {e}")
                            # Fallback to original parameters
                            data_list.append({
                                'Gender': gender,
                                'Age_Group': age_group,
                                'Stat_Variant': stat_variant,
                                'Morph_Variant': morph_variant,
                                'Neck_Diameter_1': params.get('neck_diameter_1'),
                                'Neck_Diameter_2': params.get('neck_diameter_2'),
                                'Max_Diameter': params.get('max_diameter'),
                                'Distal_Diameter': params.get('distal_diameter'),
                                'Type': f'Virtual ({subtype})'
                            })
                    else:
                        # Add to data list with original parameters
                        data_list.append({
                            'Gender': gender,
                            'Age_Group': age_group,
                            'Stat_Variant': stat_variant,
                            'Morph_Variant': morph_variant,
                            'Neck_Diameter_1': params.get('neck_diameter_1'),
                            'Neck_Diameter_2': params.get('neck_diameter_2'),
                            'Max_Diameter': params.get('max_diameter'),
                            'Distal_Diameter': params.get('distal_diameter'),
                            'Type': f'Virtual ({subtype})'
                        })
                except Exception as e:
                    print(f"    Error processing {params_file}: {e}")
    
    # Create DataFrame
    virtual_data = pd.DataFrame(data_list)
    print(f"Loaded {len(virtual_data)} virtual cases.")
    
    if len(virtual_data) > 0:
        print("Sample of loaded data:")
        print(virtual_data.head(2))
        
    return virtual_data

def prepare_combined_data(patient_data, virtual_data):
    """
    Prepare combined dataset for plotting.
    """
    # Add type column to patient data
    patient_data['Type'] = 'Patient'
    
    # Select only needed columns from patient data
    patient_subset = patient_data[['Gender', 'Age_Group', 'Neck_Diameter_1', 
                                  'Neck_Diameter_2', 'Max_Diameter', 
                                  'Distal_Diameter', 'Type']]
    
    # Combine data
    combined_data = pd.concat([patient_subset, virtual_data], ignore_index=True)
    
    # Ensure age groups are sorted correctly
    combined_data['Age_Group'] = pd.Categorical(
        combined_data['Age_Group'], 
        categories=['60-69', '70-79', '80+'], 
        ordered=True
    )
    
    return combined_data

def plot_geometry_boxplots(combined_data, parameter='Max_Diameter', 
                          include_all_virtual=True, 
                          output_dir='data/processed/boxplots'):
    """
    Create box plots comparing patient vs virtual data.
    
    Args:
        combined_data: DataFrame with patient and virtual data
        parameter: Geometry parameter to plot
        include_all_virtual: Whether to include "Virtual (all)" category
        output_dir: Directory to save plots
    """
    plt.figure(figsize=(10, 7))
    
    # Set the style
    sns.set_style("whitegrid")
    plt.rcParams.update({
        'font.family': 'serif',
        'font.size': 12,
        'axes.labelsize': 14,
        'axes.titlesize': 16,
        'xtick.labelsize': 12,
        'ytick.labelsize': 12
    })
    
    # Define the parameter labels
    param_labels = {
        'Neck_Diameter_1': 'Neck Diameter 1 (mm)',
        'Neck_Diameter_2': 'Neck Diameter 2 (mm)',
        'Max_Diameter': 'Maximum Aneurysm Diameter (mm)',
        'Distal_Diameter': 'Distal Diameter (mm)'
    }
    
    # Define color palette
    if include_all_virtual:
        palette = {'Patient': '#2c7fb8', 'Virtual (all)': '#f18f3b', 'Virtual (interior)': '#7fc97f'}
    else:
        palette = {'Patient': '#2c7fb8', 'Virtual (interior)': '#7fc97f'}
    
    # Filter data if needed
    plot_data = combined_data.copy()
    if not include_all_virtual:
        plot_data = plot_data[plot_data['Type'] != 'Virtual (all)']
    
    # Create the box plot
    sns.boxplot(
        data=plot_data,
        x='Age_Group', 
        y=parameter, 
        hue='Type',
        palette=palette,
        showfliers=False,  # Hide outliers for cleaner visualization
        width=0.7
    )
    
    plt.xlabel('Age Group')
    plt.ylabel(param_labels.get(parameter, parameter))
    title_suffix = " (with all cases)" if include_all_virtual else " (interior cases only)"
    plt.title(f'{param_labels.get(parameter, parameter)} by Age Group{title_suffix}')
    
    # Add legend with better positioning
    plt.legend(title='Data Source', bbox_to_anchor=(1.02, 1), loc='upper left')
    
    plt.tight_layout()
    
    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Save the figure
    suffix = "with_all_cases" if include_all_virtual else "interior_only"
    plt.savefig(f"{output_dir}/{parameter}_{suffix}.png", dpi=300, bbox_inches='tight')
    plt.close()

def create_all_boxplots(base_dir=None):
    """
    Generate all box plots for AAA geometry parameters.
    
    Args:
        base_dir: Base directory containing the case folders
    """
    # Load data
    print("Loading patient data...")
    patient_data = load_patient_data()
    
    print("Loading all virtual data...")
    virtual_data = load_virtual_data(base_dir=base_dir, case_type="both")
    
    if len(virtual_data) == 0:
        print("No virtual data found. Please check the directory structure and path.")
        return
    
    print("Preparing combined dataset...")
    combined_data = prepare_combined_data(patient_data, virtual_data)
    
    # Create output directory
    script_dir = Path(__file__).parent.absolute()
    output_dir = script_dir / 'processed' / 'boxplots_modified'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate plots for each parameter
    parameters = ['Neck_Diameter_1', 'Neck_Diameter_2', 'Max_Diameter', 'Distal_Diameter']
    
    for parameter in parameters:
        print(f"Generating box plots for {parameter}...")
        
        # Create box plots with all three categories
        plot_geometry_boxplots(combined_data, parameter=parameter, 
                              include_all_virtual=True, 
                              output_dir=output_dir)
        
        # Create box plots with just patient and interior cases
        plot_geometry_boxplots(combined_data, parameter=parameter, 
                              include_all_virtual=False, 
                              output_dir=output_dir)
    
    print("All box plots generated successfully!")
    print(f"Plots saved to: {output_dir}")

if __name__ == "__main__":
    # Get the directory from command line if provided, otherwise use automatic detection
    base_dir = sys.argv[1] if len(sys.argv) > 1 else None
    
    if base_dir:
        print(f"Using base directory from argument: {base_dir}")
    else:
        print("No base directory provided, attempting automatic detection...")
    
    create_all_boxplots(base_dir=base_dir)