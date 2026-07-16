#### import the simple module from the paraview
from paraview.simple import *

# Load the foam file
foamfoam = OpenDataFile('foam.foam')

# Properties modified on foamfoam
foamfoam.MeshRegions = ['wall']  # locally 'patch/wall' worked

# Create a new 'Integrate Variables'
integrateVariables1 = IntegrateVariables(Input=foamfoam)

# Create a new 'Plot Data Over Time'
plotDataOverTime1 = PlotDataOverTime(Input=integrateVariables1)

# Create a new 'SpreadSheet View'
spreadSheetView1 = CreateView('SpreadSheetView')
spreadSheetView1.ColumnToSort = ''
spreadSheetView1.BlockSize = 1024

# Show data in spreadsheet view
plotDataOverTime1Display = Show(plotDataOverTime1, spreadSheetView1, 'SpreadSheetRepresentation')

# Export view to CSV
ExportView('wss_time.csv', view=spreadSheetView1)