import numpy as np
from typing import Union

def convertVelocityComponents(
    cleanedData: np.ndarray,
    outputCSV: str,
    correctedNormal: np.ndarray
) -> None:
    """
    Convert velocity magnitudes to components along the corrected normal direction.

    This function takes cleaned velocity-time data and a corrected normal vector,
    converts the velocity magnitudes to 3D components along the normal direction,
    and saves the results to a CSV file.

    Args:
        cleanedData (np.ndarray): Array of shape (n, 2) containing [time, velocity] data
        outputCSV (str): Path to save the output CSV file
        correctedNormal (np.ndarray): Corrected normal vector of shape (3,)

    Raises:
        ValueError: If input arrays have incorrect shapes
        IOError: If unable to write to the output CSV file

    Example:
        >>> data = np.array([[0.0, 1.0], [0.1, 2.0]])
        >>> normal = np.array([1.0, 0.0, 0.0])
        >>> convertVelocityComponents(data, "output.csv", normal)
    """
    try:
        # Convert inputs to numpy arrays if they aren't already
        cleanedData = np.asarray(cleanedData)
        correctedNormal = np.asarray(correctedNormal)

        # Input validation
        if cleanedData.shape[1] != 2:
            raise ValueError("cleanedData must have shape (n, 2) containing [time, velocity]")
        if correctedNormal.shape != (3,):
            raise ValueError("correctedNormal must have shape (3,) for x,y,z components")

        # Extract time and velocity columns
        time = cleanedData[:, 0]
        velocity = cleanedData[:, 1]

        # Initialize the corrected velocity array
        correctedVelocity = np.zeros((len(velocity), 3))

        # Convert each velocity component along the corrected normal direction
        # Using broadcasting instead of a loop for better performance
        correctedVelocity = velocity[:, np.newaxis] * correctedNormal

        # Combine time and corrected velocity components into a new dataset
        newData = np.column_stack((time, correctedVelocity))

        # Write the new dataset to the output CSV file
        np.savetxt(outputCSV, newData, delimiter=',', fmt='%.6f')

        print(f'Corrected velocity components have been written to {outputCSV}.')

    except (ValueError, IOError) as e:
        raise type(e)(f"Error in convertVelocityComponents: {str(e)}")
