import numpy as np
from collections import OrderedDict
from typing import Tuple

def read_stl_ascii(filename: str) -> Tuple[np.ndarray, np.ndarray]:
    """
    Read an ASCII STL file and return vertices and faces.
    
    Args:
        filename (str): Path to the ASCII STL file
        
    Returns:
        Tuple[np.ndarray, np.ndarray]: Tuple containing:
            - vertices: Nx3 array of vertex coordinates
            - faces: Mx3 array of face indices
            
    Raises:
        FileNotFoundError: If the file cannot be opened
        ValueError: If the file format is invalid
    """
    try:
        with open(filename, 'r') as fid:
            # Initialize lists to store vertices and faces
            vertices = []
            faces = []
            # Use OrderedDict to maintain insertion order like MATLAB's containers.Map
            vertex_map = OrderedDict()
            vertex_count = 0
            face = []
            
            # Read the file line by line
            for line in fid:
                if 'vertex' in line:
                    # Extract vertex coordinates
                    coords = [float(x) for x in line.strip().split()[1:]]
                    if len(coords) != 3:
                        raise ValueError(f"Invalid vertex format in line: {line}")
                    
                    # Create a unique key for this vertex
                    vertex_key = f"{coords[0]},{coords[1]},{coords[2]}"
                    
                    # Check if we've seen this vertex before
                    if vertex_key in vertex_map:
                        vertex_idx = vertex_map[vertex_key]
                    else:
                        vertex_count += 1
                        vertex_map[vertex_key] = vertex_count - 1  # Zero-based indexing
                        vertex_idx = vertex_count - 1
                        vertices.append(coords)
                    
                    # Add to current face
                    face.append(vertex_idx)
                    
                    # If we have collected 3 vertices, we have a complete face
                    if len(face) == 3:
                        faces.append(face)
                        face = []
            
            # Convert lists to numpy arrays
            vertices = np.array(vertices)
            faces = np.array(faces)
            
            return vertices, faces
            
    except FileNotFoundError:
        raise FileNotFoundError(f"Cannot open file: {filename}")
    except Exception as e:
        raise ValueError(f"Error reading STL file: {str(e)}")