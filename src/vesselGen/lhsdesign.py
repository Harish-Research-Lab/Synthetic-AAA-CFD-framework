import numpy as np
from typing import Tuple, Union

def lhsdesign(n: int, p: int) -> np.ndarray:
    """
    Python implementation of MATLAB's lhsdesign function.
    
    Args:
        n (int): Number of points to sample
        p (int): Number of variables/dimensions
        
    Returns:
        np.ndarray: n-by-p matrix containing Latin Hypercube samples
    """
    # Generate the intervals
    cut = np.linspace(0, 1, n + 1)    
    
    # Create centers of the intervals
    centers = (cut[1:] + cut[:-1]) / 2
    
    # Generate Latin Hypercube samples
    result = np.zeros((n, p))
    
    for i in range(p):
        result[:, i] = np.random.permutation(centers)
    
    return result

def lhsdesign_modified(n: int, 
                      min_ranges_p: Union[np.ndarray, list], 
                      max_ranges_p: Union[np.ndarray, list]) -> Tuple[np.ndarray, np.ndarray]:
    """
    Modified Latin Hypercube Sampling that allows for custom ranges.
    
    Args:
        n (int): Number of randomly generated data points
        min_ranges_p (array-like): 1xp or px1 vector containing minimum values for each variable
        max_ranges_p (array-like): 1xp or px1 vector containing maximum values for each variable
        
    Returns:
        Tuple[np.ndarray, np.ndarray]: 
            - X_scaled: nxp matrix of randomly generated variables within the min/max range
            - X_normalized: nxp matrix of randomly generated variables within the 0/1 range
            
    Example:
        >>> X_scaled, X_normalized = lhsdesign_modified(100, [-50, 100], [20, 300])
        >>> import matplotlib.pyplot as plt
        >>> fig, (ax1, ax2) = plt.subplots(2, 1)
        >>> ax1.plot(X_scaled[:, 0], X_scaled[:, 1], '*')
        >>> ax1.set_title('Random Variables')
        >>> ax1.set_xlabel('X1')
        >>> ax1.set_ylabel('X2')
        >>> ax1.grid(True)
        >>> ax2.plot(X_normalized[:, 0], X_normalized[:, 1], 'r*')
        >>> ax2.set_title('Normalized Random Variables')
        >>> ax2.set_xlabel('Normalized X1')
        >>> ax2.set_ylabel('Normalized X2')
        >>> ax2.grid(True)
        >>> plt.tight_layout()
        >>> plt.show()
    """
    # Convert inputs to numpy arrays if they aren't already
    min_ranges_p = np.array(min_ranges_p)
    max_ranges_p = np.array(max_ranges_p)
    
    # Get number of variables
    p = len(min_ranges_p)
    
    # Ensure arrays are column vectors
    min_ranges_p = min_ranges_p.reshape(-1, 1)
    max_ranges_p = max_ranges_p.reshape(-1, 1)
    
    # Calculate slope and offset
    slope = max_ranges_p - min_ranges_p
    offset = min_ranges_p
    
    # Create matrices of slopes and offsets
    SLOPE = np.tile(slope.T, (n, 1))
    OFFSET = np.tile(offset.T, (n, 1))
    
    # Generate normalized Latin Hypercube samples
    X_normalized = lhsdesign(n, p)
    
    # Scale the samples to the desired range
    X_scaled = SLOPE * X_normalized + OFFSET
    
    return X_scaled, X_normalized

def plot_lhs_example():
    """
    Example function to demonstrate the usage of lhsdesign_modified.
    """
    import matplotlib.pyplot as plt
    
    # Generate samples
    X_scaled, X_normalized = lhsdesign_modified(100, [-50, 100], [20, 300])
    
    # Create subplot
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 10))
    
    # Plot scaled variables
    ax1.plot(X_scaled[:, 0], X_scaled[:, 1], '*')
    ax1.set_title('Random Variables')
    ax1.set_xlabel('X1')
    ax1.set_ylabel('X2')
    ax1.grid(True)
    
    # Plot normalized variables
    ax2.plot(X_normalized[:, 0], X_normalized[:, 1], 'r*')
    ax2.set_title('Normalized Random Variables')
    ax2.set_xlabel('Normalized X1')
    ax2.set_ylabel('Normalized X2')
    ax2.grid(True)
    
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    # Example usage
    plot_lhs_example()