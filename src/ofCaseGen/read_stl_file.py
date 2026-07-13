import numpy as np
from typing import Tuple
from .read_stl_ascii import read_stl_ascii
from .read_stl_binary import read_stl_binary

def read_stl_file(filename: str) -> Tuple[np.ndarray, np.ndarray]:
    """
    Read an STL file (either ASCII or binary) and return vertices and faces.
    
    Args:
        filename (str): Path to the STL file
        
    Returns:
        Tuple[np.ndarray, np.ndarray]: Tuple containing:
            - vertices: Nx3 array of vertex coordinates
            - faces: Mx3 array of face indices
            
    Raises:
        FileNotFoundError: If the file cannot be opened
        ValueError: If the file format is invalid
    """
    try:
        # First try to read the file in text mode to check format
        with open(filename, 'r') as fid:
            first_line = fid.readline().strip()
            
        # Check if file is ASCII (contains 'solid' in first line)
        if 'solid' in first_line.lower():
            try:
                vertices, faces = read_stl_ascii(filename)
                # Verify we got valid data from ASCII reader
                if len(vertices) > 0 and len(faces) > 0:
                    return vertices, faces
            except Exception:
                # If ASCII reading fails, try binary
                pass
                
        # If not ASCII or ASCII reading failed, try binary
        vertices, faces = read_stl_binary(filename)
        return vertices, faces
            
    except UnicodeDecodeError:
        # If we can't read it as text, it's definitely binary
        vertices, faces = read_stl_binary(filename)
        return vertices, faces
    except FileNotFoundError:
        raise FileNotFoundError(f"Cannot open file: {filename}")
    except Exception as e:
        raise ValueError(f"Error reading STL file: {str(e)}")