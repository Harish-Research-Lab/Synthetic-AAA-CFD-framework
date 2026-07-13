from typing import Dict, Any
import numpy as np

def create_asymmetric_aneurysm(
    V: np.ndarray,
    num_points: int,
    num_circumference_vertices: int,
    asymmetry_params: Dict[str, Any]
) -> np.ndarray:
    """
    Create a localized asymmetric aneurysm by modifying vertex positions.

    Args:
        V: Original vertex matrix of shape (n, 3)
        num_points: Number of points along the centerline
        num_circumference_vertices: Number of vertices on each circumference
        asymmetry_params: Dictionary containing asymmetry parameters:
            - start_point: float, Normalized start point of aneurysm (0-1)
            - end_point: float, Normalized end point of aneurysm (0-1)
            - max_bulge: float, Maximum bulge outward in mm
            - bulge_function: callable, Function defining bulge profile
            - circumferential_variation: callable, Function defining variation around circumference

    Returns:
        np.ndarray: Modified vertex matrix with asymmetric aneurysm
    """
    # Initialize with original vertices
    V_asymmetric = V.copy()

    # Extract parameters
    start_point = round(asymmetry_params['start_point'] * num_points)
    end_point = round(asymmetry_params['end_point'] * num_points)
    max_bulge = asymmetry_params['max_bulge']
    bulge_function = asymmetry_params['bulge_function']
    circumferential_variation = asymmetry_params['circumferential_variation']

    # Identify the range of points to modify
    start_index = (start_point - 1) * num_circumference_vertices + 2
    end_index = end_point * num_circumference_vertices + 1

    # Process each plane of vertices
    for i in range(start_index, end_index + 1, num_circumference_vertices):
        # Calculate the current plane's center point
        vertices_in_plane = V[i:i+num_circumference_vertices]
        center = np.mean(vertices_in_plane, axis=0)

        # Calculate the plane's normal (approximated by direction to next center)
        if i + num_circumference_vertices >= V.shape[0]:
            normal = V[-1] - center
        else:
            next_vertices = V[i+num_circumference_vertices:i+2*num_circumference_vertices]
            next_center = np.mean(next_vertices, axis=0)
            normal = next_center - center
        
        # Normalize the normal vector
        normal = normal / np.linalg.norm(normal)

        # Apply asymmetric modification to all vertices in this plane
        for j in range(num_circumference_vertices):
            # Calculate angle for this vertex
            angle = (j) * 2 * np.pi / num_circumference_vertices
            
            # Calculate bulge factor
            t = (i - start_index) / (end_index - start_index)
            bulge_factor = bulge_function(t) * circumferential_variation(angle)

            # Calculate the radial direction for this vertex
            vertex_idx = i + j
            vertex = V[vertex_idx]
            radial_direction = vertex - center
            
            # Normalize radial direction, handling zero vectors
            radial_norm = np.linalg.norm(radial_direction)
            if radial_norm > 1e-10:  # Avoid division by zero
                radial_direction = radial_direction / radial_norm

                # Apply the bulge in the radial direction
                bulge = max_bulge * bulge_factor * radial_direction
                V_asymmetric[vertex_idx] = vertex + bulge

    return V_asymmetric