import numpy as np
from pathlib import Path
from vessel_spline import VesselSpline, AnatomicalPoint
from convert_points_for_cylinder import convert_points_for_cylinder
from cylinder_triangulation import Cylinder_Triangulation_Continuous_N

def analyze_vessel_geometry(
    anatomical_points: list, 
    num_centerline_points: int = 100,
    num_circumferential_points: int = 100,
    output_dir: str = 'src/vesselGen/geom_info'
) -> None:
    """
    Analyze vessel geometry and output detailed information about coordinates and normals.
    
    Args:
        anatomical_points: List of AnatomicalPoint objects containing coordinates and diameters
        num_centerline_points: Number of points to generate along centerline (default 100)
        num_circumferential_points: Number of vertices around each circular cross-section (default 100)
        output_dir: Directory to save output files (default 'src/vesselGen/geom_info')
    """
    # Create output directory if it doesn't exist
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Create vessel spline
    vessel = VesselSpline(anatomical_points, num_centerline_points)
    
    # Get centerline points and diameters
    centerline_2d = vessel.get_points()
    diameters = vessel.get_diameters()
    
    # Convert to 3D points
    centerline_3d = convert_points_for_cylinder(centerline_2d)
    
    # Generate mesh
    vertices, faces = Cylinder_Triangulation_Continuous_N(
        centerline_3d, 
        diameters,
        num_circumferential_points
    )

    # Add visualization
    visualize_vessel_geometry(
        centerline_3d,
        vertices,
        num_centerline_points,
        num_circumferential_points,
        anatomical_points,
        output_dir
    )
    
    # Output results to files
    
    # 1. Anatomical points
    with open(output_path / 'anatomical_points.txt', 'w') as f:
        f.write("Anatomical Points:\n")
        f.write("Name, X, Y, Diameter\n")
        for point in anatomical_points:
            f.write(f"{point.name}, {point.x:.2f}, {point.y:.2f}, {point.diameter:.2f}\n")
    
    # 2. Centerline points
    with open(output_path / 'centerline_points.txt', 'w') as f:
        f.write("Centerline Points:\n")
        f.write("Index, X, Y, Z\n")
        for i, point in enumerate(centerline_3d):
            f.write(f"{i}, {point[0]:.2f}, {point[1]:.2f}, {point[2]:.2f}\n")
    
    # 3. Calculate and output normals at cross sections
    with open(output_path / 'cross_section_normals.txt', 'w') as f:
        f.write("Cross Section Normals:\n")
        f.write("Index, Normal_X, Normal_Y, Normal_Z\n")
        
        # Calculate tangent vectors (normals to cross sections)
        tangents = np.zeros_like(centerline_3d)
        for i in range(len(centerline_3d)):
            if i == 0:
                tangents[i] = centerline_3d[1] - centerline_3d[0]
            elif i == len(centerline_3d) - 1:
                tangents[i] = centerline_3d[-1] - centerline_3d[-2]
            else:
                # Use central difference
                tangents[i] = centerline_3d[i+1] - centerline_3d[i-1]
            
            # Normalize
            tangents[i] = tangents[i] / np.linalg.norm(tangents[i])
            
            f.write(f"{i}, {tangents[i][0]:.4f}, {tangents[i][1]:.4f}, {tangents[i][2]:.4f}\n")
    
    # 4. Cross section points
    with open(output_path / 'cross_section_points.txt', 'w') as f:
        f.write("Cross Section Points:\n")
        f.write("Section_Index, Point_Index, X, Y, Z\n")
        
        for i in range(num_centerline_points):
            start_idx = (i * num_circumferential_points) + 1
            end_idx = ((i + 1) * num_circumferential_points) + 1
            
            for j, vertex in enumerate(vertices[start_idx:end_idx]):
                f.write(f"{i}, {j}, {vertex[0]:.2f}, {vertex[1]:.2f}, {vertex[2]:.2f}\n")
    
    # Print summary
    print("\nGeometry Analysis Summary:")
    print(f"Number of centerline points: {num_centerline_points}")
    print(f"Number of circumferential points: {num_circumferential_points}")
    print(f"Total number of vertices: {len(vertices)}")
    print(f"Total number of faces: {len(faces)}")
    print("\nOutput files generated in {output_dir}:")
    print("- anatomical_points.txt")
    print("- centerline_points.txt") 
    print("- cross_section_normals.txt")
    print("- cross_section_points.txt")


def visualize_vessel_geometry(
    centerline_3d: np.ndarray,
    vertices: np.ndarray,
    num_centerline_points: int,
    num_circumferential_points: int,
    anatomical_points: list,
    output_dir: str = 'src/vesselGen/geom_info'
) -> None:
    """
    Create 3D visualization of the vessel geometry including:
    - Centerline
    - Points on centerline 
    - Cross-sectional planes with normals
    - Points on each plane
    - Anatomical points
    
    Args:
        centerline_3d: Nx3 array of centerline points
        vertices: Mx3 array of mesh vertices
        num_centerline_points: Number of centerline points
        num_circumferential_points: Number of points per cross section
        anatomical_points: List of AnatomicalPoint objects
        output_dir: Directory to save plots
    """
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D
    from matplotlib.patches import Circle
    import matplotlib.colors as mcolors
    
    # Create figure
    fig = plt.figure(figsize=(15, 10))
    ax = fig.add_subplot(111, projection='3d')
    
    # Plot centerline
    ax.plot(centerline_3d[:, 0], centerline_3d[:, 1], centerline_3d[:, 2],
            'b-', linewidth=2, label='Centerline')
            
    # Plot points on centerline
    ax.scatter(centerline_3d[:, 0], centerline_3d[:, 1], centerline_3d[:, 2],
              c='blue', s=20, alpha=0.5)
              
    # Calculate and plot normals
    for i in range(len(centerline_3d)):
        # Calculate tangent/normal
        if i == 0:
            tangent = centerline_3d[1] - centerline_3d[0]
        elif i == len(centerline_3d) - 1: 
            tangent = centerline_3d[-1] - centerline_3d[-2]
        else:
            tangent = centerline_3d[i+1] - centerline_3d[i-1]
        tangent = tangent / np.linalg.norm(tangent)
        
        # Get plane points
        start_idx = (i * num_circumferential_points) + 1
        end_idx = ((i + 1) * num_circumferential_points) + 1
        plane_points = vertices[start_idx:end_idx]
        
        # Plot points on plane
        if i % 10 == 0:  # Plot every 10th plane to avoid clutter
            ax.scatter(plane_points[:, 0], plane_points[:, 1], plane_points[:, 2],
                      c='gray', s=1, alpha=0.3)
            
            # Plot normal vector
            normal_length = 5  # Adjust length of normal vectors
            ax.quiver(centerline_3d[i, 0], centerline_3d[i, 1], centerline_3d[i, 2],
                     tangent[0], tangent[1], tangent[2],
                     length=normal_length, color='red', alpha=0.5)
            
            # Plot simplified plane visualization
            # Get two perpendicular vectors to create plane
            v1 = np.array([1, 0, 0])
            if abs(np.dot(v1, tangent)) > 0.9:
                v1 = np.array([0, 1, 0])
            v1 = np.cross(tangent, v1)
            v1 = v1 / np.linalg.norm(v1)
            v2 = np.cross(tangent, v1)
            
            # Create plane points
            plane_size = 5  # Size of plane visualization
            pp = np.array([
                centerline_3d[i] + plane_size*v1 + plane_size*v2,
                centerline_3d[i] + plane_size*v1 - plane_size*v2,
                centerline_3d[i] - plane_size*v1 - plane_size*v2,
                centerline_3d[i] - plane_size*v1 + plane_size*v2,
                centerline_3d[i] + plane_size*v1 + plane_size*v2
            ])
            
            # Plot plane
            ax.plot(pp[:, 0], pp[:, 1], pp[:, 2], 
                   'g-', alpha=0.2)
    
    # Plot anatomical points
    anat_points = np.array([[p.x, p.y, 0] for p in anatomical_points])
    ax.scatter(anat_points[:, 0], anat_points[:, 1], anat_points[:, 2],
              c='red', s=100, label='Anatomical Points')
              
    # Add labels
    for i, point in enumerate(anatomical_points):
        ax.text(point.x, point.y, 0, 
                f'\n{point.name}\n(d={point.diameter:.1f}mm)',
                fontsize=8)
    
    # Set equal aspect ratio
    ax.set_box_aspect([1,1,1])
    
    # Labels and title
    ax.set_xlabel('X [mm]')
    ax.set_ylabel('Y [mm]')
    ax.set_zlabel('Z [mm]')
    ax.set_title('Vessel Geometry Visualization')
    
    # Add legend
    ax.legend()
    
    # Save plot
    output_path = Path(output_dir)
    plt.savefig(output_path / 'geometry_visualization.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    print("Geometry visualization saved as geometry_visualization.png")

# Example usage:
if __name__ == "__main__":
    # Example anatomical points
    points = [
        AnatomicalPoint(0, 0, "Inlet", 22.0),
        AnatomicalPoint(0, 10, "Control point", 22.0),
        AnatomicalPoint(0, 20, "Control point", 22.0),
        AnatomicalPoint(0, 30, "Neck 1", 22.0),
        AnatomicalPoint(10, 47, "Neck 2", 22.0),
        AnatomicalPoint(20, 75.95, "Maximum Aneurysm", 50.0),
        AnatomicalPoint(10, 124.9, "Distal", 18.0)
    ]
    
    analyze_vessel_geometry(
        points,
        num_centerline_points=100,
        num_circumferential_points=100,
        output_dir='src/vesselGen/geom_info'
    )