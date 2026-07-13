# trace generated using paraview version 5.11.2
from paraview.simple import *
paraview.simple._DisableFirstRenderCameraReset()

LoadPalette(paletteName='WhiteBackground')

def setup_initial_view():
    """Initialize the basic view settings"""
    renderView = GetActiveViewOrCreate('RenderView')
    renderView.CameraParallelProjection = 1
    renderView.OrientationAxesVisibility = 0
    return renderView

def reset_camera(renderView):
    """Reset camera to fit data"""
    renderView.ResetCamera(False)

def create_transform(input_data, rotation, name):
    """Create a transform with specified rotation"""
    transform = Transform(registrationName=name, Input=input_data)
    transform.Transform = 'Transform'
    transform.Transform.Rotate = rotation
    # Hide interactive widgets
    HideInteractiveWidgets(proxy=transform.Transform)
    return transform

def setup_display(data, renderView, opacity=1.0):
    """Set up common display properties"""
    display = Show(data, renderView, 'UnstructuredGridRepresentation')
    display.Representation = 'Surface'
    display.Opacity = opacity
    return display

def hide_all_displays(renderView):
    """Hide all displays in the current view"""
    for rep in renderView.Representations:
        if hasattr(rep, 'Input'):
            Hide(rep.Input, renderView)

def cleanup_view(renderView):
    """Clean up all displays and ensure nothing is visible"""
    hide_all_displays(renderView)
    Render(renderView)

def save_view(renderView, filename, camera_position, camera_focal_point, parallel_scale, resolution=[13200, 8976]):
    """Save screenshot with specified camera settings"""
    renderView.ResetCamera(False)
    renderView.CameraPosition = camera_position
    renderView.CameraFocalPoint = camera_focal_point
    renderView.CameraParallelScale = parallel_scale
    SaveScreenshot(f'./visualizations/{filename}', renderView, ImageResolution=resolution, TransparentBackground=1)

def find_wss_range(transforms_dict, times, target_region='wall'):
    """Find global wall shear stress range across all time steps for a specific region (e.g., wall/patch)."""
    global_min = float('inf')
    global_max = float('-inf')
    
    renderView = GetActiveViewOrCreate('RenderView')
    animationScene = GetAnimationScene()
    
    # Store displays to clean up
    temp_displays = []
    
    try:
        for time in times:
            animationScene.AnimationTime = time
            for transform in transforms_dict.values():
                display = setup_display(transform, renderView)
                temp_displays.append(display)
                
                # Focus on the target region (patch/wall)
                display.BlockSelectors = [f'/{target_region}']
                ColorBy(display, ('POINTS', 'wallShearStress', 'Magnitude'))
                display.RescaleTransferFunctionToDataRange(True, False)
                
                # Get WSS range for the selected region
                dataInfo = display.Input.GetPointDataInformation().GetArray('wallShearStress')
                rng = dataInfo.GetRange(-1)  # -1 for magnitude
                global_min = min(global_min, rng[0])
                global_max = max(global_max, rng[1])
                Hide(transform, renderView)
    finally:
        # Clean up all temporary displays
        for display in temp_displays:
            Delete(display)
            del display
        cleanup_view(renderView)
    
    return [global_min, global_max]

def find_velocity_range(transforms_dict, times):
    """Find global velocity range across all time steps"""
    global_min = float('inf')
    global_max = float('-inf')
    
    renderView = GetActiveViewOrCreate('RenderView')
    animationScene = GetAnimationScene()
    
    try:
        for time in times:
            animationScene.AnimationTime = time
            for transform in transforms_dict.values():
                streamTracer = StreamTracer(registrationName='TempTracer', Input=transform, SeedType='Point Cloud')
                streamTracer.Vectors = ['POINTS', 'U']
                streamTracer.SeedType.NumberOfPoints = 100
                
                display = Show(streamTracer, renderView, 'GeometryRepresentation')
                ColorBy(display, ('POINTS', 'U', 'Magnitude'))
                display.RescaleTransferFunctionToDataRange(True, False)
                
                dataInfo = streamTracer.GetPointDataInformation().GetArray('U')
                rng = dataInfo.GetRange(-1)  # -1 for magnitude
                
                global_min = min(global_min, rng[0])
                global_max = max(global_max, rng[1])
                
                # Clean up temporary objects
                Hide(streamTracer, renderView)
                Delete(display)
                Delete(streamTracer)
                del display
                del streamTracer
    finally:
        cleanup_view(renderView)
    
    return [global_min, global_max]

def setup_color_by_wss(display, renderView, wss_range):
    """Set up wall shear stress coloring"""
    ColorBy(display, ('POINTS', 'wallShearStress', 'Magnitude'))
    display.SetScalarBarVisibility(renderView, True)
    wssLUT = GetColorTransferFunction('wallShearStress')
    wssLUT.ApplyPreset('Rainbow Uniform', True)
    wssLUT.RescaleTransferFunction(wss_range[0], wss_range[1])
    
    # Setup color bar position
    wssLUTColorBar = GetScalarBar(wssLUT, renderView)
    wssLUTColorBar.WindowLocation = 'Any Location'
    wssLUTColorBar.Position = [0.1043181818181817, 0.2807486631016043]
    wssLUTColorBar.ScalarBarLength = 0.49934046345811023
    
    return wssLUT

def create_streamlines(input_data, renderView, velocity_range, num_points):
    """Create streamlines visualization"""
    streamTracer = StreamTracer(registrationName='StreamTracer1', Input=input_data, SeedType='Point Cloud')
    streamTracer.Vectors = ['POINTS', 'U']
    streamTracer.MaximumStreamlineLength = 0.13003995138569735
    streamTracer.SeedType.NumberOfPoints = num_points
    
    tube = Tube(registrationName='Tube1', Input=streamTracer)
    tube.Radius = 0.0003
    
    tubeDisplay = Show(tube, renderView, 'GeometryRepresentation')
    Hide(streamTracer, renderView)
    ColorBy(tubeDisplay, ('POINTS', 'U', 'Magnitude'))
    tubeDisplay.SetScalarBarVisibility(renderView, True)
    
    uLUT = GetColorTransferFunction('U')
    uLUT.ApplyPreset('Rainbow Uniform', True)
    uLUT.RescaleTransferFunction(velocity_range[0], velocity_range[1])
    
    # Set up consistent color bar position
    uLUTColorBar = GetScalarBar(uLUT, renderView)
    uLUTColorBar.WindowLocation = 'Any Location'
    uLUTColorBar.Position = [0.1043181818181817, 0.2807486631016043]
    uLUTColorBar.ScalarBarLength = 0.49934046345811023
    
    return tube, tubeDisplay

def create_tawss_visualization(transform, renderView, time_range):
    """Create time-averaged wall shear stress visualization"""
    # Show transform first
    display = Show(transform, renderView)
    display.BlockSelectors = ['/wall']
    
    # Extract time steps
    extractTimeSteps = ExtractTimeSteps(registrationName='ExtractTimeSteps', Input=transform)
    extractTimeSteps.SelectionMode = 'Select Time Range'
    extractTimeSteps.TimeStepRange = time_range
    
    # Calculate temporal statistics
    temporalStats = TemporalStatistics(registrationName='TemporalStatistics', Input=extractTimeSteps)
    temporalStats.ComputeMinimum = 0
    temporalStats.ComputeMaximum = 0
    temporalStats.ComputeStandardDeviation = 0
    
    # Hide transform display and show statistics
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
    """Find global TAWSS range across all views"""
    global_min = float('inf')
    global_max = float('-inf')
    
    renderView = GetActiveViewOrCreate('RenderView')
    
    # Store temporary objects to clean up
    temp_objects = []
    
    try:
        for transform in transforms_dict.values():
            temporalStats, statsDisplay, _ = create_tawss_visualization(transform, renderView, time_range)
            temp_objects.extend([temporalStats, statsDisplay])
            
            # Get TAWSS range
            dataInfo = statsDisplay.Input.GetPointDataInformation().GetArray('wallShearStress_average')
            rng = dataInfo.GetRange(-1)  # -1 for magnitude
            global_min = min(global_min, rng[0])
            global_max = max(global_max, rng[1])
            Hide(temporalStats, renderView)
    finally:
        # Clean up temporary objects
        for obj in temp_objects:
            Delete(obj)
            del obj
        cleanup_view(renderView)
    
    return [global_min, global_max]

# Main execution
renderView = setup_initial_view()
layout = GetLayout()
layout.SetSize(1650, 1122)

# Get initial foam source and setup

foamfoam = OpenDataFile('foam.foam')
if not foamfoam:
    raise RuntimeError("Could not load foam.foam file")

foamDisplay = setup_display(foamfoam, renderView)

# Create transforms
transforms = {
    'front': create_transform(foamfoam, [0.0, 0.0, 180.0], 'Transform1'),
    'side1': create_transform(foamfoam, [0.0, 90.0, 180.0], 'Transform2'),
    'side2': create_transform(foamfoam, [0.0, 270.0, 180.0], 'Transform3')
}

# Hide foam source and clean up view
Hide(foamfoam, renderView)
cleanup_view(renderView)

# Create basic geometry views
for view_name, transform in transforms.items():
    cleanup_view(renderView)
    
    display = setup_display(transform, renderView)
    ColorBy(display, None)
    reset_camera(renderView)
    save_view(renderView, f'{view_name}.png',
             [-0.01922904932871461, -0.0646100237063365, 0.3015332296964253],
             [-0.01922904932871461, -0.0646100237063365, -0.0015790509060025215],
             0.0723292692450845)
    Hide(transform, renderView)

# Find global ranges
times = [0.15, 1.1, 2.05, 3] # Time points of interest (peak systole)


# End Diastole (E): At t ≈ 0.875s, velocity ≈ -0.003 m/s (minimum after peak diastole)
# Early Systole (A): At t ≈ 0.0449, 0.951s, velocity ≈ 0.006 m/s (baseline before acceleration)
# Peak Systole (B): At t ≈ 0.138s, velocity ≈ 0.451 m/s (maximum positive velocity)
# End Systole (C): At t ≈ 0.337s, velocity ≈ 0.002 m/s (return to baseline)
# Peak Diastole (D): At t ≈ 0.399s, velocity ≈ -0.152 m/s (maximum negative velocity)

# considering peak systole as the most interesting phase
# t ≈ 0.1375 s with velocity ≈ 0.4503 m/s
# t ≈ 1.0888 s with velocity ≈ 0.4503 m/s
# t ≈ 2.0401 s with velocity ≈ 0.4503 m/s
# t ≈ 2.9914 s with velocity ≈ 0.4503 m/s

wss_range = find_wss_range(transforms, times, target_region='wall')
velocity_range = find_velocity_range(transforms, times)

# Create WSS visualizations
for time in times:
    animationScene = GetAnimationScene()
    animationScene.AnimationTime = time
    
    for view_name, transform in transforms.items():
        cleanup_view(renderView)
        
        display = setup_display(transform, renderView)
        wssLUT = setup_color_by_wss(display, renderView, wss_range)
        reset_camera(renderView)
        save_view(renderView, f'wss_{view_name}_t{time}.png',
                 [-0.01922904932871461, -0.0646100237063365, 0.3015332296964253],
                 [-0.01922904932871461, -0.0646100237063365, -0.0015790509060025215],
                 0.0723292692450845)
        Hide(transform, renderView)

# Create streamline visualizations
for time in times:
    animationScene = GetAnimationScene()
    animationScene.AnimationTime = time
    
    for view_name, transform in transforms.items():
        cleanup_view(renderView)
        
        # Setup transparent geometry
        display = setup_display(transform, renderView, opacity=0.05)
        
        # Create streamlines
        tube, tubeDisplay = create_streamlines(transform, renderView, velocity_range, num_points=40)
        reset_camera(renderView)
        save_view(renderView, f'stream_{view_name}_t{time}.png',
                 [-0.01922904932871461, -0.0646100237063365, 0.3015332296964253],
                 [-0.01922904932871461, -0.0646100237063365, -0.0015790509060025215],
                 0.0723292692450845)
        Hide(tube, renderView)
        Hide(transform, renderView)

    
# # Create TAWSS visualizations
# timestep_ranges = {
#     'cycle1': [0, 18],    
#     'cycle2': [18, 37],  
#     'cycle3': [37, 56],   
#     'cycle4': [56, 76]   
# }

# 	# Cycle 1:  t = 0.050 \, \text{to} \, 0.1325 , Steps 1–19
# 	# Cycle 2:  t = 0.1325 \, \text{to} \, 0.215 , Steps 20–38
# 	# Cycle 3:  t = 0.215 \, \text{to} \, 0.2975 , Steps 39–56
# 	# Cycle 4:  t = 0.2975 \, \text{to} \, 0.3800 , Steps 57–75

# # First find global TAWSS range across all timesteps
# global_tawss_range = find_tawss_range(transforms, [0, 5])  # Using full time range

# # Then create visualizations for each cycle
# for cycle_name, timestep_range in timestep_ranges.items():
#     for view_name, transform in transforms.items():
#         cleanup_view(renderView)
        
#         temporalStats, statsDisplay, tawssLUT = create_tawss_visualization(transform, renderView, timestep_range)
#         tawssLUT.RescaleTransferFunction(global_tawss_range[0], global_tawss_range[1])
        
#         reset_camera(renderView)
#         save_view(renderView, f'tawss_{view_name}_{cycle_name}.png',
#                  [-0.01922904932871461, -0.0646100237063365, 0.3015332296964253],
#                  [-0.01922904932871461, -0.0646100237063365, -0.0015790509060025215],
#                  0.0723292692450845)
        
#         Delete(statsDisplay)
#         Delete(temporalStats)
#         del statsDisplay
#         del temporalStats