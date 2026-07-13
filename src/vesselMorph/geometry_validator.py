import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
from scipy.spatial import distance
from scipy.stats import norm, lognorm, gamma, weibull_min
from src.vesselStats.parameter_sampler import AAAParameterSampler

@dataclass
class ValidationResult:
    """Store validation results for a morphed geometry"""
    is_valid: bool
    measurements: Dict[str, float]
    violations: List[str]
    validation_details: Dict[str, Dict]

class GeometryValidator:
    """Validate morphed geometries against statistical distributions"""
    
    def __init__(self, parameter_sampler: AAAParameterSampler):
        """
        Initialize validator with parameter sampler for statistical bounds
        
        Args:
            parameter_sampler: Instance of AAAParameterSampler with fitted distributions
        """
        self.sampler = parameter_sampler
        
        # Define mapping between measurement names and parameter names
        self.name_mapping = {
            'Inlet': 'neck_diameter_1',
            'Neck 1': 'neck_diameter_1',
            'Neck 2': 'neck_diameter_2',
            'Maximum Aneurysm': 'max_diameter',
            'Distal': 'distal_diameter'
        }
    
    def measure_cross_section(self, 
                            point: np.ndarray,
                            direction: np.ndarray,
                            vertices: np.ndarray,
                            search_radius: float = 2.0,
                            slice_thickness: float = 1.0) -> float:
        """
        Measure diameter at a cross-section perpendicular to given direction
        
        Args:
            point: Point on centerline
            direction: Direction vector at point
            vertices: All vertices of the mesh
            search_radius: Maximum radius to search for boundary points
            slice_thickness: Thickness of the slice to consider
            
        Returns:
            float: Measured diameter
        """
        # Normalize direction vector
        direction = direction / np.linalg.norm(direction)
        
        # Create plane perpendicular to direction
        # Get two orthogonal vectors in the plane
        v1 = np.array([1, 0, 0])
        if np.abs(np.dot(v1, direction)) > 0.9:
            v1 = np.array([0, 1, 0])
        plane_x = np.cross(direction, v1)
        plane_x /= np.linalg.norm(plane_x)
        plane_y = np.cross(direction, plane_x)
        
        # Find vertices near the plane
        vertex_vectors = vertices - point
        distances_along_direction = np.abs(np.dot(vertex_vectors, direction))
        in_slice = distances_along_direction < slice_thickness
        
        if not np.any(in_slice):
            return 0.0
            
        slice_vertices = vertices[in_slice]
        
        # Project vertices onto plane
        projected_points = []
        for vertex in slice_vertices:
            # Get vector from point to vertex
            vector = vertex - point
            # Project onto plane vectors
            x = np.dot(vector, plane_x)
            y = np.dot(vector, plane_y)
            projected_points.append([x, y])
            
        projected_points = np.array(projected_points)
        
        # Find maximum distance between any two points
        if len(projected_points) >= 2:
            distances = distance.cdist(projected_points, projected_points)
            max_diameter = np.max(distances)
            return max_diameter
        
        return 0.0
        
    def measure_anatomical_dimensions(self, 
                                   vertices: np.ndarray,
                                   centerline: np.ndarray,
                                   anatomical_points: List) -> Dict[str, float]:
        """
        Measure key anatomical dimensions from morphed geometry
        
        Args:
            vertices: Vertex coordinates of morphed mesh
            centerline: Centerline points
            anatomical_points: Original anatomical points
            
        Returns:
            Dict[str, float]: Measured dimensions at key anatomical locations
        """
        measurements = {}
        
        # Calculate centerline directions
        directions = np.zeros_like(centerline)
        directions[1:-1] = centerline[2:] - centerline[:-2]
        directions[0] = centerline[1] - centerline[0]
        directions[-1] = centerline[-1] - centerline[-2]
        
        for point in anatomical_points:
            if 'Control' not in point.name:  # Skip control points
                # Find closest centerline point
                distances = np.linalg.norm(centerline - np.array([point.x, point.y, 0]), axis=1)
                closest_idx = np.argmin(distances)
                
                # Measure diameter at this location
                diameter = self.measure_cross_section(
                    centerline[closest_idx],
                    directions[closest_idx],
                    vertices
                )
                
                measurements[point.name] = diameter
                
        return measurements

    def _validate_against_distribution(self,
                                    value: float,
                                    dist_info: Dict) -> Tuple[bool, Dict, Optional[str]]:
        """
        Validate a measurement against its fitted distribution
        
        Args:
            value: Measured value
            dist_info: Distribution information from fitted parameters
            
        Returns:
            Tuple containing:
            - bool: Whether the value is valid
            - Dict: Validation details
            - str or None: Violation message if invalid
        """
        dist_name = dist_info['distribution']
        params = dist_info['parameters']
        value_range = dist_info['range']
        
        # First check if value is within the allowed range
        if value < value_range[0] or value > value_range[1]:
            details = {
                'distribution': dist_name,
                'value': value,
                'range': value_range
            }
            violation = (f"Value {value:.1f}mm is outside allowed range "
                       f"[{value_range[0]:.1f}, {value_range[1]:.1f}]mm")
            return False, details, violation
            
        # Validate against specific distribution type
        try:
            if dist_name == 'norm':
                mu, sigma = params
                dist = norm(mu, sigma)
                percentile = dist.cdf(value) * 100
                details = {
                    'distribution': 'Normal',
                    'mean': mu,
                    'std': sigma,
                    'percentile': percentile,
                    'value': value
                }
                
            elif dist_name == 'lognorm':
                s, loc, scale = params
                dist = lognorm(s, loc, scale)
                percentile = dist.cdf(value) * 100
                details = {
                    'distribution': 'Log-normal',
                    'shape': s,
                    'location': loc,
                    'scale': scale,
                    'percentile': percentile,
                    'value': value
                }
                
            elif dist_name == 'gamma':
                a, loc, scale = params
                dist = gamma(a, loc, scale)
                percentile = dist.cdf(value) * 100
                details = {
                    'distribution': 'Gamma',
                    'shape': a,
                    'location': loc,
                    'scale': scale,
                    'percentile': percentile,
                    'value': value
                }
                
            elif dist_name == 'weibull_min':
                c, loc, scale = params
                dist = weibull_min(c, loc, scale)
                percentile = dist.cdf(value) * 100
                details = {
                    'distribution': 'Weibull',
                    'shape': c,
                    'location': loc,
                    'scale': scale,
                    'percentile': percentile,
                    'value': value
                }
                
            else:
                # If distribution type is unknown, fall back to range check only
                return True, {'distribution': 'Unknown', 'value': value}, None
            
            # Value is valid if it's within the distribution's range
            # and its probability density is non-zero
            is_valid = (value >= value_range[0] and 
                       value <= value_range[1] and 
                       dist.pdf(value) > 0)
            
            if not is_valid:
                violation = (f"Value {value:.1f}mm has zero probability under "
                           f"the fitted {dist_name} distribution")
                return False, details, violation
                
            return True, details, None
            
        except Exception as e:
            return False, {'error': str(e)}, f"Error validating against distribution: {str(e)}"
    
    def validate_measurements(self,
                            measurements: Dict[str, float],
                            gender: str,
                            age_group: str) -> ValidationResult:
        """
        Validate measurements against fitted statistical distributions
        
        Args:
            measurements: Dictionary of measured dimensions
            gender: Gender for statistical comparison
            age_group: Age group for statistical comparison
            
        Returns:
            ValidationResult: Validation results including violations
        """
        violations = []
        validation_details = {}
        
        # Get distributions for this demographic
        demographic_data = self.sampler.fitted_params['demographics'][gender][age_group]
        
        # Check each measurement against its distribution
        for point_name, measurement in measurements.items():
            if point_name in self.name_mapping:
                param_name = self.name_mapping[point_name]
                dist_info = demographic_data[param_name]
                
                # Validate against distribution
                is_valid, details, violation = self._validate_against_distribution(
                    measurement, 
                    dist_info
                )
                
                validation_details[point_name] = details
                
                if not is_valid and violation is not None:
                    violations.append(f"{point_name}: {violation}")
        
        return ValidationResult(
            is_valid=len(violations) == 0,
            measurements=measurements,
            violations=violations,
            validation_details=validation_details
        )

def validate_morphed_geometry(vertices: np.ndarray,
                            centerline: np.ndarray,
                            anatomical_points: List,
                            parameter_sampler: AAAParameterSampler,
                            gender: str,
                            age_group: str) -> ValidationResult:
    """
    Convenience function to validate a morphed geometry
    
    Args:
        vertices: Vertex coordinates of morphed mesh
        centerline: Centerline points
        anatomical_points: Original anatomical points
        parameter_sampler: Instance of AAAParameterSampler
        gender: Gender for statistical comparison
        age_group: Age group for statistical comparison
        
    Returns:
        ValidationResult: Validation results
    """
    validator = GeometryValidator(parameter_sampler)
    measurements = validator.measure_anatomical_dimensions(vertices, centerline, anatomical_points)
    return validator.validate_measurements(measurements, gender, age_group)