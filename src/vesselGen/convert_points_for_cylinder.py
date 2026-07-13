import numpy as np
from typing import Union

def convert_points_for_cylinder(centers: Union[np.ndarray, list]) -> np.ndarray:
    """
    Convert input points to format required for cylinder generation.
    If input points are 2D, adds a third coordinate of zeros.
    
    Args:
        centers: Points array with either 2 or 3 columns
        
    Returns:
        np.ndarray: Points array with 3 columns
    """
    # Convert input to numpy array if it isn't already
    centers = np.asarray(centers)
    
    # Check if centers has only 2 columns and add a third column of zeros
    if centers.shape[1] == 2:
        centers = np.column_stack([centers, np.zeros(centers.shape[0])])
    
    return centers