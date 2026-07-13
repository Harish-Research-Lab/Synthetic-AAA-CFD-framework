import numpy as np
from pathlib import Path
from typing import Dict, Any, List
import shutil
import json

# Import from vesselGen
from src.vesselGen.vessel_spline import VesselSpline
from src.vesselGen.convert_points_for_cylinder import convert_points_for_cylinder
from src.vesselGen.cylinder_triangulation import Cylinder_Triangulation_Continuous_N
from src.vesselGen.remove_intermediate_faces import remove_intermediate_faces
from src.vesselGen.perturb_vertices import perturb_vertices
from src.vesselGen.save_stl_from_patches import save_stl_from_patches

# Import from vesselMorph
from src.vesselMorph.spherical_morphing import SphericalMeshMorpher
from src.vesselMorph.morphing_validator import generate_valid_morphed_variation

# Import from ofCaseGen
from src.ofCaseGen.compute_normals import computeNormals
from src.ofCaseGen.find_point_inside_stl import findPointInsideSTL
from src.ofCaseGen.correct_normal import correctNormal
from src.ofCaseGen.clean_and_repeat_cardiac_cycle import cleanAndRepeatCardiacCycle
from src.ofCaseGen.convert_velocity_components import convertVelocityComponents
from src.ofCaseGen.generate_u_file import generateUFile
from src.ofCaseGen.create_snappy_hex_mesh_dict import createSnappyHexMeshDict
from src.ofCaseGen.create_block_mesh_dict import createBlockMeshDict
from src.ofCaseGen.create_openfoam_case import createOpenFoamCase

# Import configuration
from config import ConfigParams

# Import visualization
from src.visualization.visualization import save_visualizations

def generate_base_geometry_without_perturbation(config: ConfigParams) -> Dict[str, Any]:
    """Generate base vessel geometry without perturbation"""
    print("\nGenerating base geometry...")
    
    # Create vessel spline from anatomical points
    vessel = VesselSpline(config.anatomical_points, config.vessel_settings.num_points)
    
    print("Step 1: Generating vessel centerline...")
    centerline_points = vessel.get_points()
    diameters = vessel.get_diameters()
    
    if diameters is None:
        raise ValueError("Vessel diameters must be specified for all anatomical points")
    
    print("Step 2: Converting points for cylinder generation...")
    vc_points = convert_points_for_cylinder(centerline_points)
    
    print("Step 3: Generating continuous cylinders...")
    V_combined, F_combined = Cylinder_Triangulation_Continuous_N(
        vc_points, 
        diameters, 
        config.vessel_settings.num_circumference_vertices
    )
    
    print("Step 4: Processing faces and creating patches...")
    F_combined, inlet_patch, outlet_patch, wall_patch = remove_intermediate_faces(
        F_combined, 
        config.vessel_settings.num_points, 
        config.vessel_settings.num_circumference_vertices
    )
    
    return {
        'vertices': V_combined,
        'faces': F_combined,
        'inlet_patch': inlet_patch,
        'outlet_patch': outlet_patch,
        'wall_patch': wall_patch,
        'centerline': centerline_points,
        'centerline3D': vc_points,
        'diameters': diameters
    }

def apply_perturbation(geometry: Dict[str, Any], config: ConfigParams) -> Dict[str, Any]:
    """Apply perturbation to a geometry"""
    print("Applying vertex perturbation...")
    perturbed_geometry = geometry.copy()
    
    perturbed_geometry['vertices'] = perturb_vertices(
        geometry['vertices'],
        geometry['faces'],
        geometry['inlet_patch'],
        geometry['outlet_patch'],
        config.vessel_settings.perturbation_range
    )
    
    return perturbed_geometry

def generate_morphed_variation(geometry: Dict[str, Any], config: ConfigParams) -> Dict[str, Any]:
    """Generate a single morphed variation"""
    print("\nApplying morphing transformation...")
    
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
    
    # Apply perturbation to morphed geometry
    print("Applying vertex perturbation to morphed geometry...")
    morphed_vertices = perturb_vertices(
        morphed_mesh['vertices'],
        morphed_mesh['faces'],
        geometry['inlet_patch'],
        geometry['outlet_patch'],
        config.vessel_settings.perturbation_range
    )
    
    # For morphed geometry, we'll use the same centerline as the base geometry
    # since the morphing maintains the general vessel path
    print("Adding centerline data to morphed geometry...")
    
    # Create variation geometry with all necessary data
    variation = {
        'vertices': morphed_vertices,
        'faces': morphed_mesh['faces'],
        'inlet_patch': geometry['inlet_patch'].copy(),
        'outlet_patch': geometry['outlet_patch'].copy(),
        'wall_patch': geometry['wall_patch'].copy(),
        'centerline': geometry['centerline'].copy(),
        'centerline3D': geometry['centerline3D'].copy(),
        'diameters': geometry['diameters'].copy()
    }
    
    return variation

def setup_openfoam_case(geometry: Dict[str, Any], config: ConfigParams, case_dir: Path) -> None:
    """Set up OpenFOAM case for a given geometry"""
    print(f"\nSetting up OpenFOAM case in {case_dir}")
    
    # Save geometry files
    geometry_dir = config.paths.geometry_dir / case_dir.name
    geometry_dir.mkdir(parents=True, exist_ok=True)
    
    print("Saving geometry files...")
    save_stl_from_patches(geometry['inlet_patch'], geometry['vertices'], 
                         geometry_dir / 'inlet.stl')
    save_stl_from_patches(geometry['outlet_patch'], geometry['vertices'], 
                         geometry_dir / 'outlet.stl')
    save_stl_from_patches(geometry['wall_patch'], geometry['vertices'], 
                         geometry_dir / 'wall.stl')
    
    # Compute normals and find interior point
    print("Computing normals...")
    normals, avgNormal, referencePoint = computeNormals(str(geometry_dir / 'inlet.stl'))
    insidePoint = findPointInsideSTL(str(geometry_dir / 'wall.stl'))
    correctedNormal = correctNormal(avgNormal, referencePoint, insidePoint)
    
    # Process velocity data
    print("Processing velocity data...")
    cleanedData = cleanAndRepeatCardiacCycle(
        'data/input/U/velocity_time.csv', 
        config.vessel_settings.num_cycles
    )
    
    # Generate velocity components and U file
    outputCSV = config.paths.output_dir / 'files' / 'corrected_velocity_time.csv'
    outputCSV.parent.mkdir(parents=True, exist_ok=True)
    
    convertVelocityComponents(cleanedData, str(outputCSV), correctedNormal)
    generateUFile(str(outputCSV))
    
    # Create mesh dictionaries
    print("Creating mesh dictionaries...")
    createSnappyHexMeshDict(
        insidePoint,
        'data/input/shm/shm_top.txt',
        'data/input/shm/shm_bottom.txt',
        str(config.paths.output_dir / 'files' / 'snappyHexMeshDict')
    )
    
    createBlockMeshDict(
        str(geometry_dir / 'wall.stl'),
        str(config.paths.output_dir / 'files' / 'blockMeshDict')
    )
    
    # Create OpenFOAM case
    print("Creating OpenFOAM case structure...")
    createOpenFoamCase('data/output/ofCases', case_dir.name)
    
    # Save configuration
    config.save_configuration(case_dir)


def main():
    """Main execution function"""
    print("Starting AAA Geometry Generation Framework")
    print("========================================")
    
    try:
        # Create initial configuration
        base_config = ConfigParams()
        num_statistical = base_config.demographics.stat_variant
        
        # Loop over statistical variations
        for stat_var in range(1, num_statistical + 1):
            print(f"\nProcessing Statistical Variation {stat_var}/{num_statistical}")
            
            # Create new config for this statistical variation with unique seed
            stat_seed = base_config.demographics.random_seed * 100 + stat_var if base_config.demographics.random_seed else stat_var
            config = ConfigParams(stat_seed=stat_seed)
            config.demographics.stat_variant = stat_var
            
            # Validate configuration
            if not config.validate():
                print(f"Invalid configuration for statistical variation {stat_var}")
                continue
            
            # Print configuration summary
            config.print_summary()
            
            # Generate base geometry without perturbation
            print("\nGenerating base geometry...")
            base_geometry = generate_base_geometry_without_perturbation(config)
            
            # Create perturbed version of base geometry
            perturbed_base_geometry = apply_perturbation(base_geometry, config)
            
            # Get velocity data
            velocity_data = cleanAndRepeatCardiacCycle(
                'data/input/U/velocity_time.csv', 
                config.vessel_settings.num_cycles
            )
            
            # Set up case directory for base geometry
            base_case_name = config.base_name
            base_case_dir = config.paths.openfoam_dir / base_case_name
            
            # Generate visualizations for base geometry
            print("\nGenerating visualizations for base geometry...")
            save_visualizations(
                config,
                perturbed_base_geometry,  # Use perturbed geometry for visualization
                base_geometry['centerline'],
                velocity_data,
                base_case_dir
            )
            
            # Set up OpenFOAM case for base geometry
            print(f"\nSetting up OpenFOAM case for base geometry in {base_case_dir}")
            setup_openfoam_case(perturbed_base_geometry, config, base_case_dir)
            
            # Process morphing variations if enabled
            if config.morphing_settings.enable_morphing:
                num_morphed = config.morphing_settings.num_variations
                print(f"\nGenerating {num_morphed} morphed variations...")
                
                successful_variations = 0
                morph_var = 1
                max_attempts_per_variation = 10
                
                while successful_variations < num_morphed:
                    print(f"\nProcessing Morphed Variation {successful_variations + 1}/{num_morphed}")
                    print(f"Attempt {morph_var}")
                    
                    # Set seed for this morphing variation
                    config.set_morph_seed(morph_var)
                    
                    # Generate and validate morphed geometry (using unperturbed base geometry)
                    morphed_geometry, validation_result = generate_valid_morphed_variation(
                        base_geometry,  # Use unperturbed base geometry for morphing
                        config,
                        max_attempts=max_attempts_per_variation
                    )
                    
                    if morphed_geometry is not None:
                        # Apply perturbation to valid morphed geometry
                        perturbed_morphed_geometry = apply_perturbation(morphed_geometry, config)
                        
                        # Set up case directory for morphed geometry
                        case_dir = config.get_case_dir(successful_variations + 1)
                        
                        # Generate visualizations for morphed geometry
                        print("\nGenerating visualizations for morphed geometry...")
                        save_visualizations(
                            config,
                            perturbed_base_geometry,  # Original perturbed geometry for reference
                            base_geometry['centerline'],
                            velocity_data,
                            case_dir,
                            perturbed_morphed_geometry  # Perturbed morphed geometry
                        )
                        
                        # Set up OpenFOAM case
                        setup_openfoam_case(perturbed_morphed_geometry, config, case_dir)
                        
                        # Save validation results
                        validation_file = case_dir / 'parameters' / 'validation_results.json'
                        validation_file.parent.mkdir(parents=True, exist_ok=True)
                        
                        validation_data = {
                            'measurements': validation_result.measurements,
                            'validation_details': validation_result.validation_details,
                            'attempt_number': morph_var
                        }
                        
                        with open(validation_file, 'w') as f:
                            json.dump(validation_data, f, indent=4)
                        
                        successful_variations += 1
                        print(f"\nCompleted valid morphed variation {successful_variations}")
                        
                        # Print validation details
                        print("\nValidation Results:")
                        print("------------------")
                        for point, details in validation_result.validation_details.items():
                            measurement = validation_result.measurements[point]
                            print(f"\n{point}:")
                            print(f"  Measurement: {measurement:.1f}mm")
                            if 'percentile' in details:
                                print(f"  Percentile: {details['percentile']:.1f}")
                            if 'range' in details:
                                print(f"  Valid Range: [{details['range'][0]:.1f}, "
                                     f"{details['range'][1]:.1f}]mm")
                    else:
                        print(f"\nFailed to generate valid geometry on attempt {morph_var}")
                        print("Validation failures:")
                        for violation in validation_result.violations:
                            print(f"  - {violation}")
                    
                    morph_var += 1
                    if morph_var > config.morphing_settings.num_variations * 10:
                        print(f"\nWarning: Stopping after {morph_var-1} attempts - unable to generate "
                              f"enough valid variations (generated {successful_variations}/{num_morphed})")
                        break
                
                if successful_variations < num_morphed:
                    print(f"\nNote: Only generated {successful_variations} valid morphed variations "
                          f"out of requested {num_morphed}")
            
            print(f"\nCompleted statistical variation {stat_var}")
        
        print("\nFramework execution completed successfully.")
        
    except Exception as e:
        print(f"\nError during execution: {str(e)}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    main()