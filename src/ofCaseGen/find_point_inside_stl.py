import numpy as np
import warnings
from typing import Tuple, Dict
from .read_stl_file import read_stl_file

def findPointInsideSTL(filename: str) -> Tuple[float, float, float]:
    """
    Find a point that lies inside an STL mesh by analyzing its middle plane.
    
    Args:
        filename (str): Path to the STL file
        
    Returns:
        Tuple[float, float, float]: Coordinates (x, y, z) of a point inside the mesh
        
    Raises:
        FileNotFoundError: If the STL file cannot be opened
        ValueError: If no suitable point can be found
        
    Note:
        The function uses a middle plane analysis approach and returns
        the centroid of vertices projected onto this plane.
    """
    try:
        # Read the STL file
        vertices, _ = read_stl_file(filename)
        
        # Calculate the bounding box
        min_bounds = np.min(vertices, axis=0)
        max_bounds = np.max(vertices, axis=0)
        
        # Find middle plane along Y-axis
        mid_y = (min_bounds[1] + max_bounds[1]) / 2
        
        # Calculate tolerance (1% of Y range)
        tolerance = (max_bounds[1] - min_bounds[1]) * 0.01
        
        # Find vertices near the middle plane
        mid_plane_mask = np.abs(vertices[:, 1] - mid_y) < tolerance
        mid_plane_vertices = vertices[mid_plane_mask]
        
        if len(mid_plane_vertices) == 0:
            raise ValueError(
                'No vertices found near the middle plane. '
                'Consider adjusting the tolerance.'
            )
        
        # Project vertices onto the middle plane
        projected_vertices = mid_plane_vertices.copy()
        projected_vertices[:, 1] = mid_y
        
        # Calculate centroid
        center = np.mean(projected_vertices, axis=0)
        
        # Check distance to boundary
        dist_to_boundary = np.sqrt(
            np.sum((mid_plane_vertices - center) ** 2, axis=1)
        )
        min_dist_to_boundary = np.min(dist_to_boundary)
        
        if min_dist_to_boundary < tolerance:
            warnings.warn(
                'Point may be too close to the boundary. '
                'Consider adjusting the tolerance or checking the geometry.',
                RuntimeWarning
            )
        
        # Print the result
        print(
            f'Suggested point inside the wall: '
            f'[{center[0]:.6f}, {center[1]:.6f}, {center[2]:.6f}]'
        )
        
        return (float(center[0]), float(center[1]), float(center[2]))
        
    except Exception as e:
        raise ValueError(f"Error finding point inside STL: {str(e)}")

def verify_point_inside(
    vertices: np.ndarray, 
    point: Tuple[float, float, float], 
    tolerance: float = None
) -> bool:
    """
    Verify that a point appears to be inside the mesh bounds with some margin.
    
    Args:
        vertices: Nx3 array of mesh vertices
        point: Tuple of (x, y, z) coordinates to check
        tolerance: Optional margin from bounds (default: 1% of mesh size)
        
    Returns:
        bool: True if point appears to be valid
    """
    # Calculate mesh bounds
    min_bounds = np.min(vertices, axis=0)
    max_bounds = np.max(vertices, axis=0)
    
    if tolerance is None:
        # Default tolerance is 1% of the mesh size
        mesh_size = np.max(max_bounds - min_bounds)
        tolerance = mesh_size * 0.01
    
    # Convert point to numpy array for comparison
    point_array = np.array(point)
    
    # Check if point is within bounds with tolerance
    within_bounds = np.all(point_array > min_bounds + tolerance) and \
                   np.all(point_array < max_bounds - tolerance)
    
    return within_bounds

def estimate_mesh_quality(vertices: np.ndarray, faces: np.ndarray) -> Dict[str, float]:
    """
    Estimate the quality of the mesh for point finding.
    
    Args:
        vertices: Nx3 array of mesh vertices
        faces: Mx3 array of face indices
        
    Returns:
        Dict[str, float]: Dictionary containing quality metrics
    """
    # Calculate mesh properties
    bounds = np.max(vertices, axis=0) - np.min(vertices, axis=0)
    aspect_ratio = np.max(bounds) / np.min(bounds)
    
    # Calculate mesh density
    volume = np.prod(bounds)
    density = len(vertices) / volume if volume > 0 else 0
    
    return {
        'bounds_x': float(bounds[0]),
        'bounds_y': float(bounds[1]),
        'bounds_z': float(bounds[2]),
        'aspect_ratio': float(aspect_ratio),
        'vertex_count': float(len(vertices)),
        'face_count': float(len(faces)),
        'vertex_density': float(density)
    }