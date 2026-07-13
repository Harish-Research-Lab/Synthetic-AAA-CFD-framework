import numpy as np
from pathlib import Path
from typing import Tuple, Optional
from .read_stl_file import read_stl_file  # Assuming this is already converted

def createBlockMeshDict(stl_file_path: str, output_file_path: str) -> None:
    """
    Create a blockMeshDict file for OpenFOAM based on STL file boundaries.
    
    Args:
        stl_file_path: Path to the input STL file
        output_file_path: Path where the blockMeshDict file should be written
        
    Raises:
        FileNotFoundError: If STL file cannot be found
        IOError: If there are issues reading STL or writing output
        ValueError: If STL vertices are invalid
    """
    try:
        # Hardcoded parameters
        offset = 25  # Example offset value
        refinement_factor = 2  # Example refinement factor
        
        # Convert paths to Path objects
        stl_path = Path(stl_file_path)
        output_path = Path(output_file_path)
        
        # Create output directory if it doesn't exist
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Read the STL file to get vertices
        vertices, _ = read_stl_file(stl_path)
        
        # Calculate the bounding box with offset
        min_bounds = np.min(vertices, axis=0) - offset
        max_bounds = np.max(vertices, axis=0) + offset
        
        # Define the vertices of the bounding box
        vertices_block = np.array([
            [min_bounds[0], min_bounds[1], min_bounds[2]],
            [max_bounds[0], min_bounds[1], min_bounds[2]],
            [max_bounds[0], max_bounds[1], min_bounds[2]],
            [min_bounds[0], max_bounds[1], min_bounds[2]],
            [min_bounds[0], min_bounds[1], max_bounds[2]],
            [max_bounds[0], min_bounds[1], max_bounds[2]],
            [max_bounds[0], max_bounds[1], max_bounds[2]],
            [min_bounds[0], max_bounds[1], max_bounds[2]]
        ])
        
        # Calculate the number of cells in each direction
        n_cells_x = int(np.ceil((max_bounds[0] - min_bounds[0]) * refinement_factor))
        n_cells_y = int(np.ceil((max_bounds[1] - min_bounds[1]) * refinement_factor))
        n_cells_z = int(np.ceil((max_bounds[2] - min_bounds[2]) * refinement_factor))
        
        # Write the blockMeshDict file
        with open(output_path, 'w') as f:
            # Write header
            f.write('FoamFile\n{\n')
            f.write('    version     2.0;\n')
            f.write('    format      ascii;\n')
            f.write('    class       dictionary;\n')
            f.write('    object      blockMeshDict;\n')
            f.write('}\n\n')
            f.write('convertToMeters 1;\n\n')
            
            # Write vertices
            f.write('vertices\n(\n')
            for vertex in vertices_block:
                f.write(f'    ({vertex[0]:.6f} {vertex[1]:.6f} {vertex[2]:.6f})\n')
            f.write(');\n\n')
            
            # Write blocks
            f.write('blocks\n(\n')
            f.write(f'    hex (0 1 2 3 4 5 6 7) ({n_cells_x} {n_cells_y} {n_cells_z}) simpleGrading (1 1 1)\n')
            f.write(');\n\n')
            
            # Write edges
            f.write('edges\n(\n')
            f.write(');\n\n')
            
            # Write boundary
            f.write('boundary\n(\n')
            f.write('    world\n    {\n')
            f.write('        type patch;\n')
            f.write('        faces\n        (\n')
            f.write('            (3 7 6 2)\n')
            f.write('            (0 4 7 3)\n')
            f.write('            (2 6 5 1)\n')
            f.write('            (1 5 4 0)\n')
            f.write('            (0 3 2 1)\n')
            f.write('            (4 5 6 7)\n')
            f.write('        );\n')
            f.write('    }\n')
            f.write(');\n\n')
            
            # Write merge patch pairs
            f.write('mergePatchPairs\n(\n')
            f.write(');\n')
            
        print(f'blockMeshDict created successfully at {output_path}')
        
    except Exception as e:
        raise Exception(f"Error in createBlockMeshDict: {str(e)}")

def verify_block_mesh_dict(file_path: str) -> bool:
    """
    Verify that a blockMeshDict file was created correctly.
    
    Args:
        file_path: Path to the blockMeshDict file to verify
        
    Returns:
        bool: True if file is valid, False otherwise
    """
    try:
        with open(file_path, 'r') as f:
            content = f.read()
            
        # Check for required sections
        required_sections = [
            'FoamFile',
            'vertices',
            'blocks',
            'edges',
            'boundary',
            'mergePatchPairs'
        ]
        
        return all(section in content for section in required_sections)
        
    except Exception:
        return False

