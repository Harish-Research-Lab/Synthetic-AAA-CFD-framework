from paraview.simple import *

def create_osi_spreadsheet(foam_source, time_range, output_filename):
    """
    Create OSI spreadsheet for a specific time range
    
    Parameters:
    foam_source: The foam file source
    time_range: List of [start_step, end_step] for the cycle
    output_filename: Name of the output CSV file
    """
    # Extract the specific time steps for this cycle
    extractTimeSteps = ExtractTimeSteps(registrationName='ExtractTimeSteps', Input=foam_source)
    extractTimeSteps.SelectionMode = 'Select Time Range'
    extractTimeSteps.TimeStepRange = time_range
    
    # Calculate instantaneous WSS magnitude
    instantWSS = Calculator(registrationName='InstantWSS', Input=extractTimeSteps)
    instantWSS.ResultArrayName = 'instantWSS'
    instantWSS.Function = 'mag(wallShearStress)'
    
    # Calculate temporal statistics
    temporalStats = TemporalStatistics(registrationName='TemporalStatistics', Input=instantWSS)
    temporalStats.ComputeMinimum = 0
    temporalStats.ComputeMaximum = 0
    temporalStats.ComputeStandardDeviation = 0
    
    # Calculate OSI
    osiCalc = Calculator(registrationName='OSICalculator', Input=temporalStats)
    osiCalc.ResultArrayName = 'OSI'
    osiCalc.Function = '0.5*(1 - mag(wallShearStress_average)/instantWSS_average)'
    
    # Create spreadsheet view
    spreadSheetView = CreateView('SpreadSheetView')
    spreadSheetView.ColumnToSort = ''
    spreadSheetView.BlockSize = 1024
    
    # Show data in view
    osiDisplay = Show(osiCalc, spreadSheetView, 'SpreadSheetRepresentation')
    
    # Export to CSV
    ExportView(output_filename, view=spreadSheetView)
    
    # Cleanup
    Delete(spreadSheetView)
    Delete(osiCalc)
    Delete(temporalStats)
    Delete(instantWSS)
    Delete(extractTimeSteps)
    del spreadSheetView
    del osiCalc
    del temporalStats
    del instantWSS
    del extractTimeSteps

# Load the foam file
foamfoam = OpenDataFile('foam.foam')

# Properties modified on foamfoam - use 'patch/wall' which works correctly
foamfoam.MeshRegions = ['patch/wall']

# Define cycle ranges
timestep_ranges = {
    'cycle1': [0, 18],    
    'cycle2': [18, 37],  
    'cycle3': [37, 56],   
    'cycle4': [56, 76]   
}

# Create OSI spreadsheet for each cycle
for cycle_name, time_range in timestep_ranges.items():
    output_file = f'postProcessing/osi_{cycle_name}.csv'
    create_osi_spreadsheet(foamfoam, time_range, output_file)

# Cleanup
Delete(foamfoam)
del foamfoam