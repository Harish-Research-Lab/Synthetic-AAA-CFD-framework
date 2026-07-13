from dataclasses import dataclass
from pathlib import Path
import json
import numpy as np
from scipy import stats
from typing import Dict, List, Any, Optional

@dataclass
class AAAGeometryParams:
    """Container for AAA geometric parameters"""
    neck_diameter_1: float  # Proximal neck diameter
    neck_diameter_2: float  # Distal neck diameter
    max_diameter: float     # Maximum aneurysm diameter
    distal_diameter: float  # Diameter at bifurcation
    
    def validate(self) -> bool:
        """Validate parameters are physiologically plausible"""
        if self.max_diameter <= self.neck_diameter_1:
            return False
        if self.max_diameter <= self.neck_diameter_2:
            return False
        if self.distal_diameter <= 0:
            return False
        return True
    
    def to_dict(self) -> Dict[str, float]:
        """Convert parameters to dictionary"""
        return {
            'neck_diameter_1': self.neck_diameter_1,
            'neck_diameter_2': self.neck_diameter_2,
            'max_diameter': self.max_diameter,
            'distal_diameter': self.distal_diameter
        }

class AAAParameterSampler:
    """Samples AAA parameters from pre-fitted distributions"""
    
    def __init__(self, fitted_params_path: str = 'data/processed/fitted_distributions.json'):
        """Initialize sampler with fitted distribution parameters"""
        with open(fitted_params_path, 'r') as f:
            self.fitted_params = json.load(f)
            
        # Validate available demographics
        self.available_genders = list(self.fitted_params['demographics'].keys())
        self.available_age_groups = list(self.fitted_params['demographics']['All'].keys())
    
    def _sample_from_distribution(self, dist_info: Dict[str, Any]) -> float:
        """Sample a value from the specified distribution"""
        dist_name = dist_info['distribution']
        params = dist_info['parameters']
        value_range = dist_info['range']
        
        # Create distribution instance
        if dist_name == 'norm':
            dist = stats.norm(*params)
        elif dist_name == 'lognorm':
            dist = stats.lognorm(*params)
        elif dist_name == 'gamma':
            dist = stats.gamma(*params)
        elif dist_name == 'weibull_min':
            dist = stats.weibull_min(*params)
        else:
            return dist_info['mean']
        
        # Sample until we get a valid value
        for _ in range(100):
            value = float(dist.rvs())
            if value_range[0] <= value <= value_range[1]:
                return value
        
        return dist_info['mean']
    
    def generate_parameters(self, gender: str, age_group: str) -> AAAGeometryParams:
        """Generate parameters for specified demographics"""
        if gender not in self.fitted_params['demographics']:
            raise ValueError(f"Invalid gender: {gender}. Available: {self.available_genders}")
        if age_group not in self.fitted_params['demographics'][gender]:
            raise ValueError(f"Invalid age group: {age_group}. Available: {self.available_age_groups}")
        
        demographic_data = self.fitted_params['demographics'][gender][age_group]
        params = {}
        
        for param_name, dist_info in demographic_data.items():
            params[param_name] = self._sample_from_distribution(dist_info)
        
        return AAAGeometryParams(
            neck_diameter_1=params['neck_diameter_1'],
            neck_diameter_2=params['neck_diameter_2'],
            max_diameter=params['max_diameter'],
            distal_diameter=params['distal_diameter']
        )
    
    def generate_virtual_population(
        self,
        num_variations: int,
        gender: str,
        age_group: str,
        max_attempts: int = 100
    ) -> List[AAAGeometryParams]:
        """Generate multiple valid parameter sets"""
        valid_params = []
        attempts = 0
        
        while len(valid_params) < num_variations and attempts < max_attempts:
            params = self.generate_parameters(gender, age_group)
            if params.validate():
                valid_params.append(params)
            attempts += 1
            
        if len(valid_params) < num_variations:
            print(f"Warning: Could only generate {len(valid_params)} valid variations "
                  f"after {attempts} attempts")
            
        return valid_params
    
    def save_parameters(self, params: AAAGeometryParams, output_path: Path) -> None:
        """Save parameters to JSON file"""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(params.to_dict(), f, indent=4)
    
    def load_parameters(self, input_path: Path) -> AAAGeometryParams:
        """Load parameters from JSON file"""
        with open(input_path, 'r') as f:
            params_dict = json.load(f)
        return AAAGeometryParams(**params_dict)

def get_case_name(gender: str, age_group: str, stat_var: int, morph_var: Optional[int] = None) -> str:
    """Generate standardized case name"""
    base_name = f"AAA_{gender}_{age_group}_stat_{stat_var}"
    if morph_var is not None:
        return f"{base_name}_morph_{morph_var}"
    return base_name

def setup_case_directory(base_dir: Path, case_name: str) -> Path:
    """Set up directory structure for a case"""
    case_dir = base_dir / case_name
    case_dir.mkdir(parents=True, exist_ok=True)
    
    # Create subdirectories
    (case_dir / "0").mkdir(exist_ok=True)
    (case_dir / "constant").mkdir(exist_ok=True)
    (case_dir / "system").mkdir(exist_ok=True)
    (case_dir / "parameters").mkdir(exist_ok=True)
    
    return case_dir