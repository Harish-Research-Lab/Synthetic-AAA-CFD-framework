from dataclasses import dataclass
from typing import Optional, List, Dict, Tuple
import numpy as np

@dataclass
class SphericalMorphParams:
    """Parameters for spherical morphing with buffer zones"""
    sphere_radius: float = 5.0         # Maximum radius of movement sphere
    num_control_points: int = 30       # Number of control points
    influence_radius: float = 20.0     # Radius of influence for each control point
    fixed_percentage: float = 10.0     # Percentage of vessel length for fixed regions
    buffer_percentage: float = 5.0     # Percentage of vessel length for buffer regions
    smoothing_iterations: int = 5      # Number of smoothing iterations
    smoothing_factor: float = 0.5      # Factor for smoothing (0-1)
    transition_power: float = 2.0      # Power for smooth transition function

class SphericalMeshMorpher:
    """Class for morphing vessel meshes using spherical control points with buffer zones"""
    
    def __init__(self, vertices: np.ndarray, faces: np.ndarray, params: Optional[SphericalMorphParams] = None):
        """Initialize morpher with mesh data"""
        self.original_vertices = vertices.copy()
        self.vertices = vertices.copy()
        self.faces = faces
        self.params = params or SphericalMorphParams()
        
        # Initialize regions and weights
        self._initialize_regions()
        # Initialize control points
        self.control_points = self._select_control_points()
        self.movement_spheres = self._create_movement_spheres()
    
    def _initialize_regions(self) -> None:
        """Initialize fixed, buffer, and morphable regions with smooth transitions"""
        # Find primary axis (longest dimension)
        ranges = np.ptp(self.vertices, axis=0)
        self.primary_axis = np.argmax(ranges)
        
        # Get coordinates along primary axis
        coords = self.vertices[:, self.primary_axis]
        coord_min, coord_max = np.min(coords), np.max(coords)
        coord_range = coord_max - coord_min
        
        # Calculate region boundaries
        fixed_size = coord_range * (self.params.fixed_percentage / 100)
        buffer_size = coord_range * (self.params.buffer_percentage / 100)
        
        # Calculate transition weights for smooth blending
        self.transition_weights = np.ones(len(self.vertices))
        
        # Inlet region weights
        inlet_start = coord_min
        inlet_end = inlet_start + fixed_size
        buffer_end = inlet_end + buffer_size
        
        inlet_mask = (coords >= inlet_start) & (coords <= inlet_end)
        inlet_buffer_mask = (coords > inlet_end) & (coords <= buffer_end)
        
        self.transition_weights[inlet_mask] = 0.0
        buffer_weights = self._calculate_buffer_weights(
            coords[inlet_buffer_mask],
            inlet_end,
            buffer_end
        )
        self.transition_weights[inlet_buffer_mask] = buffer_weights
        
        # Outlet region weights
        outlet_end = coord_max
        outlet_start = outlet_end - fixed_size
        buffer_start = outlet_start - buffer_size
        
        outlet_mask = (coords <= outlet_end) & (coords >= outlet_start)
        outlet_buffer_mask = (coords < outlet_start) & (coords >= buffer_start)
        
        self.transition_weights[outlet_mask] = 0.0
        buffer_weights = self._calculate_buffer_weights(
            coords[outlet_buffer_mask],
            buffer_start,
            outlet_start,
            reverse=True
        )
        self.transition_weights[outlet_buffer_mask] = buffer_weights
        
        # Store masks for different regions
        self.fixed_mask = inlet_mask | outlet_mask
        self.buffer_mask = inlet_buffer_mask | outlet_buffer_mask
        self.morphable_mask = ~(self.fixed_mask | self.buffer_mask)
        
        # Store fixed points
        self.fixed_vertices = self.vertices[self.fixed_mask].copy()
    
    def _calculate_buffer_weights(self, 
                                coords: np.ndarray, 
                                start: float, 
                                end: float, 
                                reverse: bool = False) -> np.ndarray:
        """Calculate smooth transition weights for buffer regions"""
        t = (coords - start) / (end - start)
        if reverse:
            t = 1 - t
        return t ** self.params.transition_power
    
    def _select_control_points(self) -> np.ndarray:
        """Select control points from morphable region only"""
        morphable_vertices = self.vertices[self.morphable_mask]
        indices = np.random.choice(
            len(morphable_vertices),
            min(self.params.num_control_points, len(morphable_vertices)),
            replace=False
        )
        return morphable_vertices[indices]
    
    def _create_movement_spheres(self) -> List[Dict]:
        """Create movement spheres for each control point"""
        return [
            {
                'center': point.copy(),
                'radius': self.params.sphere_radius,
                'current_position': point.copy()
            }
            for point in self.control_points
        ]
    
    def _apply_point_movement(self, point_idx: int, new_position: np.ndarray) -> None:
        """Apply movement of a single control point with smooth transitions"""
        sphere = self.movement_spheres[point_idx]
        sphere['current_position'] = new_position
        
        # Calculate displacement
        displacement = new_position - sphere['center']
        
        # Calculate influence on vertices
        distances = np.linalg.norm(self.vertices - sphere['center'], axis=1)
        influence = np.exp(-0.5 * (distances / self.params.influence_radius)**2)
        
        # Apply transition weights to influence
        influence *= self.transition_weights
        
        # Apply weighted displacement
        self.vertices += influence[:, np.newaxis] * displacement
    
    def smooth_mesh(self) -> None:
        """Apply Laplacian smoothing with transition weights"""
        for _ in range(self.params.smoothing_iterations):
            # Create adjacency mapping
            neighbors = [[] for _ in range(len(self.vertices))]
            for face in self.faces:
                for i in range(3):
                    neighbors[face[i]].extend([face[(i+1)%3], face[(i+2)%3]])
            
            # Remove duplicates
            neighbors = [list(set(n)) for n in neighbors]
            
            # Calculate new positions
            new_positions = np.zeros_like(self.vertices)
            for i in range(len(self.vertices)):
                if not self.fixed_mask[i] and neighbors[i]:
                    # Weight smoothing by transition weight
                    weight = self.transition_weights[i]
                    new_pos = np.mean(self.vertices[neighbors[i]], axis=0)
                    new_positions[i] = (1 - weight) * self.vertices[i] + weight * new_pos
                else:
                    new_positions[i] = self.vertices[i]
            
            # Update positions
            self.vertices = new_positions
            
            # Restore fixed vertices
            self.vertices[self.fixed_mask] = self.fixed_vertices
    
    def random_spherical_movement(self) -> None:
        """Apply random movement to all control points"""
        for i, sphere in enumerate(self.movement_spheres):
            # Generate random spherical coordinates
            theta = np.random.uniform(0, 2 * np.pi)
            phi = np.arccos(np.random.uniform(-1, 1))
            r = np.random.uniform(0, sphere['radius'])
            
            # Convert to Cartesian coordinates
            x = r * np.sin(phi) * np.cos(theta)
            y = r * np.sin(phi) * np.sin(theta)
            z = r * np.cos(phi)
            
            # Update position
            new_position = sphere['center'] + np.array([x, y, z])
            self._apply_point_movement(i, new_position)
    
    def reset(self) -> None:
        """Reset mesh to original state"""
        self.vertices = self.original_vertices.copy()
        self.movement_spheres = self._create_movement_spheres()
    
    def get_current_mesh(self) -> Dict[str, np.ndarray]:
        """Get current mesh state"""
        return {
            'vertices': self.vertices.copy(),
            'faces': self.faces.copy()
        }