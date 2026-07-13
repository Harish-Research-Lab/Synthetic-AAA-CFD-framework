from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from pathlib import Path
from src.vesselMorph.spherical_morphing import SphericalMorphParams
from src.vesselStats.parameter_sampler import AAAParameterSampler, AAAGeometryParams
from src.vesselGen.vessel_spline import AnatomicalPoint

@dataclass
class FrameworkPaths:
    """Container for framework file paths"""
    base_dir: Path = Path('data')
    input_dir: Path = Path('data/input')
    output_dir: Path = Path('data/output')
    geometry_dir: Path = Path('data/input/geometry')
    openfoam_dir: Path = Path('data/output/ofCases')
    fitted_params_file: Path = Path('data/processed/fitted_distributions.json')

@dataclass
class Demographics:
    """Demographics settings"""
    gender: str = 'F'
    age_group: str = '70-79'
    stat_variant: int = 2
    random_seed: Optional[int] = 42
    custom_suffix: str = 'trial_of_locations'  # New field for custom identification

@dataclass
class MorphingSettings:
    """Settings for geometric morphing"""
    enable_morphing: bool = True
    num_variations: int = 2
    save_control_points: bool = False
    visualize_morphing: bool = False
    generate_cases: bool = True
    
    # Spherical morphing parameters
    sphere_radius: float = 5.0
    num_control_points: int = 50
    influence_radius: float = 10.0
    fixed_percentage: float = 10.0
    buffer_percentage: float = 5.0
    smoothing_iterations: int = 2
    smoothing_factor: float = 0.5
    transition_power: float = 2.0

@dataclass
class VesselSettings:
    """Settings for vessel generation"""
    num_points: int = 100
    num_circumference_vertices: int = 100
    perturbation_range: float = 0.15
    num_cycles: int = 4

@dataclass
class AnatomicalTemplate:
    """Template for anatomical point positions"""
    # Coordinates in (x, y) format and descriptive names
    inlet_position: tuple = (0, 0)
    control_point1_position: tuple = (0, 10)
    control_point2_position: tuple = (0, 20)
    neck1_position: tuple = (0, 30)
    neck2_position: tuple = (10, 47)
    max_aneurysm_position: tuple = (20, 75.95)
    distal_position: tuple = (10, 124.9)
    
    def generate_points(self, params: AAAGeometryParams) -> List[AnatomicalPoint]:
        """Generate anatomical points from parameters using the template positions"""
        points = [
            # Proximal section
            AnatomicalPoint(self.inlet_position[0], self.inlet_position[1], 
                          "Inlet", params.neck_diameter_1),
            AnatomicalPoint(self.control_point1_position[0], self.control_point1_position[1], 
                          "Control point", params.neck_diameter_1),
            AnatomicalPoint(self.control_point2_position[0], self.control_point2_position[1], 
                          "Control point", params.neck_diameter_1),
            AnatomicalPoint(self.neck1_position[0], self.neck1_position[1], 
                          "Neck 1", params.neck_diameter_1),
            AnatomicalPoint(self.neck2_position[0], self.neck2_position[1], 
                          "Neck 2", params.neck_diameter_2),
            AnatomicalPoint(self.max_aneurysm_position[0], self.max_aneurysm_position[1], 
                          "Maximum Aneurysm", params.max_diameter),
            AnatomicalPoint(self.distal_position[0], self.distal_position[1], 
                          "Distal", params.distal_diameter)
        ]
        return points

class ConfigParams:
    """Main configuration class for AAA generation framework"""
    
    def __init__(self, stat_seed: Optional[int] = None):
        """
        Initialize configuration
        Args:
            stat_seed: Optional seed for statistical variation. If None, uses demographics.random_seed
        """
        # Initialize demographics
        self.demographics = Demographics()
        
        # Initialize paths
        self.paths = FrameworkPaths()
        
        # Create directories
        self._create_directories()
        
        # Set random seed based on statistical variation
        if stat_seed is not None:
            base_seed = stat_seed
        elif self.demographics.random_seed is not None:
            base_seed = self.demographics.random_seed
        else:
            import random
            base_seed = random.randint(0, 100000)
        
        # Store the base seed
        self.base_seed = base_seed
        
        # Set initial seed for geometric parameters
        import numpy as np
        np.random.seed(self.base_seed)
        
        # Initialize parameter sampler
        self.sampler = AAAParameterSampler(str(self.paths.fitted_params_file))
        
        # Generate geometric parameters
        self.geometry_params = self.sampler.generate_parameters(
            self.demographics.gender, 
            self.demographics.age_group
        )
        
        # Initialize anatomical template
        self.anatomical_template = AnatomicalTemplate()
        
        # Convert to anatomical points using the template
        self.anatomical_points = self.anatomical_template.generate_points(self.geometry_params)
        
        # Initialize vessel settings
        self.vessel_settings = VesselSettings()
        
        # Initialize morphing settings
        self.morphing_settings = MorphingSettings()
        
        # Get spherical morphing parameters
        self.spherical_morph_params = SphericalMorphParams(
            sphere_radius=self.morphing_settings.sphere_radius,
            num_control_points=self.morphing_settings.num_control_points,
            influence_radius=self.morphing_settings.influence_radius,
            fixed_percentage=self.morphing_settings.fixed_percentage,
            buffer_percentage=self.morphing_settings.buffer_percentage,
            smoothing_iterations=self.morphing_settings.smoothing_iterations,
            smoothing_factor=self.morphing_settings.smoothing_factor,
            transition_power=self.morphing_settings.transition_power
        )


    def set_morph_seed(self, morph_variant: int) -> None:
        """Set random seed for morphing based on base seed and morph variant"""
        import numpy as np
        morph_seed = self.base_seed * 1000 + morph_variant
        np.random.seed(morph_seed)
               
    
    def _create_directories(self) -> None:
        """Create necessary directory structure"""
        directories = [
            self.paths.input_dir,
            self.paths.output_dir,
            self.paths.geometry_dir,
            self.paths.openfoam_dir
        ]
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    def set_custom_suffix(self, suffix: str) -> None:
        """
        Set a custom suffix to differentiate between different parameter sets.
        
        Args:
            suffix: Custom identifier to add to case names
        """
        self.demographics.custom_suffix = suffix
    
    @property
    def base_name(self) -> str:
        """Generate base name for the current configuration"""
        base = (f'AAA_{self.demographics.gender}_'
                f'{self.demographics.age_group}_stat_'
                f'{self.demographics.stat_variant}')
        
        # Add custom suffix if it exists
        if self.demographics.custom_suffix:
            base += f'_{self.demographics.custom_suffix}'
            
        return base
    
    def generate_case_name(self, morph_variant: int) -> str:
        """Generate full case name including morphing variation"""
        return f"{self.base_name}_morph_{morph_variant}"
    
    def get_case_dir(self, morph_variant: int) -> Path:
        """Get directory path for a specific case"""
        return self.paths.openfoam_dir / self.generate_case_name(morph_variant)
    
    def save_configuration(self, case_dir: Path) -> None:
        """Save current configuration to case directory"""
        # Create parameters directory
        params_dir = case_dir / 'parameters'
        params_dir.mkdir(parents=True, exist_ok=True)
        
        # Save geometric parameters
        self.sampler.save_parameters(
            self.geometry_params,
            params_dir / 'geometry_params.json'
        )
        
        # Save complete configuration
        config_data = {
            'demographics': {
                'gender': self.demographics.gender,
                'age_group': self.demographics.age_group,
                'stat_variant': self.demographics.stat_variant
            },
            'vessel_settings': vars(self.vessel_settings),
            'morphing_settings': vars(self.morphing_settings),
            'anatomical_template': vars(self.anatomical_template)
        }
        
        import json
        with open(params_dir / 'config.json', 'w') as f:
            json.dump(config_data, f, indent=4)
    
    def validate(self) -> bool:
        """Validate current configuration"""
        # Check demographic parameters
        if self.demographics.gender not in self.sampler.available_genders:
            print(f"Invalid gender: {self.demographics.gender}")
            return False
        
        if self.demographics.age_group not in self.sampler.available_age_groups:
            print(f"Invalid age group: {self.demographics.age_group}")
            return False
        
        # Validate geometry parameters
        if not self.geometry_params.validate():
            print("Invalid geometry parameters")
            return False
        
        # Validate vessel settings
        if self.vessel_settings.num_points < 10:
            print("Insufficient number of points")
            return False
        
        if self.vessel_settings.num_circumference_vertices < 10:
            print("Insufficient number of circumference vertices")
            return False
        
        return True
    
    def print_summary(self) -> None:
        """Print summary of current configuration"""
        print("\nConfiguration Summary:")
        print("=====================")
        print(f"Demographics:")
        print(f"  Gender: {self.demographics.gender}")
        print(f"  Age Group: {self.demographics.age_group}")
        print(f"  Statistical Variation: {self.demographics.stat_variant}")
        
        print("\nGeometry Parameters:")
        print(f"  Neck Diameter 1: {self.geometry_params.neck_diameter_1:.2f} mm")
        print(f"  Neck Diameter 2: {self.geometry_params.neck_diameter_2:.2f} mm")
        print(f"  Maximum Diameter: {self.geometry_params.max_diameter:.2f} mm")
        print(f"  Distal Diameter: {self.geometry_params.distal_diameter:.2f} mm")
        
        print("\nMorphing Settings:")
        print(f"  Enabled: {self.morphing_settings.enable_morphing}")
        print(f"  Number of Variations: {self.morphing_settings.num_variations}")
        
        print("\nVessel Settings:")
        print(f"  Number of Points: {self.vessel_settings.num_points}")
        print(f"  Circumference Vertices: {self.vessel_settings.num_circumference_vertices}")
        print(f"  Number of Cycles: {self.vessel_settings.num_cycles}")
        
        print("\nAnatomical Points:")
        for point in self.anatomical_points:
            print(f"  {point.name}: ({point.x}, {point.y}) - Diameter: {point.diameter:.2f} mm")