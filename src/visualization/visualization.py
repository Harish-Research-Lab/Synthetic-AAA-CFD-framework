import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from mpl_toolkits.mplot3d import Axes3D
from scipy.spatial import ConvexHull
import seaborn as sns
import trimesh
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from config import ConfigParams
from src.vesselMorph.compute_morphed_centerline import compute_morphed_centerline

def set_paper_style():
    """Set the plotting style suitable for research papers"""
    plt.style.use('seaborn-whitegrid')
    plt.rcParams.update({
        'font.family': 'serif',
        'font.serif': ['Times New Roman'],
        'font.size': 10,
        'axes.labelsize': 12,
        'axes.titlesize': 14,
        'figure.titlesize': 14,
        'figure.facecolor': 'white',
        'savefig.dpi': 300,
        'savefig.bbox': 'tight',
        'savefig.facecolor': 'white'
    })

def calculate_shape_metrics(vertices: np.ndarray, faces: np.ndarray) -> dict:
    """
    Calculate shape metrics using both mesh geometry and convex hull.
    
    Args:
        vertices: Nx3 array of vertex coordinates
        faces: Mx3 array of face indices
    """
    # Calculate mesh volume using trimesh (tetrahedralization) for correctness.
    # The divergence theorem with per-face abs() overestimates volume on non-convex
    # meshes — trimesh avoids this by decomposing into signed tetrahedra.
    tri = trimesh.Trimesh(vertices=vertices, faces=faces)
    tri.fix_normals()
    tri.fill_holes()

    if tri.is_watertight:
        mesh_volume = float(tri.volume)
    else:
        # Signed divergence theorem: accumulate without abs, take abs of the total
        vol = 0.0
        for face in faces:
            v1, v2, v3 = vertices[face]
            cp = np.cross(v2 - v1, v3 - v1)
            area = np.linalg.norm(cp) / 2
            if area > 0:
                n_hat = cp / (2 * area)
                centroid = (v1 + v2 + v3) / 3
                vol += np.dot(centroid, n_hat) * area / 3
        mesh_volume = abs(vol)

    mesh_surface_area = float(np.sum(tri.area_faces))
    
    # Calculate convex hull measurements for comparison
    hull = ConvexHull(vertices)
    hull_volume = hull.volume
    hull_surface_area = hull.area
    
    # Calculate sphericity using actual mesh measurements
    sphericity = ((36 * np.pi * mesh_volume**2)**(1/3)) / mesh_surface_area
    
    # Calculate roundness
    centroid = np.mean(vertices, axis=0)
    radii = np.linalg.norm(vertices - centroid, axis=1)
    roundness = np.min(radii) / np.max(radii)
    
    # Calculate additional metrics
    surface_volume_ratio = mesh_surface_area / mesh_volume if mesh_volume > 0 else float('inf')
    convexity = mesh_volume / hull_volume if hull_volume > 0 else 1.0
    avg_radius = np.mean(radii)
    
    return {
        # Actual mesh measurements
        'volume': float(mesh_volume),
        'surface_area': float(mesh_surface_area),
        'sphericity': float(sphericity),
        'roundness': float(roundness),
        'surface_volume_ratio': float(surface_volume_ratio),
        'average_radius': float(avg_radius),
        
        # Convex hull measurements
        'hull_volume': float(hull_volume),
        'hull_surface_area': float(hull_surface_area),
        'convexity': float(convexity)
    }

def calculate_centerline_metrics(centerline: np.ndarray) -> dict:
    """Calculate centerline-based metrics."""
    # Calculate straight-line length
    straight_length = np.linalg.norm(centerline[-1] - centerline[0])
    
    # Calculate centerline length
    segments = np.diff(centerline, axis=0)
    centerline_length = np.sum(np.sqrt(np.sum(segments**2, axis=1)))
    
    # Calculate tortuosity
    tortuosity = centerline_length / straight_length if straight_length > 0 else 1.0
    
    return {
        'centerline_length': float(centerline_length),
        'straight_length': float(straight_length),
        'tortuosity': float(tortuosity)
    }

def plot_anatomical_points(spline_points: np.ndarray, 
                         anatomical_points: List, 
                         output_path: Path,
                         figsize: Tuple[int, int] = (10, 12)) -> None:
    """Plot the initial curve with anatomical points and perpendicular diameter lines."""
    set_paper_style()
    fig, ax = plt.subplots(figsize=figsize)
    
    # Flip the y-axis to show inlet at top
    ax.invert_yaxis()
    
    # Plot the centerline
    ax.plot(spline_points[:, 0], spline_points[:, 1], 'k-', linewidth=1.5, label='Centerline')
    
    # Separate control points and anatomical points
    control_points = [p for p in anatomical_points if 'Control' in p.name]
    anat_points = [p for p in anatomical_points if 'Control' not in p.name]
    
    def calculate_perpendicular_line(point, next_point, diameter):
        """Calculate endpoints of perpendicular line representing diameter."""
        # Calculate direction vector
        if next_point is not None:
            dx = next_point.x - point.x
            dy = next_point.y - point.y
        else:
            prev_idx = anatomical_points.index(point) - 1
            prev_point = anatomical_points[prev_idx]
            dx = point.x - prev_point.x
            dy = point.y - prev_point.y
            
        # Normalize direction vector
        length = np.sqrt(dx**2 + dy**2)
        dx, dy = dx/length, dy/length
        
        # Calculate perpendicular vector
        perpx, perpy = -dy, dx
        
        # Calculate endpoints
        radius = diameter / 2
        start_x = point.x - perpx * radius
        start_y = point.y - perpy * radius
        end_x = point.x + perpx * radius
        end_y = point.y + perpy * radius
        
        return (start_x, start_y), (end_x, end_y)
    
    # Plot anatomical points
    for i, point in enumerate(anat_points):
        # Plot point
        ax.plot(point.x, point.y, 'ro', markersize=8)
        
        # Calculate next point for direction
        next_point = anat_points[i + 1] if i < len(anat_points) - 1 else None
        
        # Plot diameter line
        (start_x, start_y), (end_x, end_y) = calculate_perpendicular_line(point, next_point, point.diameter)
        ax.plot([start_x, end_x], [start_y, end_y], 'r--', alpha=0.5)
        
        # Add label
        ax.annotate(f'{point.name}\n(D={point.diameter:.1f}mm)', 
                   (point.x, point.y), 
                   xytext=(15, 15), 
                   textcoords='offset points',
                   bbox=dict(facecolor='white', edgecolor='red', alpha=0.8),
                   arrowprops=dict(arrowstyle='->'))
    
    # Plot control points
    for point in control_points:
        ax.plot(point.x, point.y, 'bo', markersize=6)
    
    ax.set_xlabel('X [mm]')
    ax.set_ylabel('Y [mm]')
    ax.set_title('AAA Geometry with Anatomical Points')
    ax.grid(True, linestyle='--', alpha=0.7)
    ax.set_aspect('equal')
    
    plt.savefig(output_path)
    plt.close()

def plot_orthogonal_views(geometry: Dict,
                         output_prefix: Path,
                         is_morphed: bool = False,
                         original_centerline: Optional[np.ndarray] = None,
                         figsize: Tuple[int, int] = (10, 12)) -> None:
    """Plot three orthogonal views with correct alignment and simplified legend."""
    set_paper_style()
    
    views = [
        {
            'name': 'front_xz',
            'title': 'Front View (X-Z plane)',
            'elev': 0,
            'azim': 0,
            'xlabel': 'Z [mm]',
            'ylabel': 'X [mm]'
        },
        {
            'name': 'side_yz',
            'title': 'Side View (Y-Z plane)',
            'elev': 0,
            'azim': 90,
            'xlabel': 'Z [mm]',
            'ylabel': 'Y [mm]'
        },
        {
            'name': 'top_xy',
            'title': 'Top View (X-Y plane)',
            'elev': 90,
            'azim': 0,
            'xlabel': 'X [mm]',
            'ylabel': 'Y [mm]'
        }
    ]
    
    geometry_type = 'Morphed' if is_morphed else 'Base'
    
    for view in views:
        fig = plt.figure(figsize=figsize)
        ax = fig.add_subplot(111, projection='3d')
        
        # Plot surface mesh
        surf = ax.plot_trisurf(geometry['vertices'][:, 0],
                             geometry['vertices'][:, 2],
                             -geometry['vertices'][:, 1],
                             triangles=geometry['faces'],
                             color='lightgray',
                             alpha=0.7)
        
        # Plot centerlines with simplified legend
        # Plot centerlines with simplified legend
        if is_morphed and original_centerline is not None:
            # Compute morphed centerline
            morphed_centerline = compute_morphed_centerline(
                geometry['vertices'],
                original_centerline,
                geometry['inlet_patch'],
                geometry['outlet_patch']
            )
            
            # Calculate metrics for legend
            cl_metrics = calculate_centerline_metrics(morphed_centerline)
            centerline_label = f"Morphed Centerline\nL={cl_metrics['centerline_length']:.1f}mm\nτ={cl_metrics['tortuosity']:.2f}"
            
            # Plot morphed centerline
            ax.plot(morphed_centerline[:, 0],
                morphed_centerline[:, 2],
                -morphed_centerline[:, 1],
                'r-', linewidth=2,
                label=centerline_label)
            
            # Plot original centerline
            ax.plot(original_centerline[:, 0],
                original_centerline[:, 2],
                -original_centerline[:, 1],
                'b:', linewidth=1.5,
                label='Original Centerline')
        else:
            # Calculate metrics for base centerline
            cl_metrics = calculate_centerline_metrics(geometry['centerline3D'])
            centerline_label = f"Centerline\nL={cl_metrics['centerline_length']:.1f}mm\nτ={cl_metrics['tortuosity']:.2f}"
            
            # Plot base centerline
            ax.plot(geometry['centerline3D'][:, 0],
                geometry['centerline3D'][:, 2],
                -geometry['centerline3D'][:, 1],
                'r-', linewidth=2,
                label=centerline_label)
        
        # Set parallel projection
        ax.set_proj_type('ortho')
        
        # Calculate bounds while maintaining orientation
        vertices = geometry['vertices']
        max_range = np.array([
            vertices[:, 0].max() - vertices[:, 0].min(),
            vertices[:, 2].max() - vertices[:, 2].min(),
            vertices[:, 1].max() - vertices[:, 1].min()
        ]).max() / 2.0
        
        # Calculate midpoints
        mid_x = (vertices[:, 0].max() + vertices[:, 0].min()) / 2
        mid_y = (vertices[:, 2].max() + vertices[:, 2].min()) / 2
        mid_z = (-vertices[:, 1].max() + -vertices[:, 1].min()) / 2
        
        # Set equal aspect ratio
        ax.set_xlim(mid_x - max_range, mid_x + max_range)
        ax.set_ylim(mid_y - max_range, mid_y + max_range)
        ax.set_zlim(mid_z - max_range, mid_z + max_range)
        
        ax.view_init(elev=view['elev'], azim=view['azim'])
        ax.set_xlabel(view['xlabel'])
        ax.set_ylabel(view['ylabel'])
        ax.set_title(f'{geometry_type} AAA Geometry - {view["title"]}')
        
        ax.grid(True, linestyle='-', alpha=0.2)
        ax.tick_params(axis='x', which='major', pad=0)
        ax.tick_params(axis='y', which='major', pad=0)
        
        legend = ax.legend(bbox_to_anchor=(1.02, 1), loc='upper left')
        
        plt.tight_layout()
        output_path = output_prefix.parent / f"{output_prefix.stem}_{view['name']}.png"
        plt.savefig(output_path,
                   bbox_inches='tight',
                   bbox_extra_artists=(legend,),
                   dpi=300,
                   pad_inches=0.1)
        plt.close()

def plot_velocity_profile(velocity_data: np.ndarray, 
                         output_path: Path,
                         figsize: Tuple[int, int] = (10, 6)) -> None:
    """Plot and save the inlet velocity time profile."""
    set_paper_style()
    
    fig, ax = plt.subplots(figsize=figsize)
    
    time = velocity_data[:, 0]
    velocity = velocity_data[:, 1]
    
    ax.plot(time, velocity, 'b-', linewidth=2)
    ax.set_xlabel('Time [s]')
    ax.set_ylabel('Velocity [m/s]')
    ax.set_title('Inlet Velocity Profile')
    ax.grid(True, linestyle='--', alpha=0.7)
    
    plt.savefig(output_path)
    plt.close()

def save_visualizations(config: ConfigParams,
                       base_geometry: Dict,
                       spline_points: np.ndarray,
                       velocity_data: np.ndarray,
                       case_dir: Path,
                       morphed_geometry: Optional[Dict] = None) -> Dict:
    """Generate and save all visualizations and metrics for a case."""
    vis_dir = case_dir / 'visualizations'
    vis_dir.mkdir(parents=True, exist_ok=True)

    # PNG renders are optional (config.vessel_settings.save_visualization_images);
    # the geometry_metrics.json descriptors below are always written.
    save_images = getattr(config.vessel_settings, 'save_visualization_images', True)

    # Plot anatomical points
    if save_images:
        plot_anatomical_points(
            spline_points,
            config.anatomical_points,
            vis_dir / 'anatomical_points.png'
        )

    # Calculate and store metrics for base geometry
    base_metrics = {
        'shape': calculate_shape_metrics(base_geometry['vertices'], base_geometry['faces']),
        'centerline': calculate_centerline_metrics(base_geometry['centerline3D'])
    }
    
    # Plot base geometry views with metrics
    if save_images:
        plot_orthogonal_views(
            base_geometry,
            vis_dir / 'base_geometry',
            is_morphed=False
        )
    
    # Initialize metrics dictionary
    metrics = {
        'base': base_metrics,
        'parameters': {
            'gender': config.demographics.gender,
            'age_group': config.demographics.age_group,
            'statistical_variation': config.demographics.stat_variant
        }
    }
    
    # Process morphed geometry if provided
    if morphed_geometry is not None:
        # Compute actual morphed centerline
        morphed_centerline = compute_morphed_centerline(
            morphed_geometry['vertices'],
            base_geometry['centerline3D'],
            morphed_geometry['inlet_patch'],
            morphed_geometry['outlet_patch']
        )
        
        # Update the centerline in morphed geometry
        morphed_geometry['centerline3D'] = morphed_centerline
        
        # Calculate metrics with the correct centerline
        morphed_metrics = {
            'shape': calculate_shape_metrics(morphed_geometry['vertices'], morphed_geometry['faces']),
            'centerline': calculate_centerline_metrics(morphed_centerline)
        }
        
        # Calculate relative changes
        relative_changes = {
            'volume_change': (morphed_metrics['shape']['volume'] - base_metrics['shape']['volume']) / base_metrics['shape']['volume'] * 100,
            'surface_area_change': (morphed_metrics['shape']['surface_area'] - base_metrics['shape']['surface_area']) / base_metrics['shape']['surface_area'] * 100,
            'centerline_length_change': (morphed_metrics['centerline']['centerline_length'] - base_metrics['centerline']['centerline_length']) / base_metrics['centerline']['centerline_length'] * 100,
            'tortuosity_change': (morphed_metrics['centerline']['tortuosity'] - base_metrics['centerline']['tortuosity']) / base_metrics['centerline']['tortuosity'] * 100,
            'sphericity_change': (morphed_metrics['shape']['sphericity'] - base_metrics['shape']['sphericity']) / base_metrics['shape']['sphericity'] * 100
        }
        metrics['relative_changes'] = {k: float(v) for k, v in relative_changes.items()}
        
        # Plot morphed geometry views
        if save_images:
            plot_orthogonal_views(
                morphed_geometry,
                vis_dir / 'morphed_geometry',
                is_morphed=True,
                original_centerline=base_geometry['centerline3D']
            )

    # Plot velocity profile
    if save_images:
        plot_velocity_profile(
            velocity_data,
            vis_dir / 'velocity_profile.png'
        )
    
    # Save metrics to JSON file
    import json
    metrics_file = vis_dir / 'geometry_metrics.json'
    with open(metrics_file, 'w') as f:
        json.dump(metrics, f, indent=4)
        
    # Generate summary text file
    summary_file = vis_dir / 'metrics_summary.txt'
    with open(summary_file, 'w') as f:
        f.write(f"Geometry Metrics Summary\n")
        f.write(f"======================\n\n")
        f.write(f"Case: {case_dir.name}\n")
        f.write(f"Gender: {config.demographics.gender}\n")
        f.write(f"Age Group: {config.demographics.age_group}\n\n")
        
        f.write(f"Base Geometry:\n")
        f.write(f"-------------\n")
        f.write(f"Volume: {base_metrics['shape']['volume']:.1f} mm³\n")
        f.write(f"Surface Area: {base_metrics['shape']['surface_area']:.1f} mm²\n")
        f.write(f"Centerline Length: {base_metrics['centerline']['centerline_length']:.1f} mm\n")
        f.write(f"Tortuosity: {base_metrics['centerline']['tortuosity']:.3f}\n")
        f.write(f"Sphericity: {base_metrics['shape']['sphericity']:.3f}\n")
        f.write(f"Convexity: {base_metrics['shape']['convexity']:.3f}\n")
        f.write(f"Average Radius: {base_metrics['shape']['average_radius']:.1f} mm\n\n")
        
        if morphed_geometry is not None:
            f.write(f"Morphed Geometry:\n")
            f.write(f"----------------\n")
            f.write(f"Volume: {morphed_metrics['shape']['volume']:.1f} mm³\n")
            f.write(f"Surface Area: {morphed_metrics['shape']['surface_area']:.1f} mm²\n")
            f.write(f"Centerline Length: {morphed_metrics['centerline']['centerline_length']:.1f} mm\n")
            f.write(f"Tortuosity: {morphed_metrics['centerline']['tortuosity']:.3f}\n")
            f.write(f"Sphericity: {morphed_metrics['shape']['sphericity']:.3f}\n")
            f.write(f"Convexity: {morphed_metrics['shape']['convexity']:.3f}\n")
            f.write(f"Average Radius: {morphed_metrics['shape']['average_radius']:.1f} mm\n\n")
            
            f.write(f"Relative Changes (%):\n")
            f.write(f"-------------------\n")
            for metric, change in metrics['relative_changes'].items():
                f.write(f"{metric.replace('_', ' ').title()}: {change:.1f}%\n")
    
    return metrics