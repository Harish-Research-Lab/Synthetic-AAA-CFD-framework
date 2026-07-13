import numpy as np
from typing import List, Union
from pathlib import Path

def generateUFile(outputCSV: str) -> None:
    """
    Generate an OpenFOAM U file from velocity data.
    
    This function reads velocity-time data from a CSV file and generates an OpenFOAM U file
    by combining it with template header and footer content from specified files.
    
    Args:
        outputCSV (str): Path to the CSV file containing time and velocity components data
        
    Raises:
        FileNotFoundError: If input files cannot be found
        IOError: If there are issues reading input or writing output files
        ValueError: If the CSV data format is incorrect
        
    Note:
        The function expects:
        - A top template file at 'data/input/U/U_top.txt'
        - A bottom template file at 'data/input/U/U_bottom.txt'
        - CSV data with columns: [time, velocity_x, velocity_y, velocity_z]
    """
    try:
        # Define the hardcoded filenames
        u_top_file = Path('data/input/U/U_top.txt')
        u_bottom_file = Path('data/input/U/U_bottom.txt')
        output_u_file = Path('data/output/files/U')
        
        # Create output directory if it doesn't exist
        output_u_file.parent.mkdir(parents=True, exist_ok=True)

        # Read the top part of the U file
        with open(u_top_file, 'r') as f:
            u_top = f.read()

        # Read the corrected velocity-time data from the CSV file
        data = np.loadtxt(outputCSV, delimiter=',')

        # Validate data format
        if data.shape[1] != 4:  # time + 3 velocity components
            raise ValueError("CSV file must contain 4 columns: time and 3 velocity components")

        # Extract time and corrected velocity columns
        time = data[:, 0]
        velocity = data[:, 1:4]

        # Format the time-velocity pairs
        formatted_velocities = []
        for t, v in zip(time, velocity):
            formatted_velocities.append(
                f"  ({t:.4f} ({v[0]:.4f} {v[1]:.4f} {v[2]:.4f}))"
            )
        formatted_velocities = '\n'.join(formatted_velocities) + '\n'

        # Read the bottom part of the U file
        with open(u_bottom_file, 'r') as f:
            u_bottom = f.read()

        # Concatenate all parts to generate the final U file content
        u_file_content = u_top + formatted_velocities + u_bottom

        # Write the final U file content to the output file
        with open(output_u_file, 'w') as f:
            f.write(u_file_content)

        print(f'OpenFOAM U file has been written to {output_u_file}')

    except FileNotFoundError as e:
        raise FileNotFoundError(f"Required file not found: {str(e)}")
    except IOError as e:
        raise IOError(f"Error reading/writing files: {str(e)}")
    except ValueError as e:
        raise ValueError(f"Error processing data: {str(e)}")
    except Exception as e:
        raise Exception(f"Unexpected error in generateUFile: {str(e)}")

if __name__ == "__main__":
    # Example usage
    try:
        # Create sample data
        sample_data = np.array([
            [0.0, 1.0, 0.0, 0.0],
            [0.1, 2.0, 0.0, 0.0],
            [0.2, 1.5, 0.0, 0.0]
        ])
        
        # Save sample data to CSV
        test_csv = "test_velocity.csv"
        np.savetxt(test_csv, sample_data, delimiter=',')
        
        # Generate U file
        generateUFile(test_csv)
        
        # Read and print first few lines of generated file
        try:
            with open('data/output/files/U', 'r') as f:
                print("\nFirst few lines of generated U file:")
                for _ in range(5):
                    print(f.readline().rstrip())
        except FileNotFoundError:
            print("Note: Example output checking skipped - template files not present")
            
    except Exception as e:
        print(f"Error in example: {str(e)}")