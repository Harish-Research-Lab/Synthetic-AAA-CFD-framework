from paraview.simple import *

def create_tawss_spreadsheet(foam_source, time_range, output_filename):
    """
    Create TAWSS spreadsheet for a specific time range
    
    Parameters:
    foam_source: The foam file source
    time_range: List of [start_step, end_step] for the cycle
    output_filename: Name of the output CSV file
    """
    # Extract the specific time steps for this cycle
    extractTimeSteps = ExtractTimeSteps(registrationName='ExtractTimeSteps', Input=foam_source)
    extractTimeSteps.SelectionMode = 'Select Time Range'
    extractTimeSteps.TimeStepRange = time_range
    
    # Calculate temporal statistics
    temporalStats = TemporalStatistics(registrationName='TemporalStatistics', Input=extractTimeSteps)
    temporalStats.ComputeMinimum = 0
    temporalStats.ComputeMaximum = 0
    temporalStats.ComputeStandardDeviation = 0
    
    # Create spreadsheet view
    spreadSheetView = CreateView('SpreadSheetView')
    spreadSheetView.ColumnToSort = ''
    spreadSheetView.BlockSize = 1024
    
    # Show data in view
    temporalStatsDisplay = Show(temporalStats, spreadSheetView, 'SpreadSheetRepresentation')
    
    # Export to CSV
    ExportView(output_filename, view=spreadSheetView)
    
    # Cleanup
    Delete(spreadSheetView)
    Delete(temporalStats)
    Delete(extractTimeSteps)
    del spreadSheetView
    del temporalStats
    del extractTimeSteps

# Load the foam file
foamfoam = OpenDataFile('foam.foam')
foamfoam.MeshRegions = ['wall']

# Define cycle ranges
timestep_ranges = {
    'cycle1': [0, 18],    
    'cycle2': [18, 37],  
    'cycle3': [37, 56],   
    'cycle4': [56, 76]   
}

# Create TAWSS spreadsheet for each cycle
for cycle_name, time_range in timestep_ranges.items():
    output_file = f'tawss_{cycle_name}.csv'
    create_tawss_spreadsheet(foamfoam, time_range, output_file)

# Cleanup
Delete(foamfoam)
del foamfoam