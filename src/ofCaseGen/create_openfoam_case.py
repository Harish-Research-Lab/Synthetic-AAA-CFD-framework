import os
import shutil
from pathlib import Path
from typing import List
import warnings

def createOpenFoamCase(base_case_folder: str, output_case_folder: str) -> None:
    """
    Create OpenFOAM case files by copying a base case and replacing necessary files.
    
    Args:
        base_case_folder: Path to the base case folder
        output_case_folder: Name of the output case folder
        
    Raises:
        FileNotFoundError: If required files or folders cannot be found
        IOError: If there are issues copying files
        
    Note:
        Expected directory structure:
        - data/input/of_base_case/
        - data/output/files/
        - data/input/geometry/<case_name>/
    """
    try:
        # Define paths using Path for better cross-platform compatibility
        input_folder = Path('data/input')
        output_folder = Path('data/output/files')
        output_case_path = Path('data/output/ofCases') / output_case_folder
        
        # Step 1: Copy the base case folder to the ofCases folder
        print("\nStep 1: Creating case directory structure...")
        output_case_path.mkdir(parents=True, exist_ok=True)
        
        base_case_path = input_folder / 'of_base_case'
        if not base_case_path.exists():
            raise FileNotFoundError(f"Base case not found at: {base_case_path}")
            
        # Copy base case contents
        shutil.copytree(base_case_path, output_case_path, dirs_exist_ok=True)
        
        # Step 2: Replace OpenFOAM dictionary files
        print("\nStep 2: Copying OpenFOAM dictionary files...")
        file_mappings = {
            'U': {'src': output_folder / 'U',
                 'dst': output_case_path / '0' / 'U'},
            'snappyHexMeshDict': {'src': output_folder / 'snappyHexMeshDict',
                                 'dst': output_case_path / 'system' / 'snappyHexMeshDict'},
            'blockMeshDict': {'src': output_folder / 'blockMeshDict',
                            'dst': output_case_path / 'system' / 'blockMeshDict'}
        }
        
        for file_name, paths in file_mappings.items():
            if not paths['src'].exists():
                raise FileNotFoundError(f"Source file not found: {paths['src']}")
            
            paths['dst'].parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(paths['src'], paths['dst'])
            print(f"Copied {file_name} to {paths['dst']}")
        
        # Step 3: Copy geometry files
        print("\nStep 3: Copying geometry files...")
        geometry_src_folder = input_folder / 'geometry' / output_case_folder
        tri_surface_folder = output_case_path / 'constant' / 'triSurface'
        
        # Create triSurface directory if it doesn't exist
        tri_surface_folder.mkdir(parents=True, exist_ok=True)
        
        # List of necessary STL files
        stl_files = ['wall.stl', 'inlet.stl', 'outlet.stl']
        
        for stl_file in stl_files:
            src_file = geometry_src_folder / stl_file
            dest_file = tri_surface_folder / stl_file
            
            if src_file.exists():
                shutil.copy2(src_file, dest_file)
                print(f"Copied {stl_file} to {tri_surface_folder}")
            else:
                warnings.warn(f"File not found: {src_file}")
        
        print(f"\nOpenFOAM case files created at: {output_case_path}")
        
    except Exception as e:
        raise Exception(f"Error in createOpenFoamCase: {str(e)}")

def verify_case_structure(case_path: Path) -> bool:
    """
    Verify that an OpenFOAM case directory has the expected structure.
    
    Args:
        case_path: Path to the OpenFOAM case directory
        
    Returns:
        bool: True if the case structure is valid, False otherwise
    """
    required_paths = [
        case_path / '0',
        case_path / 'system',
        case_path / 'constant',
        case_path / 'constant' / 'triSurface',
        case_path / 'system' / 'blockMeshDict',
        case_path / 'system' / 'snappyHexMeshDict',
        case_path / '0' / 'U'
    ]
    
    return all(path.exists() for path in required_paths)
