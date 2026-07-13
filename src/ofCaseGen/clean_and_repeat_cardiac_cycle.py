import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from typing import Union, Tuple

def cleanAndRepeatCardiacCycle(inputCSV: str, numCycles: int) -> np.ndarray:
    """
    Clean and repeat cardiac cycle data from a CSV file.
    
    This function reads velocity-time data, cleans it by removing negative times
    and duplicates, ensures the cycle ends at zero velocity, and repeats the cycle
    the specified number of times.
    
    Args:
        inputCSV (str): Path to the input CSV file containing time and velocity data
        numCycles (int): Number of times to repeat the cardiac cycle
        
    Returns:
        np.ndarray: Cleaned and repeated cardiac cycle data with shape (n, 2)
                   where columns are [time, velocity]
    
    Raises:
        ValueError: If no point near zero velocity is found
        FileNotFoundError: If the input CSV file cannot be found
    """
    try:
        # Read the velocity-time data from the CSV file
        data = pd.read_csv(inputCSV, header=None).values
        
        # Extract time and velocity columns
        time = data[:, 0]
        velocity = data[:, 1]
        
        # Combine time and velocity into a single array
        combined_data = np.column_stack((time, velocity))
        
        # Sort data by time
        sorted_data = combined_data[combined_data[:, 0].argsort()]
        
        # Remove rows with negative time values
        positive_time_data = sorted_data[sorted_data[:, 0] >= 0]
        
        # Remove duplicate times, keeping only the first occurrence
        unique_data = pd.DataFrame(positive_time_data).drop_duplicates(subset=[0], keep='first').values
        
        # Define threshold for zero velocity
        zero_threshold = 0.01
        
        # Find the last point where velocity is close to zero
        zero_velocity_indices = np.where(np.abs(unique_data[:, 1]) < zero_threshold)[0]
        if len(zero_velocity_indices) == 0:
            raise ValueError('No point near zero velocity found.')
            
        end_index = zero_velocity_indices[-1]
        
        # Trim the data
        cleaned_data = unique_data[:end_index + 1]
        
        # Ensure the first and last point are the same for smooth cycle repeat
        cleaned_data[-1, 1] = cleaned_data[0, 1]  # Set last velocity equal to first
        
        # Repeat the cycle for the desired number of cycles
        total_time = cleaned_data[-1, 0]  # Duration of one cycle
        full_cycle_data = cleaned_data.copy()
        
        for i in range(1, numCycles):
            next_cycle = cleaned_data.copy()
            next_cycle[:, 0] += i * total_time
            full_cycle_data = np.vstack((full_cycle_data, next_cycle))
        
        # # Plot velocity vs. time for the repeated cycles
        # plt.figure(figsize=(10, 6))
        # plt.plot(full_cycle_data[:, 0], full_cycle_data[:, 1], '-o')
        # plt.xlabel('Time (s)')
        # plt.ylabel('Velocity (m/s)')
        # plt.title(f'Velocity vs Time - {numCycles} Cardiac Cycles')
        # plt.grid(True)
        # plt.show()
        
        print('Processed and repeated cardiac cycles have been plotted.')
        
        return full_cycle_data
        
    except FileNotFoundError:
        raise FileNotFoundError(f"Could not find input CSV file: {inputCSV}")
    except Exception as e:
        raise Exception(f"Error processing cardiac cycle data: {str(e)}")
