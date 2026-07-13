import numpy as np
from typing import Union, Tuple

def correctNormal(avgNormal: np.ndarray, 
                 referencePoint: np.ndarray, 
                 insidePoint: np.ndarray) -> np.ndarray:
    """
    Correct the direction of a normal vector to ensure it points inward.
    
    This function verifies and corrects the direction of a normal vector by checking
    its orientation relative to a vector pointing from a reference point to an inside point.
    If the normal is pointing outward, it is flipped to point inward.
    
    Args:
        avgNormal (np.ndarray): The average normal vector to be corrected
        referencePoint (np.ndarray): A reference point on the surface
        insidePoint (np.ndarray): A point known to be inside the geometry
        
    Returns:
        np.ndarray: The corrected normal vector pointing inward
        
    Example:
        >>> avg_normal = np.array([1.0, 0.0, 0.0])
        >>> ref_point = np.array([0.0, 0.0, 0.0])
        >>> inside_point = np.array([-1.0, 0.0, 0.0])
        >>> corrected = correctNormal(avg_normal, ref_point, inside_point)
        >>> print(corrected)
        [-1.  0.  0.]
    """
    # Convert inputs to numpy arrays if they aren't already
    avgNormal = np.asarray(avgNormal)
    referencePoint = np.asarray(referencePoint)
    insidePoint = np.asarray(insidePoint)
    
    # Compute the vector from the reference point to the inside point
    vectorToInside = insidePoint - referencePoint
    
    # Check the direction using dot product
    if np.dot(avgNormal, vectorToInside) < 0:
        # If dot product is negative, normal points outward, so flip it
        correctedNormal = -avgNormal
    else:
        # Normal already points inward
        correctedNormal = avgNormal
        
    return correctedNormal