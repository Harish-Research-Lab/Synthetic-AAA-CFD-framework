# trace generated using paraview version 5.11.2
from paraview.simple import *
paraview.simple._DisableFirstRenderCameraReset()

LoadPalette(paletteName='WhiteBackground')

def setup_initial_view():
    renderView = GetActiveViewOrCreate('RenderView')
    renderView.CameraParallelProjection = 1
    renderView.OrientationAxesVisibility = 0
    return renderView

def create_transform(input_data, rotation, name):
    transform = Transform(registrationName=name, Input=input_data)
    transform.Transform = 'Transform'
    transform.Transform.Rotate = rotation
    HideInteractiveWidgets(proxy=transform.Transform)
    return transform

def setup_display(data, renderView):
    display = Show(data, renderView, 'UnstructuredGridRepresentation')
    display.Representation = 'Surface'
    return display

def hide_all_displays(renderView):
    for rep in renderView.Representations:
        if hasattr(rep, 'Input'):
            Hide(rep.Input, renderView)

def cleanup_view(renderView):
    hide_all_displays(renderView)
    Render(renderView)

def save_view(renderView, filename, camera_position, camera_focal_point, parallel_scale, resolution=[13200, 8976]):
    renderView.ResetCamera(False)
    renderView.CameraPosition = camera_position
    renderView.CameraFocalPoint = camera_focal_point
    renderView.CameraParallelScale = parallel_scale
    SaveScreenshot(f'./visualizations/{filename}', renderView, ImageResolution=resolution, TransparentBackground=1)

def create_tawss_visualization(transform, renderView, time_range):
    display = Show(transform, renderView)
    display.BlockSelectors = ['/wall']
    
    extractTimeSteps = ExtractTimeSteps(registrationName='ExtractTimeSteps', Input=transform)
    extractTimeSteps.SelectionMode = 'Select Time Range'
    extractTimeSteps.TimeStepRange = time_range
    
    temporalStats = TemporalStatistics(registrationName='TemporalStatistics', Input=extractTimeSteps)
    temporalStats.ComputeMinimum = 0
    temporalStats.ComputeMaximum = 0
    temporalStats.ComputeStandardDeviation = 0
    
    Hide(transform, renderView)
    statsDisplay = Show(temporalStats, renderView, 'GeometryRepresentation')
    statsDisplay.Representation = 'Surface'
    
    ColorBy(statsDisplay, ('POINTS', 'wallShearStress_average', 'Magnitude'))
    statsDisplay.RescaleTransferFunctionToDataRange(True, False)
    statsDisplay.SetScalarBarVisibility(renderView, True)
    
    tawssLUT = GetColorTransferFunction('wallShearStress_average')
    tawssLUT.ApplyPreset('Rainbow Uniform', True)
    
    tawssLUTColorBar = GetScalarBar(tawssLUT, renderView)
    tawssLUTColorBar.WindowLocation = 'Any Location'
    tawssLUTColorBar.Position = [0.1043181818181817, 0.2807486631016043]
    tawssLUTColorBar.ScalarBarLength = 0.49934046345811023
    
    return temporalStats, statsDisplay, tawssLUT

def find_tawss_range(transforms_dict, time_range):
    global_min = float('inf')
    global_max = float('-inf')
    renderView = GetActiveViewOrCreate('RenderView')
    temp_objects = []
    
    try:
        for transform in transforms_dict.values():
            temporalStats, statsDisplay, _ = create_tawss_visualization(transform, renderView, time_range)
            temp_objects.extend([temporalStats, statsDisplay])
            
            dataInfo = statsDisplay.Input.GetPointDataInformation().GetArray('wallShearStress_average')
            rng = dataInfo.GetRange(-1)
            global_min = min(global_min, rng[0])
            global_max = max(global_max, rng[1])
            Hide(temporalStats, renderView)
    finally:
        for obj in temp_objects:
            Delete(obj)
            del obj
        cleanup_view(renderView)
    
    return [global_min, global_max]

# Main execution
renderView = setup_initial_view()
layout = GetLayout()
layout.SetSize(1650, 1122)

# Load foam file
foamfoam = OpenDataFile('foam.foam')
if not foamfoam:
    raise RuntimeError("Could not load foam.foam file")

# Create transforms
transforms = {
    'front': create_transform(foamfoam, [0.0, 0.0, 180.0], 'Transform1'),
    'side1': create_transform(foamfoam, [0.0, 90.0, 180.0], 'Transform2'),
    'side2': create_transform(foamfoam, [0.0, 270.0, 180.0], 'Transform3')
}

Hide(foamfoam, renderView)
cleanup_view(renderView)

# Define time ranges for each cycle
timestep_ranges = {
    'cycle1': [0, 18],    
    'cycle2': [18, 37],  
    'cycle3': [37, 56],   
    'cycle4': [56, 76]   
}

# Find global TAWSS range
global_tawss_range = find_tawss_range(transforms, [0, 5])

# Generate TAWSS visualizations for each cycle
for cycle_name, timestep_range in timestep_ranges.items():
    for view_name, transform in transforms.items():
        cleanup_view(renderView)
        
        temporalStats, statsDisplay, tawssLUT = create_tawss_visualization(transform, renderView, timestep_range)
        tawssLUT.RescaleTransferFunction(global_tawss_range[0], global_tawss_range[1])
        
        save_view(renderView, f'tawss_{view_name}_{cycle_name}.png',
                 [-0.01922904932871461, -0.0646100237063365, 0.3015332296964253],
                 [-0.01922904932871461, -0.0646100237063365, -0.0015790509060025215],
                 0.0723292692450845)
        
        Delete(statsDisplay)
        Delete(temporalStats)
        del statsDisplay
        del temporalStats