import numpy as np
from scipy.linalg import null_space

def Cylinder_Triangulation_Continuous_N(vc_points, d, num_circumference_vertices):
    """
    Generate triangulated mesh for a cylinder with varying diameter along a curve.
    
    Args:
        vc_points (np.ndarray): Points defining the centerline of the cylinder
        d (np.ndarray): Array of diameters corresponding to each point
        num_circumference_vertices (int): Number of vertices around each circular cross-section
    
    Returns:
        tuple: (V, F) where V is vertices array and F is faces array
    """
    num_points = vc_points.shape[0]
    
    # Calculate tangent vectors with smoothing
    tangents = np.zeros_like(vc_points)
    for i in range(num_points):
        if i == 0:
            tangents[i] = vc_points[1] - vc_points[0]
        elif i == num_points - 1:
            tangents[i] = vc_points[-1] - vc_points[-2]
        else:
            # Use 5-point moving average for smoothing
            start_idx = max(0, i-2)
            end_idx = min(num_points, i+2)
            tangents[i] = np.mean(np.diff(vc_points[start_idx:end_idx+1], axis=0), axis=0)
        tangents[i] = tangents[i] / np.linalg.norm(tangents[i])
    
    # Generate vertices
    V = np.zeros(((num_points * num_circumference_vertices) + 2, 3))
    V[0] = vc_points[0]  # Inlet center point
    V[-1] = vc_points[-1]  # Outlet center point
    
    # Initialize first perpendicular vector
    z = tangents[0]
    x = null_space(z[np.newaxis])[:, 0]
    y = np.cross(z, x)
    
    for i in range(num_points):
        z = tangents[i]
        
        # Update x and y to maintain continuity
        x = np.cross(y, z)
        x = x / np.linalg.norm(x)
        y = np.cross(z, x)
        y = y / np.linalg.norm(y)
        
        # Generate circle points
        theta = np.linspace(0, 2*np.pi, num_circumference_vertices+1)[:-1]
        
        # Create rotation matrix
        R = np.column_stack((x, y, z))
        
        # Generate circle in xy-plane and rotate
        circle_xy = np.column_stack((
            (d[i]/2) * np.cos(theta),
            (d[i]/2) * np.sin(theta),
            np.zeros_like(theta)
        ))
        circle = circle_xy @ R.T
        
        # Transform circle to global coordinates
        circle_global = circle + vc_points[i]
        
        # Store vertices
        start_idx = (i * num_circumference_vertices) + 1
        end_idx = ((i + 1) * num_circumference_vertices) + 1
        V[start_idx:end_idx] = circle_global
    
    # Generate faces for the cylinder wall
    F = np.zeros(((num_points-1) * num_circumference_vertices * 2, 3), dtype=int)
    for i in range(num_points - 1):
        for j in range(num_circumference_vertices):
            v1 = i * num_circumference_vertices + j + 1
            v2 = i * num_circumference_vertices + ((j + 1) % num_circumference_vertices) + 1
            v3 = (i + 1) * num_circumference_vertices + j + 1
            v4 = (i + 1) * num_circumference_vertices + ((j + 1) % num_circumference_vertices) + 1
            
            idx = (i * num_circumference_vertices + j) * 2
            F[idx] = [v1, v2, v4]
            F[idx + 1] = [v1, v4, v3]
    
    # Generate inlet and outlet faces
    F_inlet = np.zeros((num_circumference_vertices, 3), dtype=int)
    F_outlet = np.zeros((num_circumference_vertices, 3), dtype=int)
    
    for i in range(num_circumference_vertices):
        F_inlet[i] = [0, i+1, ((i + 1) % num_circumference_vertices) + 1]
        F_outlet[i] = [
            V.shape[0] - 1,
            V.shape[0] - num_circumference_vertices - 1 + i,
            V.shape[0] - num_circumference_vertices - 1 + ((i + 1) % num_circumference_vertices)
        ]
    
    # Combine all faces
    F = np.vstack((F, F_inlet, F_outlet))
    
    return V, F