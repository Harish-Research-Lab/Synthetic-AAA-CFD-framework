import numpy as np
from typing import Tuple
import struct

def read_stl_binary(filename: str) -> Tuple[np.ndarray, np.ndarray]:
    """
    Read a binary STL file and return vertices and faces.
    
    Args:
        filename (str): Path to the binary STL file
        
    Returns:
        Tuple[np.ndarray, np.ndarray]: Tuple containing:
            - vertices: Nx3 array of vertex coordinates
            - faces: Mx3 array of face indices
            
    Raises:
        FileNotFoundError: If the file cannot be opened
        ValueError: If the file format is invalid
    """
    try:
        with open(filename, 'rb') as fid:
            # Skip header
            fid.seek(80)
            
            # Read number of faces (using little endian '<')
            num_faces = struct.unpack('<I', fid.read(4))[0]
            
            # Pre-allocate arrays
            vertices = np.zeros((num_faces * 3, 3), dtype=np.float32)
            faces = np.zeros((num_faces, 3), dtype=np.int32)
            
            # Read face data
            for i in range(num_faces):
                # Skip normal vector (12 bytes = 3 * float32)
                fid.read(12)
                
                # Read vertices for this face (3 vertices * 3 coordinates * 4 bytes)
                v1 = struct.unpack('<3f', fid.read(12))
                v2 = struct.unpack('<3f', fid.read(12))
                v3 = struct.unpack('<3f', fid.read(12))
                
                # Skip attribute byte count (2 bytes)
                fid.read(2)
                
                # Store vertices
                vertices[i*3] = v1
                vertices[i*3 + 1] = v2
                vertices[i*3 + 2] = v3
                
                # Store face indices (using zero-based indexing)
                faces[i] = [i*3, i*3 + 1, i*3 + 2]
            
            return vertices, faces
            
    except FileNotFoundError:
        raise FileNotFoundError(f"Cannot open file: {filename}")
    except Exception as e:
        raise ValueError(f"Error reading STL file: {str(e)}")

def verify_stl_binary(filename: str) -> bool:
    """
    Verify that a binary STL file has the correct format.
    
    Args:
        filename (str): Path to the binary STL file
        
    Returns:
        bool: True if file appears to be valid binary STL
    """
    try:
        with open(filename, 'rb') as fid:
            # Read header and number of faces
            header = fid.read(80)
            num_faces = struct.unpack('<I', fid.read(4))[0]
            
            # Calculate expected file size:
            # - 80 bytes header
            # - 4 bytes for number of faces
            # - For each face:
            #   - 12 bytes normal vector (3 * float32)
            #   - 36 bytes vertices (9 * float32)
            #   - 2 bytes attribute
            expected_size = 84 + num_faces * 50
            
            # Get actual file size
            fid.seek(0, 2)  # Seek to end of file
            actual_size = fid.tell()
            
            return actual_size == expected_size
            
    except Exception:
        return False