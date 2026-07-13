import numpy as np
from pathlib import Path
from typing import Union, List, Tuple

def createSnappyHexMeshDict(
    pointInside: Union[np.ndarray, List[float], Tuple[float, float, float]],
    shmTopFile: str,
    shmBottomFile: str,
    outputFile: str
) -> None:
    """
    Create a snappyHexMeshDict file for OpenFOAM by combining template files
    and inserting a point location.
    
    Args:
        pointInside: Point coordinates as array-like with 3 components [x, y, z]
        shmTopFile: Path to the top template file
        shmBottomFile: Path to the bottom template file
        outputFile: Path where the output file should be written
        
    Raises:
        FileNotFoundError: If template files cannot be found
        IOError: If there are issues reading templates or writing output
        ValueError: If pointInside doesn't have exactly 3 components
        
    Example:
        >>> point = [1.0, 2.0, 3.0]
        >>> createSnappyHexMeshDict(
        ...     point,
        ...     "templates/shm_top.txt",
        ...     "templates/shm_bottom.txt",
        ...     "output/snappyHexMeshDict"
        ... )
    """
    try:
        # Convert input point to numpy array and validate
        point = np.asarray(pointInside, dtype=float)
        if point.size != 3:
            raise ValueError("pointInside must have exactly 3 components (x, y, z)")
            
        # Convert paths to Path objects
        shm_top_path = Path(shmTopFile)
        shm_bottom_path = Path(shmBottomFile)
        output_path = Path(outputFile)
        
        # Create output directory if it doesn't exist
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Read the template files
        try:
            with open(shm_top_path, 'r') as f:
                top_content = f.read()
                
            with open(shm_bottom_path, 'r') as f:
                bottom_content = f.read()
                
        except FileNotFoundError:
            raise FileNotFoundError(f"Could not find template files at {shmTopFile} or {shmBottomFile}")
        
        # Format the point string
        point_str = f"({point[0]:.2f} {point[1]:.2f} {point[2]:.2f})"
        
        # Combine all content
        final_content = top_content + point_str + bottom_content
        
        # Write the output file
        try:
            with open(output_path, 'w') as f:
                f.write(final_content)
                
            print(f'snappyHexMeshDict created successfully at {output_path}')
            
        except IOError:
            raise IOError(f"Error writing to output file: {outputFile}")
            
    except Exception as e:
        raise Exception(f"Error in createSnappyHexMeshDict: {str(e)}")

if __name__ == "__main__":
    # Example usage
    try:
        # Sample point
        test_point = [1.0, 2.0, 3.0]
        
        # Create test files with sample content
        with open('test_top.txt', 'w') as f:
            f.write("// Top content\nLocationInMesh\n")
            
        with open('test_bottom.txt', 'w') as f:
            f.write("\n// Bottom content")
        
        # Generate snappyHexMeshDict
        createSnappyHexMeshDict(
            test_point,
            'test_top.txt',
            'test_bottom.txt',
            'test_output/snappyHexMeshDict'
        )
        
        # Read and print the generated file
        try:
            with open('test_output/snappyHexMeshDict', 'r') as f:
                print("\nGenerated file content:")
                print(f.read())
                
        except FileNotFoundError:
            print("Note: Could not read generated file for this example")
            
    except Exception as e:
        print(f"Error in example: {str(e)}")