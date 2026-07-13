import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Button, TextBox
from dataclasses import dataclass
from typing import List, Optional, Tuple
import json

@dataclass
class DesignPoint:
    """Class to store design points with position and metadata"""
    x: float
    y: float
    diameter: Optional[float] = None
    name: str = ""
    
    def to_dict(self) -> dict:
        """Convert point to dictionary for export"""
        return {
            'x': self.x,
            'y': self.y,
            'diameter': self.diameter,
            'name': self.name
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'DesignPoint':
        """Create point from dictionary"""
        return cls(**data)

class VesselDesigner:
    def __init__(self):
        self.points: List[DesignPoint] = []
        self.setup_plot()
        self.selected_point = None
        self.spline_points = None
        self.spline_diameters = None
        
    def setup_plot(self):
        """Setup the matplotlib figure and interface"""
        self.fig = plt.figure(figsize=(15, 8))
        
        # Main geometry plot
        self.ax_geom = self.fig.add_subplot(121)
        self.ax_geom.set_xlabel('X [mm]')
        self.ax_geom.set_ylabel('Y [mm]')
        self.ax_geom.set_title('Vessel Geometry Designer')
        self.ax_geom.grid(True)
        
        # Diameter plot
        self.ax_diam = self.fig.add_subplot(122)
        self.ax_diam.set_xlabel('Y position [mm]')
        self.ax_diam.set_ylabel('Diameter [mm]')
        self.ax_diam.set_title('Diameter Profile')
        self.ax_diam.grid(True)
        
        # Add buttons and text boxes
        ax_add = plt.axes([0.02, 0.92, 0.1, 0.04])
        self.btn_add = Button(ax_add, 'Add Point')
        self.btn_add.on_clicked(self.add_point_click)
        
        ax_remove = plt.axes([0.13, 0.92, 0.1, 0.04])
        self.btn_remove = Button(ax_remove, 'Remove Point')
        self.btn_remove.on_clicked(self.remove_point_click)
        
        ax_export = plt.axes([0.24, 0.92, 0.1, 0.04])
        self.btn_export = Button(ax_export, 'Export')
        self.btn_export.on_clicked(self.export_points)
        
        ax_import = plt.axes([0.35, 0.92, 0.1, 0.04])
        self.btn_import = Button(ax_import, 'Import')
        self.btn_import.on_clicked(self.import_points)
        
        # Text boxes for point properties
        self.txt_boxes = {
            'name': TextBox(plt.axes([0.02, 0.85, 0.2, 0.04]), 'Name: ', initial=''),
            'diameter': TextBox(plt.axes([0.02, 0.80, 0.2, 0.04]), 'Diameter: ', initial='')
        }
        
        for txt in self.txt_boxes.values():
            txt.on_submit(self.update_point_properties)
        
        # Connect events
        self.fig.canvas.mpl_connect('button_press_event', self.on_click)
        self.fig.canvas.mpl_connect('motion_notify_event', self.on_motion)
        
        plt.tight_layout()
    
    def add_point_click(self, event):
        """Enter point adding mode"""
        self.adding_point = True
    
    def remove_point_click(self, event):
        """Remove selected point"""
        if self.selected_point is not None:
            self.points.pop(self.selected_point)
            self.selected_point = None
            self.update_plot()
    
    def on_click(self, event):
        """Handle mouse clicks"""
        if event.inaxes != self.ax_geom:
            return
            
        if hasattr(self, 'adding_point') and self.adding_point:
            # Add new point
            point = DesignPoint(event.xdata, event.ydata, diameter=20.0, 
                              name=f'Point {len(self.points)}')
            self.points.append(point)
            self.adding_point = False
            self.update_plot()
        else:
            # Select existing point
            self.selected_point = self.find_nearest_point(event.xdata, event.ydata)
            if self.selected_point is not None:
                point = self.points[self.selected_point]
                self.txt_boxes['name'].set_val(point.name)
                self.txt_boxes['diameter'].set_val(str(point.diameter))
            self.update_plot()
    
    def on_motion(self, event):
        """Handle mouse motion for dragging points"""
        if event.inaxes != self.ax_geom or self.selected_point is None or not event.button:
            return
        
        self.points[self.selected_point].x = event.xdata
        self.points[self.selected_point].y = event.ydata
        self.update_plot()
    
    def find_nearest_point(self, x, y, threshold=10) -> Optional[int]:
        """Find nearest point within threshold"""
        if not self.points:
            return None
            
        distances = [(i, np.sqrt((p.x - x)**2 + (p.y - y)**2)) 
                    for i, p in enumerate(self.points)]
        nearest = min(distances, key=lambda x: x[1])
        
        return nearest[0] if nearest[1] < threshold/self.ax_geom.get_window_extent().width else None
    
    def update_point_properties(self, _):
        """Update properties of selected point"""
        if self.selected_point is None:
            return
            
        point = self.points[self.selected_point]
        point.name = self.txt_boxes['name'].text
        try:
            point.diameter = float(self.txt_boxes['diameter'].text)
        except ValueError:
            pass
        
        self.update_plot()
    
    def generate_spline(self) -> Tuple[np.ndarray, np.ndarray]:
        """Generate spline through points"""
        if len(self.points) < 2:
            return None, None
            
        # Sort points by Y coordinate
        sorted_points = sorted(self.points, key=lambda p: p.y)
        
        # Extract coordinates and diameters
        y_coords = np.array([p.y for p in sorted_points])
        x_coords = np.array([p.x for p in sorted_points])
        diameters = np.array([p.diameter for p in sorted_points])
        
        # Generate spline points
        t = np.linspace(y_coords[0], y_coords[-1], 100)
        x_spline = np.interp(t, y_coords, x_coords)
        d_spline = np.interp(t, y_coords, diameters)
        
        return np.column_stack((x_spline, t)), d_spline
    
    def update_plot(self):
        """Update the plot with current points and spline"""
        self.ax_geom.clear()
        self.ax_diam.clear()
        
        # Plot points
        for i, point in enumerate(self.points):
            color = 'red' if i == self.selected_point else 'blue'
            self.ax_geom.plot(point.x, point.y, 'o', color=color, markersize=8)
            self.ax_geom.annotate(f'{point.name}\n(d={point.diameter}mm)', 
                                (point.x, point.y), xytext=(10, 10),
                                textcoords='offset points')
        
        # Generate and plot spline
        if len(self.points) >= 2:
            spline_points, spline_diameters = self.generate_spline()
            if spline_points is not None:
                self.spline_points = spline_points
                self.spline_diameters = spline_diameters
                
                # Plot centerline
                self.ax_geom.plot(spline_points[:,0], spline_points[:,1], 'g-', label='Centerline')
                
                # Plot diameter profile
                self.ax_diam.plot(spline_points[:,1], spline_diameters, 'b-')
                self.ax_diam.scatter([p.y for p in self.points], 
                                   [p.diameter for p in self.points], 
                                   color='red')
        
        # Configure axes
        self.ax_geom.grid(True)
        self.ax_geom.set_xlabel('X [mm]')
        self.ax_geom.set_ylabel('Y [mm]')
        self.ax_geom.set_title('Vessel Geometry Designer')
        
        self.ax_diam.grid(True)
        self.ax_diam.set_xlabel('Y position [mm]')
        self.ax_diam.set_ylabel('Diameter [mm]')
        self.ax_diam.set_title('Diameter Profile')
        
        # Set aspect ratio for geometry plot
        self.ax_geom.set_aspect('equal')
        
        plt.draw()
    
    def export_points(self, _):
        """Export points to a configuration-ready format"""
        if not self.points:
            print("No points to export")
            return
            
        # Sort points by Y coordinate
        sorted_points = sorted(self.points, key=lambda p: p.y)
        
        # Generate Python code
        code = "self.anatomical_points = [\n"
        for point in sorted_points:
            code += f"    AnatomicalPoint({point.x:.1f}, {point.y:.1f}, "
            code += f"\"{point.name}\", {point.diameter:.1f}),\n"
        code += "]\n"
        
        # Save to file and print
        with open('vessel_points.txt', 'w') as f:
            f.write(code)
        
        print("\nConfiguration code has been written to 'vessel_points.txt'")
        print("\nCopy and paste this into your configuration file:")
        print(code)
        
        # Also save full data as JSON for later import
        data = {
            'points': [p.to_dict() for p in self.points]
        }
        with open('vessel_design.json', 'w') as f:
            json.dump(data, f, indent=4)
    
    def import_points(self, _):
        """Import points from JSON file"""
        try:
            with open('vessel_design.json', 'r') as f:
                data = json.load(f)
                self.points = [DesignPoint.from_dict(p) for p in data['points']]
                self.update_plot()
        except FileNotFoundError:
            print("No saved design found")

# Run the designer
if __name__ == "__main__":
    designer = VesselDesigner()
    plt.show()