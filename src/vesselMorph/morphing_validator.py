from typing import Dict, Any, Optional, Tuple
import json
from .geometry_validator import GeometryValidator, ValidationResult
import numpy as np
from src.vesselStats.parameter_sampler import AAAParameterSampler
from typing import List
from config import ConfigParams


def validate_morphed_geometry(vertices: np.ndarray,
                            centerline: np.ndarray,
                            anatomical_points: List,
                            parameter_sampler: 'AAAParameterSampler',
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

def generate_valid_morphed_variation(
    geometry: Dict[str, Any],
    config: 'ConfigParams',
    max_attempts: int = 10
) -> Tuple[Optional[Dict[str, Any]], ValidationResult]:
    """
    Generate a morphed variation that passes clinical validation
    
    Args:
        geometry: Base geometry dictionary
        config: Configuration parameters
        max_attempts: Maximum number of morphing attempts
        
    Returns:
        Tuple containing:
        - Morphed geometry dictionary if valid, None if failed
        - Validation result for the final attempt
    """
    from .spherical_morphing import SphericalMeshMorpher
    
    print("\nGenerating clinically valid morphed variation...")
    
    for attempt in range(max_attempts):
        print(f"\nMorphing attempt {attempt + 1}/{max_attempts}")
        
        # Initialize morpher
        morpher = SphericalMeshMorpher(
            vertices=geometry['vertices'],
            faces=geometry['faces'],
            params=config.spherical_morph_params
        )
        
        # Apply random morphing
        morpher.random_spherical_movement()
        morpher.smooth_mesh()
        
        # Get morphed mesh
        morphed_mesh = morpher.get_current_mesh()
        
        # Create morphed geometry dictionary
        morphed = {
            'vertices': morphed_mesh['vertices'],
            'faces': morphed_mesh['faces'],
            'inlet_patch': geometry['inlet_patch'].copy(),
            'outlet_patch': geometry['outlet_patch'].copy(),
            'wall_patch': geometry['wall_patch'].copy(),
            'centerline': geometry['centerline'].copy(),
            'centerline3D': geometry['centerline3D'].copy(),
            'diameters': geometry['diameters'].copy()
        }
        
        # Validate the morphed geometry
        validation_result = validate_morphed_geometry(
            morphed['vertices'],
            morphed['centerline3D'],
            config.anatomical_points,
            config.sampler,
            config.demographics.gender,
            config.demographics.age_group
        )
        
        if validation_result.is_valid:
            print("\nGenerated valid morphed geometry:")
            print("Measurements:")
            for point, details in validation_result.validation_details.items():
                print(f"  {point}:")
                print(f"    Measurement: {validation_result.measurements[point]:.1f}mm")
                if 'percentile' in details:
                    print(f"    Percentile: {details['percentile']:.1f}")
                if 'range' in details:
                    print(f"    Valid Range: [{details['range'][0]:.1f}, {details['range'][1]:.1f}]mm")
            return morphed, validation_result
        else:
            print("\nInvalid morphed geometry:")
            for violation in validation_result.violations:
                print(f"  - {violation}")
    
    print(f"\nFailed to generate valid morphed geometry after {max_attempts} attempts")
    return None, validation_result
