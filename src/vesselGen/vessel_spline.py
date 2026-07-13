import numpy as np
from scipy.interpolate import CubicSpline
import matplotlib.pyplot as plt
from dataclasses import dataclass
from typing import List, Tuple, Optional

@dataclass
class AnatomicalPoint:
    """Class to store anatomical points with position and metadata"""
    x: float
    y: float
    name: str
    diameter: Optional[float] = None  # Vessel diameter at this point

class VesselSpline:
    """Class for generating and managing vessel centerline using cubic spline interpolation"""
    
    def __init__(self, anatomical_points: List[AnatomicalPoint], num_points: int = 100):
        """
        Initialize spline with anatomical points.
        
        Args:
            anatomical_points: List of AnatomicalPoint objects defining key positions
            num_points: Number of points to generate along the spline
        """
        self.anatomical_points = anatomical_points
        self.num_points = num_points
        
        # Extract coordinates and create spline
        self.points_array = np.array([[p.x, p.y] for p in anatomical_points])
        self._create_spline()
    
    def _create_spline(self) -> None:
        """Create the cubic spline interpolation"""
        # Use curve parameter based on cumulative distance
        t = np.zeros(len(self.points_array))
        for i in range(1, len(self.points_array)):
            t[i] = t[i-1] + np.linalg.norm(
                self.points_array[i] - self.points_array[i-1]
            )
        
        # Create splines for x and y coordinates
        self.spline_x = CubicSpline(t, self.points_array[:, 0])
        self.spline_y = CubicSpline(t, self.points_array[:, 1])
        
        # Create spline for diameters if available
        diameters = [p.diameter for p in self.anatomical_points]
        if all(d is not None for d in diameters):
            self.spline_diameter = CubicSpline(t, diameters)
        else:
            self.spline_diameter = None
        
        # Store parameter range
        self.t_range = t[-1]
    
    def get_points(self) -> np.ndarray:
        """
        Get points along the spline.
        
        Returns:
            np.ndarray: Array of shape (num_points, 2) containing (x, y) coordinates
        """
        t = np.linspace(0, self.t_range, self.num_points)
        return np.column_stack((self.spline_x(t), self.spline_y(t)))
    
    def get_diameters(self) -> Optional[np.ndarray]:
        """
        Get interpolated diameters along the spline.
        
        Returns:
            Optional[np.ndarray]: Array of diameters or None if diameters not available
        """
        if self.spline_diameter is None:
            return None
        
        t = np.linspace(0, self.t_range, self.num_points)
        return self.spline_diameter(t)
    
    def get_derivatives(self) -> np.ndarray:
        """
        Get first derivatives along the spline.
        
        Returns:
            np.ndarray: Array of shape (num_points, 2) containing (dx/dt, dy/dt)
        """
        t = np.linspace(0, self.t_range, self.num_points)
        return np.column_stack((
            self.spline_x.derivative()(t),
            self.spline_y.derivative()(t)
        ))
    
    def plot(self, show_points: bool = True, show_derivatives: bool = False) -> None:
        """
        Plot the spline and optionally show anatomical points and derivatives.
        
        Args:
            show_points: Whether to show anatomical points
            show_derivatives: Whether to show derivative vectors
        """
        plt.figure(figsize=(10, 8))
        
        # Plot the spline
        points = self.get_points()
        plt.plot(points[:, 0], points[:, 1], 'b-', linewidth=2, label='Vessel Centerline')
        
        if show_points:
            # Plot anatomical points
            plt.plot(self.points_array[:, 0], self.points_array[:, 1], 'ro', 
                    markersize=8, label='Anatomical Points')
            
            # Add labels for anatomical points
            for point in self.anatomical_points:
                plt.annotate(
                    f'{point.name}\n(d={point.diameter:.1f}mm)' if point.diameter else point.name,
                    (point.x, point.y),
                    xytext=(10, 10),
                    textcoords='offset points',
                    bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.5)
                )
        
        if show_derivatives:
            # Plot derivatives as arrows
            derivatives = self.get_derivatives()
            scale = 0.1 * self.t_range  # Scale factor for arrow length
            for i in range(0, len(points), len(points)//10):
                plt.arrow(
                    points[i, 0], points[i, 1],
                    derivatives[i, 0] * scale, derivatives[i, 1] * scale,
                    head_width=1, head_length=1.5, fc='g', ec='g', alpha=0.5
                )
        
        plt.grid(True)
        plt.xlabel('X')
        plt.ylabel('Y')
        plt.title('Vessel Centerline with Anatomical Points')
        plt.legend()
        plt.axis('equal')
        plt.show()
        
        # Plot diameter profile if available
        diameters = self.get_diameters()
        if diameters is not None:
            plt.figure(figsize=(10, 4))
            t = np.linspace(0, self.t_range, self.num_points)
            plt.plot(t, diameters, 'b-', linewidth=2)
            plt.grid(True)
            plt.xlabel('Distance along centerline')
            plt.ylabel('Diameter (mm)')
            plt.title('Vessel Diameter Profile')
            plt.show()