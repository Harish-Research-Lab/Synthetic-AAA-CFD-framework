#!/usr/bin/env pvpython
"""
ParaView script to extract WSS percentiles at specific time points
This script reads OpenFOAM case data and calculates percentile values
of wall shear stress magnitude on the 'wall' patch.

Usage:
    pvpython extract_wss_percentiles_paraview.py [case_path]

If case_path is not provided, it will use the current directory.
"""

import sys
import os
import numpy as np
from paraview.simple import *

# Configuration
TIMES = [0.15, 1.1, 2.05, 3.0]  # Time points to analyze
PERCENTILES = [50, 75, 90, 95, 99]  # Percentiles to extract
BLOOD_DENSITY = 1060  # kg/m³ - for converting kinematic to dynamic WSS

def extract_wss_percentiles_at_time(reader, time_value, percentiles):
    """
    Extract WSS percentiles at a specific time point

    Args:
        reader: OpenFOAM reader object
        time_value: Time point to extract data from
        percentiles: List of percentile values to calculate (e.g., [50, 95, 99])

    Returns:
        Dictionary mapping percentile to value
    """
    # Set the time
    reader.UpdatePipeline(time_value)

    # Extract the wall patch
    extractBlock = ExtractBlock(Input=reader)
    extractBlock.BlockIndices = []

    # Find the wall patch block
    # Get all block names
    block_info = reader.GetProperty('PatchArrayStatus')
    n_patches = block_info.GetNumberOfElements()

    wall_block_index = None
    for i in range(n_patches):
        patch_name = block_info.GetElement(i)
        if 'wall' in patch_name.lower():
            wall_block_index = i
            print(f"  Found wall patch: {patch_name} at index {i}")
            break

    if wall_block_index is None:
        print("  ERROR: Could not find 'wall' patch")
        return None

    # Extract only the wall patch
    extractBlock.BlockIndices = [wall_block_index]
    extractBlock.UpdatePipeline()

    # Calculate WSS magnitude
    calculator = Calculator(Input=extractBlock)
    calculator.ResultArrayName = 'WSS_Magnitude'
    calculator.Function = 'mag(wallShearStress)'
    calculator.UpdatePipeline()

    # Get the data
    data = servermanager.Fetch(calculator)

    # Extract WSS magnitude values from all cells
    wss_values = []
    for i in range(data.GetNumberOfCells()):
        cell_data = data.GetCellData()
        wss_array = cell_data.GetArray('WSS_Magnitude')
        if wss_array:
            wss_val = wss_array.GetValue(i)
            # Convert kinematic to dynamic (Pa) by multiplying with density
            wss_val_pa = wss_val * BLOOD_DENSITY
            wss_values.append(wss_val_pa)

    # Also check point data if cell data is empty
    if len(wss_values) == 0:
        print("  No cell data found, checking point data...")
        for i in range(data.GetNumberOfPoints()):
            point_data = data.GetPointData()
            wss_array = point_data.GetArray('WSS_Magnitude')
            if wss_array:
                wss_val = wss_array.GetValue(i)
                wss_val_pa = wss_val * BLOOD_DENSITY
                wss_values.append(wss_val_pa)

    if len(wss_values) == 0:
        print("  ERROR: No WSS data found")
        return None

    # Convert to numpy array and calculate percentiles
    wss_array = np.array(wss_values)
    print(f"  Extracted {len(wss_values)} WSS values")
    print(f"  WSS range: {wss_array.min():.2f} - {wss_array.max():.2f} Pa")

    # Calculate percentiles
    percentile_values = {}
    for p in percentiles:
        percentile_val = np.percentile(wss_array, p)
        percentile_values[p] = percentile_val
        print(f"  {p}th percentile: {percentile_val:.4f} Pa")

    return percentile_values

def main():
    # Get case path from command line or use current directory
    if len(sys.argv) > 1:
        case_path = sys.argv[1]
    else:
        case_path = os.getcwd()

    print(f"Processing OpenFOAM case: {case_path}")

    # Look for .foam file or create one
    foam_file = None
    for f in os.listdir(case_path):
        if f.endswith('.foam') or f.endswith('.OpenFOAM'):
            foam_file = os.path.join(case_path, f)
            break

    if foam_file is None:
        # Create a .foam file
        foam_file = os.path.join(case_path, 'case.foam')
        with open(foam_file, 'w') as f:
            f.write('')
        print(f"Created {foam_file}")

    # Load the OpenFOAM case
    print("\nLoading OpenFOAM case...")
    reader = OpenFOAMReader(FileName=foam_file)
    reader.CaseType = 'Decomposed Case'
    reader.UpdatePipeline()

    # Get available time steps
    time_steps = reader.TimestepValues
    print(f"Available time steps: {len(time_steps)} steps")
    print(f"Time range: {time_steps[0]:.4f} - {time_steps[-1]:.4f}")

    # Prepare output
    output_dir = os.path.join(case_path, 'postProcessing', 'wssPercentiles_paraview')
    os.makedirs(output_dir, exist_ok=True)

    output_file = os.path.join(output_dir, 'wss_percentiles.csv')

    # Process each time point
    results = {}
    for time_val in TIMES:
        print(f"\n{'='*60}")
        print(f"Processing time: {time_val}")
        print(f"{'='*60}")

        # Find the closest available time step
        closest_time = min(time_steps, key=lambda x: abs(x - time_val))
        if abs(closest_time - time_val) > 0.01:
            print(f"WARNING: Requested time {time_val} not found, using closest: {closest_time}")

        # Extract percentiles
        percentile_values = extract_wss_percentiles_at_time(reader, closest_time, PERCENTILES)

        if percentile_values:
            results[closest_time] = percentile_values

    # Write results to CSV
    print(f"\n{'='*60}")
    print("Writing results to CSV...")
    print(f"{'='*60}")

    with open(output_file, 'w') as f:
        # Write header
        header = "Time," + ",".join([f"{p}th_Percentile_Pa" for p in PERCENTILES])
        f.write(header + "\n")

        # Write data
        for time_val in sorted(results.keys()):
            line = f"{time_val}"
            for p in PERCENTILES:
                line += f",{results[time_val][p]:.6f}"
            f.write(line + "\n")

    print(f"\nResults saved to: {output_file}")

    # Also create a text file with more detailed output
    txt_file = os.path.join(output_dir, 'wss_percentiles.txt')
    with open(txt_file, 'w') as f:
        f.write("WSS Percentiles Analysis\n")
        f.write("="*60 + "\n")
        f.write(f"Blood density: {BLOOD_DENSITY} kg/m³\n")
        f.write(f"Percentiles: {PERCENTILES}\n")
        f.write("="*60 + "\n\n")

        for time_val in sorted(results.keys()):
            f.write(f"Time: {time_val}\n")
            f.write("-"*40 + "\n")
            for p in PERCENTILES:
                f.write(f"  {p}th percentile: {results[time_val][p]:.6f} Pa\n")
            f.write("\n")

    print(f"Detailed results saved to: {txt_file}")
    print("\nDone!")

if __name__ == "__main__":
    main()
