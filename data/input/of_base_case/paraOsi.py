from paraview.simple import *
paraview.simple._DisableFirstRenderCameraReset()

LoadPalette(paletteName='WhiteBackground')

def setup_initial_view():
    renderView = GetActiveViewOrCreate('RenderView')
    renderView.CameraParallelProjection = 1
    renderView.OrientationAxesVisibility = 0
    return renderView

def reset_camera(renderView):
    renderView.ResetCamera(False)

def create_transform(input_data, rotation, name):
    transform = Transform(registrationName=name, Input=input_data)
    transform.Transform = 'Transform'
    transform.Transform.Rotate = rotation
    HideInteractiveWidgets(proxy=transform.Transform)
    return transform

def setup_display(data, renderView, opacity=1.0):
    display = Show(data, renderView, 'UnstructuredGridRepresentation')
    display.Representation = 'Surface'
    display.Opacity = opacity
    return display

def cleanup_view(renderView):
    for rep in renderView.Representations:
        if hasattr(rep, 'Input'):
            Hide(rep.Input, renderView)
    Render(renderView)

def save_view(renderView, filename, camera_position, camera_focal_point, parallel_scale, resolution=[13200, 8976]):
    renderView.ResetCamera(False)
    renderView.CameraPosition = camera_position 
    renderView.CameraFocalPoint = camera_focal_point
    renderView.CameraParallelScale = parallel_scale
    SaveScreenshot(f'./visualizations/{filename}', renderView, ImageResolution=resolution, TransparentBackground=1)

def create_osi_visualization(transform, renderView, time_range):
    display = Show(transform, renderView)
    display.BlockSelectors = ['/wall']
    
    extractTimeSteps = ExtractTimeSteps(registrationName=f'ExtractTimeSteps_{time_range[0]}_{time_range[1]}', Input=transform)
    extractTimeSteps.SelectionMode = 'Select Time Range'
    extractTimeSteps.TimeStepRange = time_range
    
    instantWSS = Calculator(registrationName=f'InstantWSS_{time_range[0]}_{time_range[1]}', Input=extractTimeSteps)
    instantWSS.ResultArrayName = 'instantWSS'
    instantWSS.Function = 'mag(wallShearStress)'
    
    temporalStats = TemporalStatistics(registrationName=f'TemporalStatistics_{time_range[0]}_{time_range[1]}', Input=instantWSS)
    temporalStats.ComputeMinimum = 0
    temporalStats.ComputeMaximum = 0
    temporalStats.ComputeStandardDeviation = 0
    
    osiCalc = Calculator(registrationName=f'OSICalculator_{time_range[0]}_{time_range[1]}', Input=temporalStats)
    osiCalc.ResultArrayName = 'OSI'
    osiCalc.Function = '0.5*(1 - mag(wallShearStress_average)/instantWSS_average)'
    
    Hide(transform, renderView)
    Hide(extractTimeSteps, renderView)
    Hide(instantWSS, renderView)
    Hide(temporalStats, renderView)
    
    osiDisplay = Show(osiCalc, renderView, 'GeometryRepresentation')
    osiDisplay.Representation = 'Surface'
    
    ColorBy(osiDisplay, ('POINTS', 'OSI'))
    osiDisplay.SetScalarBarVisibility(renderView, True)
    
    osiLUT = GetColorTransferFunction('OSI')
    osiLUT.ApplyPreset('Rainbow Uniform', True)
    osiLUT.RescaleTransferFunction(0.0, 0.5)
    
    osiLUTColorBar = GetScalarBar(osiLUT, renderView)
    osiLUTColorBar.WindowLocation = 'Any Location'
    osiLUTColorBar.Position = [0.1043181818181817, 0.2807486631016043]
    osiLUTColorBar.ScalarBarLength = 0.49934046345811023
    
    return osiCalc, osiDisplay, osiLUT

# Main execution
renderView = setup_initial_view()
layout = GetLayout()
layout.SetSize(1650, 1122)

foamfoam = OpenDataFile('foam.foam')
if not foamfoam:
    raise RuntimeError("Could not load foam.foam file")

transforms = {
    'front': create_transform(foamfoam, [0.0, 0.0, 180.0], 'Transform1'),
    'side1': create_transform(foamfoam, [0.0, 90.0, 180.0], 'Transform2'),
    'side2': create_transform(foamfoam, [0.0, 270.0, 180.0], 'Transform3')
}

timestep_ranges = {
    'cycle1': [0, 18],    
    'cycle2': [18, 37],  
    'cycle3': [37, 56],   
    'cycle4': [56, 76]   
}

for cycle_name, timestep_range in timestep_ranges.items():
    for view_name, transform in transforms.items():
        cleanup_view(renderView)
        osiCalc, osiDisplay, osiLUT = create_osi_visualization(transform, renderView, timestep_range)
        reset_camera(renderView)
        save_view(renderView, f'osi_{view_name}_{cycle_name}.png',
                 [-0.01922904932871461, -0.0646100237063365, 0.3015332296964253],
                 [-0.01922904932871461, -0.0646100237063365, -0.0015790509060025215],
                 0.0723292692450845)
        Delete(osiCalc)
        Delete(osiDisplay)
        del osiCalc
        del osiDisplay
        del osiLUT