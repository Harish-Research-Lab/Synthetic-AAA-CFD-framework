import numpy as np
from typing import Tuple
from .read_stl_file import read_stl_file

def computeNormals(stl_file: str) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Compute face normals, average normal, and reference point from an STL file.
    
    Args:
        stl_file (str): Path to the STL file
        
    Returns:
        Tuple[np.ndarray, np.ndarray, np.ndarray]: Tuple containing:
            - normals: Nx3 array of face normal vectors
            - avg_normal: 1x3 array of average normal vector
            - reference_point: 1x3 array of reference point coordinates
            
    Raises:
        FileNotFoundError: If the STL file cannot be opened
        ValueError: If normal vectors cannot be computed correctly
    """
    # Read the STL file
    vertices, faces = read_stl_file(stl_file)
    
    # Pre-allocate array for normals
    normals = np.zeros((faces.shape[0], 3))
    
    # Calculate the normals for each face
    for i in range(faces.shape[0]):
        # Get vertices of this face
        v1 = vertices[faces[i, 0]]
        v2 = vertices[faces[i, 1]]
        v3 = vertices[faces[i, 2]]
        
        # Calculate normal using cross product
        normal = np.cross(v2 - v1, v3 - v1)
        
        # Normalize the normal vector
        normal_length = np.linalg.norm(normal)
        if normal_length > 1e-10:  # Avoid division by zero
            normal = normal / normal_length
        
        normals[i] = normal
    
    # Calculate the average normal vector
    avg_normal = np.mean(normals, axis=0)
    
    # Normalize the average normal vector
    avg_normal_length = np.linalg.norm(avg_normal)
    if avg_normal_length > 1e-10:  # Avoid division by zero
        avg_normal = avg_normal / avg_normal_length
    
    # Validate the average normal vector
    if len(avg_normal) != 3 or np.any(np.isnan(avg_normal)):
        raise ValueError('Invalid normal vector calculated from the STL file.')
    
    # Get the reference point (first vertex of first face)
    reference_point = vertices[faces[0, 0]]
    
    return normals, avg_normal, reference_point

def verify_normals(normals: np.ndarray, avg_normal: np.ndarray) -> bool:
    """
    Verify that computed normals are valid.
    
    Args:
        normals: Nx3 array of face normal vectors
        avg_normal: 1x3 array of average normal vector
        
    Returns:
        bool: True if normals appear to be valid
    """
    # Check for NaN values
    if np.any(np.isnan(normals)) or np.any(np.isnan(avg_normal)):
        return False
    
    # Check that all normals are unit vectors
    normal_lengths = np.linalg.norm(normals, axis=1)
    if not np.allclose(normal_lengths, 1.0, atol=1e-5):
        return False
    
    # Check that average normal is a unit vector
    avg_normal_length = np.linalg.norm(avg_normal)
    if not np.isclose(avg_normal_length, 1.0, atol=1e-5):
        return False
    
    return True