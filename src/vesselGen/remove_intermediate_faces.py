import numpy as np

def remove_intermediate_faces(F, num_points, num_circumference_vertices):
    """
    Extract inlet, outlet, and wall patches from the triangulated mesh faces.
    
    Args:
        F (np.ndarray): Array of face indices
        num_points (int): Number of points along the centerline
        num_circumference_vertices (int): Number of vertices around each circular cross-section
    
    Returns:
        tuple: (F_combined, inlet_patch, outlet_patch, wall_patch)
            - F_combined: Combined faces array
            - inlet_patch: Faces forming the inlet
            - outlet_patch: Faces forming the outlet
            - wall_patch: Faces forming the wall
    """
    total_faces = F.shape[0]
    
    # Identify inlet and outlet patches
    inlet_start = total_faces - 2 * num_circumference_vertices
    outlet_start = total_faces - num_circumference_vertices
    
    inlet_patch = F[inlet_start:outlet_start]
    outlet_patch = F[outlet_start:]
    
    # The rest is the wall patch
    wall_patch = F[:inlet_start]
    
    # Combine all patches
    F_combined = np.vstack((inlet_patch, wall_patch, outlet_patch))
    
    return F_combined, inlet_patch, outlet_patch, wall_patch