import numpy as np
import matplotlib.pyplot as plt
from .bezier_curve_points import bezier_curve_points

def compute_equidistant_points_and_normals(n: int, p: np.ndarray, num_points: int) -> tuple[np.ndarray, np.ndarray]:
    """
    Compute equidistant points and their normal vectors along a Bezier curve.
    
    Args:
        n (int): Number of control points
        p (np.ndarray): Control points as a matrix [[x1, y1], [x2, y2], ..., [xn, yn]]
        num_points (int): Number of equidistant points to generate
    
    Returns:
        tuple[np.ndarray, np.ndarray]: Tuple containing:
            - equidistant_points: Array of equidistant points along the curve
            - normals: Array of normal vectors at each point
    """
    # Generate the Bezier curve points
    P = bezier_curve_points(n, p)
    
    # Calculate approximate curve length
    diff_P = np.diff(P, axis=0)
    segment_lengths = np.sqrt(np.sum(diff_P**2, axis=1))
    curve_length = np.sum(segment_lengths)
    
    # Calculate target distance between points
    target_distance = curve_length / (num_points + 1)
    
    # Initialize equidistant points with first point
    equidistant_points = [P[0]]
    current_distance = 0
    
    # Find equidistant points
    for i in range(1, len(P)):
        segment_length = np.linalg.norm(P[i] - P[i-1])
        current_distance += segment_length
        if current_distance >= target_distance:
            equidistant_points.append(P[i])
            current_distance = 0
    
    # Include the last point
    if not np.array_equal(equidistant_points[-1], P[-1]):
        equidistant_points.append(P[-1])
    
    # Convert list to numpy array
    equidistant_points = np.array(equidistant_points)
    
    # Calculate normal vectors
    num_equidistant = len(equidistant_points)
    normals = np.zeros_like(equidistant_points)
    
    # Calculate normals for interior points
    for i in range(1, num_equidistant - 1):
        tangent = equidistant_points[i+1] - equidistant_points[i-1]
        normal = np.array([-tangent[1], tangent[0]])  # Rotate by 90 degrees
        normals[i] = normal / np.linalg.norm(normal)  # Normalize
    
    # Handle first and last points
    tangent_first = equidistant_points[1] - equidistant_points[0]
    normal_first = np.array([-tangent_first[1], tangent_first[0]])
    normals[0] = normal_first / np.linalg.norm(normal_first)
    
    tangent_last = equidistant_points[-1] - equidistant_points[-2]
    normal_last = np.array([-tangent_last[1], tangent_last[0]])
    normals[-1] = normal_last / np.linalg.norm(normal_last)
    
    # Plot the curve, equidistant points, and normals
    plt.figure()
    plt.plot(P[:, 0], P[:, 1], 'b-', linewidth=2, label='Bezier Curve')
    plt.plot(p[:, 0], p[:, 1], 'ro--', linewidth=1.5, label='Control Points')
    plt.quiver(equidistant_points[:, 0], equidistant_points[:, 1], 
              normals[:, 0], normals[:, 1], 
              color='g', label='Normals')
    
    plt.xlabel('X')
    plt.ylabel('Y')
    plt.title('Bezier Curve with Equidistant Points and Normals')
    plt.legend()
    plt.grid(True)
    plt.show()
    
    return equidistant_points, normals