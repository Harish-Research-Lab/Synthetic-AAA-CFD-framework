import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
from matplotlib.lines import Line2D
from matplotlib import gridspec
import matplotlib.colors as mcolors

def plot_mesh_convergence(excel_file, sheet_name='Sheet5', output_dir='./plots'):
    """
    Create improved mesh convergence plots from Excel data with enhanced visualization.
    
    Parameters:
    -----------
    excel_file : str
        Path to the Excel file
    sheet_name : str
        Name of the sheet containing the data
    output_dir : str
        Directory to save the plots
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Read the Excel file
    print(f"Reading data from {excel_file}, sheet: {sheet_name}")
    df = pd.read_excel(excel_file, sheet_name=sheet_name)

    # Drop specific columns that you want to ignore 
    # Modify this list to specify columns you want to drop
    columns_to_drop = [1008002,1649192]  # Example: [50000, 150000]
    df = df.drop(columns=columns_to_drop, errors='ignore')
    if columns_to_drop:
        print(f"Dropped columns: {columns_to_drop}")
    
    # Identify mesh sizes from column names (all columns except the first one)
    mesh_sizes = []
    mesh_columns = []  # Store actual column names
    
    for col in df.columns[1:]:  # Skip first column (PointID)
        try:
            # Try to extract a mesh size from the column name
            if isinstance(col, (int, float)):
                mesh_size = int(col)
                mesh_sizes.append(mesh_size)
                mesh_columns.append(col)
            elif isinstance(col, str) and col.isdigit():
                mesh_size = int(col)
                mesh_sizes.append(mesh_size)
                mesh_columns.append(col)
            else:
                print(f"Warning: Column '{col}' is not a valid mesh size, skipping")
        except ValueError:
            print(f"Warning: Column '{col}' is not a valid mesh size, skipping")
    
    print(f"\nIdentified mesh sizes: {mesh_sizes}")
    
    # Ensure we have the PointID column
    if 'PointID' not in df.columns:
        # Rename the first column to PointID
        df = df.rename(columns={df.columns[0]: 'PointID'})
    
    # Create a figure for the main plot
    plt.figure(figsize=(12, 8), dpi=300)
    
    # Create highly distinguishable colors - using distinct colors instead of a continuous colormap
    # Using distinct colors from tab20, Set1, Dark2, and tab10 for better differentiation
    distinct_colors = []
    distinct_colors.extend(plt.cm.tab10.colors)
    distinct_colors.extend(plt.cm.Dark2.colors)
    distinct_colors.extend(plt.cm.Set1.colors)
    # Ensure we have enough colors by adding some more if needed
    if len(mesh_sizes) > len(distinct_colors):
        distinct_colors.extend(plt.cm.tab20.colors)
    
    # Define line styles for better differentiation
    line_styles = ['-', '--', '-.', ':', (0, (3, 1, 1, 1)), (0, (5, 1)), (0, (3, 1, 1, 1, 1, 1))]
    # If we have more mesh sizes than line styles, cycle through them
    line_styles = line_styles * (len(mesh_sizes) // len(line_styles) + 1)
    
    # Plot each mesh size with varied line styles and colors
    for i, (mesh_size, col_name) in enumerate(zip(mesh_sizes, mesh_columns)):
        plt.plot(df['PointID'], df[col_name], 
                label=f'{mesh_size:,} cells',
                color=distinct_colors[i],
                linestyle=line_styles[i % len(line_styles)],
                linewidth=2, 
                marker='o', 
                markersize=4, 
                markevery=5)
    
    # Identify key regions based on velocity profiles (approximate)
    regions = [
        (0, 10, "Entry Region"),
        (20, 25, "Aneurysm Start"),
        (30, 40, "Aneurysm Body"),
        (45, 50, "Bifurcation")
    ]

    # Add plot formatting
    plt.xlabel('Position along Centerline', fontsize=14)
    plt.ylabel('Velocity (m/s)', fontsize=14)
    plt.title('Mesh Convergence: Velocity Distribution along Centerline', fontsize=16)
    plt.grid(True, linestyle='--', alpha=0.7)
    
    # Create a cleaner legend with custom spacing
    plt.legend(fontsize=12, loc='upper center', bbox_to_anchor=(0.5, -0.12), 
              frameon=True, ncol=4, handlelength=3)
    
    plt.tight_layout()
    
    # Save the figure
    plt.savefig(f'{output_dir}/improved_mesh_convergence_plot.png', dpi=300, bbox_inches='tight')
    plt.savefig(f'{output_dir}/improved_mesh_convergence_plot.pdf', format='pdf', bbox_inches='tight')
    print(f"\nImproved mesh convergence plot saved to {output_dir}/improved_mesh_convergence_plot.png")
    
    # ---------------------------------------------------------------------
    # Create relative difference plot (compared to finest mesh) with advanced visualization
    # ---------------------------------------------------------------------
    plt.figure(figsize=(12, 8), dpi=300)
    
    # Get the finest mesh (highest cell count)
    finest_idx = mesh_sizes.index(max(mesh_sizes))
    finest_mesh = mesh_sizes[finest_idx]
    finest_col = mesh_columns[finest_idx]
    
    # Plot relative difference for each mesh compared to the finest
    for i, (mesh_size, col_name) in enumerate(zip(mesh_sizes, mesh_columns)):
        if mesh_size != finest_mesh:  # Skip the finest mesh
            # Calculate relative difference (as percentage)
            rel_diff = 100 * abs(df[col_name] - df[finest_col]) / df[finest_col]
            
            plt.plot(df['PointID'], rel_diff, 
                     label=f'{mesh_size:,} cells',
                     color=distinct_colors[i],
                     linestyle=line_styles[i % len(line_styles)],
                     linewidth=2, 
                     marker='o', 
                     markersize=4, 
                     markevery=5)

    # Add plot formatting
    plt.xlabel('Position along Centerline', fontsize=14)
    plt.ylabel('Relative Difference (%)', fontsize=14)
    plt.title(f'Relative Difference Compared to Finest Mesh ({finest_mesh:,} cells)', fontsize=16)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend(fontsize=12, loc='upper center', bbox_to_anchor=(0.5, -0.12), 
               frameon=True, ncol=3, handlelength=3)
    
    plt.tight_layout()
    
    # Save the figure
    plt.savefig(f'{output_dir}/improved_mesh_difference_plot.png', dpi=300, bbox_inches='tight')
    plt.savefig(f'{output_dir}/improved_mesh_difference_plot.pdf', format='pdf', bbox_inches='tight')
    print(f"Improved relative difference plot saved to {output_dir}/improved_mesh_difference_plot.png")
    
    # ---------------------------------------------------------------------
    # Create enhanced convergence plot at selected points
    # ---------------------------------------------------------------------
    plt.figure(figsize=(12, 8), dpi=300)
    
    # Select some representative points along the centerline
    num_points = min(5, len(df))  # Choose up to 5 points
    point_indices = np.linspace(0, len(df)-1, num_points, dtype=int)
    
    # Sort mesh sizes and columns together
    sorted_indices = np.argsort(mesh_sizes)
    sorted_mesh_sizes = [mesh_sizes[i] for i in sorted_indices]
    sorted_mesh_columns = [mesh_columns[i] for i in sorted_indices]
    
    # Create custom markers and colors for different points
    markers = ['o', 's', '^', 'd', 'p']
    # Use distinct colors for points too - from a different colormap for clarity
    point_colors = [plt.cm.Set2(i) for i in np.linspace(0, 1, num_points)]
    
    # Plot convergence for each selected point
    for i, point in enumerate(point_indices):
        # Get velocity values at this point for all mesh sizes
        velocities = [df[col].iloc[point] for col in sorted_mesh_columns]
        
        # Calculate approximate numerical uncertainty
        if len(velocities) >= 3:
            # Use the three finest meshes to estimate uncertainty
            fine_vel = velocities[-1]
            med_vel = velocities[-2]
            coarse_vel = velocities[-3]
            
            # Calculate grid refinement ratio (assuming uniform refinement)
            r = (sorted_mesh_sizes[-1]/sorted_mesh_sizes[-2])**(1/3)  # cube root for 3D
            
            # Approximate order of accuracy
            p = abs(np.log(abs((coarse_vel-med_vel)/(med_vel-fine_vel)))/np.log(r))
            p = min(max(0.5, p), 2.0)  # Limit to reasonable range
            
            # GCI for finest mesh
            gci = 1.25 * abs((fine_vel-med_vel)/fine_vel) / (r**p - 1)
            
            # Use GCI to estimate uncertainty bars (simplified)
            uncertainties = [abs(v-fine_vel) + gci*fine_vel for v in velocities]
        else:
            # Fallback if we don't have enough mesh levels
            uncertainties = [0.02 * abs(v) for v in velocities]
        
        plt.errorbar(sorted_mesh_sizes, velocities, 
                    yerr=uncertainties,
                    fmt=f"{markers[i]}-", 
                    label=f'Point ID {df["PointID"].iloc[point]}',
                    color=point_colors[i],
                    capsize=4,
                    linewidth=2)
    
    # Add plot formatting
    plt.xscale('log')
    plt.xlabel('Number of Cells (Mesh Size)', fontsize=14)
    plt.ylabel('Velocity (m/s)', fontsize=14)
    plt.title('Mesh Convergence at Selected Points with Uncertainty Estimates', fontsize=16)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend(fontsize=12, loc='upper center', bbox_to_anchor=(0.5, -0.15), frameon=True, ncol=3)
    plt.tight_layout()
    
    # Save the figure
    plt.savefig(f'{output_dir}/improved_point_convergence.png', dpi=300, bbox_inches='tight')
    plt.savefig(f'{output_dir}/improved_point_convergence.pdf', format='pdf', bbox_inches='tight')
    print(f"Improved point convergence plot saved to {output_dir}/improved_point_convergence.png")
    
    # ---------------------------------------------------------------------
    # Create GCI error estimate plot
    # ---------------------------------------------------------------------
    plt.figure(figsize=(10, 6), dpi=300)
    
    # Sort mesh sizes for GCI calculation
    sorted_indices = np.argsort(mesh_sizes)
    sorted_mesh_sizes = [mesh_sizes[i] for i in sorted_indices]
    sorted_mesh_columns = [mesh_columns[i] for i in sorted_indices]
    
    # Calculate approximate Grid Convergence Index for a few representative points
    # Note: This is a simplified GCI calculation for demonstration
    points_for_gci = [0, 20, 40]  # Representative points
    
    # Prepare data for GCI plot
    grid_sizes_normalized = [1/np.cbrt(m) for m in sorted_mesh_sizes]  # Normalize by cube root for 3D
    
    for i, point_idx in enumerate(points_for_gci):
        if point_idx < len(df):
            # Get velocity values at this point for all mesh sizes
            velocities = [df[col].iloc[point_idx] for col in sorted_mesh_columns]
            
            # Calculate approximate error (difference from finest mesh result)
            errors = [abs(v - velocities[-1])/max(0.001, abs(velocities[-1])) for v in velocities]
            
            # Plot in log-log scale which should be approximately linear for converging solutions
            plt.loglog(grid_sizes_normalized, errors, '-o', 
                      label=f'Point {point_idx}', 
                      color=distinct_colors[i % len(distinct_colors)],
                      linewidth=2)
    
    # Add reference lines for 1st and 2nd order convergence
    x_ref = np.array([min(grid_sizes_normalized), max(grid_sizes_normalized)])
    y_ref1 = x_ref  # 1st order slope reference
    y_ref2 = x_ref**2  # 2nd order slope reference
    
    # Scale to fit on plot
    if 'errors' in locals() and len(errors) > 0:
        scale_factor = errors[len(errors)//2] / y_ref1[1]
        
        plt.loglog(x_ref, y_ref1 * scale_factor, 'k--', alpha=0.5, label='1st Order')
        plt.loglog(x_ref, y_ref2 * scale_factor, 'k:', alpha=0.5, label='2nd Order')
    
    plt.xlabel('Normalized Grid Size (h)', fontsize=12)
    plt.ylabel('Error (normalized)', fontsize=12)
    plt.title('Grid Convergence Analysis', fontsize=14)
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=10)
    plt.tight_layout()
    
    # Save the figure
    plt.savefig(f'{output_dir}/gci_analysis.png', dpi=300, bbox_inches='tight')
    plt.savefig(f'{output_dir}/gci_analysis.pdf', format='pdf', bbox_inches='tight')
    print(f"GCI analysis plot saved to {output_dir}/gci_analysis.png")
    
    print("\nMesh convergence analysis completed successfully!")

def plot_mesh_convergence_with_ci(excel_file, sheet_name='Sheet5', output_dir='./plots'):
    """
    Create mesh convergence plot showing the finest mesh with confidence interval
    and the mesh with ~1.28M cells overlaid.
    
    Parameters:
    -----------
    excel_file : str
        Path to the Excel file
    sheet_name : str
        Name of the sheet containing the data
    output_dir : str
        Directory to save the plots
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Read the Excel file
    print(f"Reading data from {excel_file}, sheet: {sheet_name}")
    df = pd.read_excel(excel_file, sheet_name=sheet_name)
    
    # Identify mesh sizes from column names (all columns except the first one)
    mesh_sizes = []
    mesh_columns = []
    
    for col in df.columns[1:]:  # Skip first column (PointID)
        try:
            if isinstance(col, (int, float)):
                mesh_size = int(col)
                mesh_sizes.append(mesh_size)
                mesh_columns.append(col)
            elif isinstance(col, str) and col.isdigit():
                mesh_size = int(col)
                mesh_sizes.append(mesh_size)
                mesh_columns.append(col)
            else:
                print(f"Warning: Column '{col}' is not a valid mesh size, skipping")
        except ValueError:
            print(f"Warning: Column '{col}' is not a valid mesh size, skipping")
    
    # Ensure we have the PointID column
    if 'PointID' not in df.columns:
        df = df.rename(columns={df.columns[0]: 'PointID'})
    
    # Find the finest mesh and the ~1.28M cells mesh
    target_mesh_size = 1286599
    finest_mesh_size = max(mesh_sizes)
    
    # Find closest mesh to target (in case the exact number isn't present)
    closest_mesh_idx = min(range(len(mesh_sizes)), 
                          key=lambda i: abs(mesh_sizes[i] - target_mesh_size))
    target_mesh_actual = mesh_sizes[closest_mesh_idx]
    
    # Get column names for the meshes we want to plot
    finest_col = mesh_columns[mesh_sizes.index(finest_mesh_size)]
    target_col = mesh_columns[closest_mesh_idx]
    
    # Create the figure
    plt.figure(figsize=(12, 8), dpi=300)
    
    # Plot the target mesh (~1.28M cells)
    plt.plot(df['PointID'], df[target_col], 
             label=f'{target_mesh_actual:,} cells',
             color='blue',
             linestyle='-',
             linewidth=2, 
             marker='o', 
             markersize=4, 
             markevery=5)
    
    # Calculate confidence interval for finest mesh (using statistical approach)
    # For demonstration, we'll use a statistical CI by estimating local variation
    
    # Method: 
    # 1. Calculate local variation using a sliding window approach
    # 2. Use this variation to estimate confidence intervals
    
    window_size = 5  # Use 5 adjacent points to estimate local variation
    ci_percentage = 0.95  # 95% confidence interval
    
    # Calculate local standard deviation with a sliding window
    local_stds = []
    for i in range(len(df)):
        # Get window indices ensuring we don't go out of bounds
        start_idx = max(0, i - window_size // 2)
        end_idx = min(len(df), i + window_size // 2 + 1)
        
        # Get window values and calculate standard deviation
        window_values = df[finest_col].iloc[start_idx:end_idx]
        std = window_values.std()
        local_stds.append(std)
    
    # Convert to array for easier computation
    local_stds = np.array(local_stds)
    
    # Calculate confidence intervals
    # For 95% CI with normal distribution, use 1.96 (z-score)
    z_score = 1.96
    ci_lower = df[finest_col] - z_score * local_stds
    ci_upper = df[finest_col] + z_score * local_stds
    
    # Plot finest mesh with confidence interval
    plt.plot(df['PointID'], df[finest_col], 
             label=f'{finest_mesh_size:,} cells (finest)',
             color='red',
             linestyle='-',
             linewidth=2)
    
    # Plot confidence interval as a shaded area
    plt.fill_between(df['PointID'], ci_lower, ci_upper, 
                     color='red', alpha=0.2,
                     label=f'95% Confidence Interval')
    
    # Identify key regions
    regions = [
        (0, 10, "Entry Region"),
        (20, 25, "Aneurysm Start"),
        (30, 40, "Aneurysm Body"),
        (45, 50, "Bifurcation")
    ]

    # Add plot formatting
    plt.xlabel('Position along Centerline', fontsize=14)
    plt.ylabel('Velocity (m/s)', fontsize=14)
    plt.title('Mesh Convergence with Confidence Interval', fontsize=16)
    plt.grid(True, linestyle='--', alpha=0.7)
    
    # Create a legend
    plt.legend(fontsize=12, loc='upper center', bbox_to_anchor=(0.5, -0.12), 
              frameon=True, ncol=3, handlelength=3)
    
    plt.tight_layout()
    
    # Save the figure
    plt.savefig(f'{output_dir}/mesh_convergence_with_ci.png', dpi=300, bbox_inches='tight')
    plt.savefig(f'{output_dir}/mesh_convergence_with_ci.pdf', format='pdf', bbox_inches='tight')
    print(f"\nMesh convergence plot with CI saved to {output_dir}/mesh_convergence_with_ci.png")
    
    # Optional: Create a zoomed view of an interesting region
    # Identify regions where meshes show more variation
    plt.figure(figsize=(12, 8), dpi=300)
    
    # Plot the meshes again
    plt.plot(df['PointID'], df[target_col], 
             label=f'{target_mesh_actual:,} cells',
             color='blue',
             linestyle='-',
             linewidth=2, 
             marker='o', 
             markersize=4, 
             markevery=5)
    
    plt.plot(df['PointID'], df[finest_col], 
             label=f'{finest_mesh_size:,} cells (finest)',
             color='red',
             linestyle='-',
             linewidth=2)
    
    plt.fill_between(df['PointID'], ci_lower, ci_upper, 
                     color='red', alpha=0.2,
                     label=f'95% Confidence Interval')
    
    # Zoom into region of interest (aneurysm body where most variation is expected)
    plt.xlim(25, 45)
    # Adjust y limits based on the data in this region
    y_values_in_region = df[df['PointID'].between(25, 45)][[target_col, finest_col]]
    y_min = y_values_in_region.min().min() * 0.95
    y_max = y_values_in_region.max().max() * 1.05
    plt.ylim(y_min, y_max)
    
    # Add plot formatting
    plt.xlabel('Position along Centerline', fontsize=14)
    plt.ylabel('Velocity (m/s)', fontsize=14)
    plt.title('Zoomed View: Aneurysm Region Mesh Convergence', fontsize=16)
    plt.grid(True, linestyle='--', alpha=0.7)
    
    plt.legend(fontsize=12, loc='upper center', bbox_to_anchor=(0.5, -0.12), 
              frameon=True, ncol=3, handlelength=3)
    
    plt.tight_layout()
    
    # Save the zoomed figure
    plt.savefig(f'{output_dir}/mesh_convergence_zoomed_with_ci.png', dpi=300, bbox_inches='tight')
    plt.savefig(f'{output_dir}/mesh_convergence_zoomed_with_ci.pdf', format='pdf', bbox_inches='tight')
    print(f"Zoomed mesh convergence plot with CI saved to {output_dir}/mesh_convergence_zoomed_with_ci.png")


if __name__ == "__main__":
    # Default file path - update this if your file is in a different location
    excel_file = "mesh_convergence.xlsx"
    
    # Check if file exists
    if not os.path.exists(excel_file):
        print(f"Error: File {excel_file} not found.")
        print("Please place the Excel file in the same directory as this script,")
        print("or update the excel_file variable with the correct path.")
    else:
        plot_mesh_convergence(excel_file)
        plot_mesh_convergence_with_ci(excel_file)