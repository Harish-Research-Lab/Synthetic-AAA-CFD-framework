from dataclasses import dataclass
from typing import List, Tuple, Union
import numpy as np

@dataclass
class FVStruct:
    """Class to hold face-vertex structure data"""
    vertices: np.ndarray  # Nx3 array of vertex coordinates
    faces: np.ndarray    # Mx3 array of face indices

def stlwrite(fv: FVStruct, filename: str) -> None:
    """
    Create an ASCII STL file from given vertices and faces structure.
    
    Args:
        fv: FVStruct containing vertices and faces data
            vertices: Nx3 numpy array of vertex coordinates
            faces: Mx3 numpy array of face indices
        filename: Path to the output STL file
    
    Raises:
        ValueError: If vertices or faces data is invalid
        IOError: If unable to write to the specified file
    """
    # Input validation
    if not isinstance(fv.vertices, np.ndarray) or not isinstance(fv.faces, np.ndarray):
        raise ValueError("Vertices and faces must be numpy arrays")
    
    if fv.vertices.shape[1] != 3:
        raise ValueError("Vertices must be a Nx3 array")
    
    if fv.faces.shape[1] != 3:
        raise ValueError("Faces must be a Mx3 array")
        
    # Check if any face indices are out of bounds
    if np.any(fv.faces >= len(fv.vertices)) or np.any(fv.faces < 0):
        raise ValueError("Face indices out of bounds")
    
    try:
        with open(filename, 'w') as fid:
            # Write header
            fid.write(f'solid {filename}\n')
            
            # Write each triangle face
            for face in fv.faces:
                # Write facet normal (using 0 0 0 as placeholder)
                fid.write('  facet normal 0 0 0\n')
                fid.write('    outer loop\n')
                
                # Write the three vertices of this face
                for vertex_idx in face:
                    vertex = fv.vertices[vertex_idx]
                    fid.write(f'      vertex {vertex[0]:.6f} {vertex[1]:.6f} {vertex[2]:.6f}\n')
                
                # Close the face
                fid.write('    endloop\n')
                fid.write('  endfacet\n')
            
            # Write footer
            fid.write(f'endsolid {filename}\n')
            
    except IOError as e:
        raise IOError(f'Unable to write to {filename}: {str(e)}')
        
    return None

def save_stl_from_patches(patch_faces: Union[np.ndarray, List[List[int]]], 
                         vertices: Union[np.ndarray, List[List[float]]], 
                         filename: str) -> None:
    """
    Save an STL file from patch faces and vertices.
    
    Args:
        patch_faces: Mx3 array/list of face indices
        vertices: Nx3 array/list of vertex coordinates
        filename: Path to the output STL file
    
    Raises:
        ValueError: If face indices are invalid
        IOError: If unable to write to the specified file
    """
    # Convert inputs to numpy arrays if they aren't already
    patch_faces = np.array(patch_faces)
    vertices = np.array(vertices)
    
    # Check for invalid face indices
    max_index = np.max(patch_faces)
    if max_index >= vertices.shape[0]:
        raise ValueError(
            f"Invalid face index detected. Max index: {max_index}, "
            f"Number of vertices: {vertices.shape[0]}"
        )
    
    # Create face-vertex structure and write STL
    fv = FVStruct(vertices=vertices, faces=patch_faces)
    stlwrite(fv, filename)
    print(f'STL file saved: {filename}')