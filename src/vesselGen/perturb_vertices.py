import numpy as np
from typing import List, Union
from numpy.typing import NDArray
from src.vesselGen.lhsdesign import lhsdesign_modified

def perturb_vertices(vertices: NDArray, 
                    faces_combined: NDArray,
                    inlet_patch: NDArray,
                    outlet_patch: NDArray,
                    perturbation_range: float) -> NDArray:
    """
    Perturb vertices of a 3D mesh while keeping inlet and outlet vertices fixed.
    
    Args:
        vertices: Original vertex coordinates, shape (num_vertices, 3)
        faces_combined: Combined faces of the mesh, shape (num_faces, 3)
        inlet_patch: Faces forming the inlet patch, shape (num_inlet_faces, 3)
        outlet_patch: Faces forming the outlet patch, shape (num_outlet_faces, 3)
        perturbation_range: Maximum perturbation distance
        
    Returns:
        NDArray: Perturbed vertex coordinates with same shape as input vertices
    """
    # Get number of vertices
    num_vertices = vertices.shape[0]
    
    # Initialize perturbations with zeros
    perturbations = np.zeros_like(vertices)
    
    # Find unique vertices in inlet and outlet patches
    inlet_vertices = np.unique(inlet_patch)
    outlet_vertices = np.unique(outlet_patch)
    
    # Find vertices to perturb (all vertices except inlet and outlet)
    vertices_to_perturb = np.setdiff1d(
        np.arange(num_vertices),
        np.union1d(inlet_vertices, outlet_vertices)
    )
    
    if len(vertices_to_perturb) > 0:
        # Generate perturbations using LHS for the selected vertices
        # Create min and max ranges for x, y, z coordinates
        min_ranges = [-perturbation_range] * 3
        max_ranges = [perturbation_range] * 3
        
        # Generate perturbations using Latin Hypercube Sampling
        perturb_values, _ = lhsdesign_modified(
            len(vertices_to_perturb),
            min_ranges,
            max_ranges
        )
        
        # Apply the perturbations to the selected vertices
        perturbations[vertices_to_perturb] = perturb_values
    
    # Apply the perturbations to the vertices
    vertices_perturbed = vertices + perturbations
    
    # Ensure inlet and outlet vertices remain unchanged
    vertices_perturbed[inlet_vertices] = vertices[inlet_vertices]
    vertices_perturbed[outlet_vertices] = vertices[outlet_vertices]
    
    return vertices_perturbed