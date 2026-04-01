"""
Input Processing Module

Handles parsing of 2D jewelry design files (SVG, vector formats)
and extraction of geometric features including curves, symmetry axes,
stone positions, and dimension annotations.
"""

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import numpy as np

try:
    from svgpathtools import svg2paths2, Line, CubicBezier, QuadraticBezier, Arc
    SVG_TOOLS_AVAILABLE = True
except ImportError:
    SVG_TOOLS_AVAILABLE = False
    print("Warning: svgpathtools not available. Using fallback SVG parser.")


class InputProcessor:
    """
    Processes 2D jewelry design files and extracts structured geometry data.
    
    Supports:
    - SVG files with paths, shapes, and annotations
    - Dimension markers and stone position indicators
    - Symmetry detection
    - Curve extraction and discretization
    """
    
    # Default configuration
    DEFAULT_CONFIG = {
        'curve_resolution': 50,  # Points per curve segment
        'dimension_regex': r'(\d+\.?\d*)\s*mm',  # Pattern for dimension extraction
        'stone_markers': ['circle', 'diamond'],  # Shape types indicating stones
        'symmetry_detection': True,
        'min_curve_length': 0.1,  # Minimum curve length in mm
    }
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialize input processor with configuration."""
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}
        
    def process(self, input_file: str) -> Dict:
        """
        Process input file and extract geometry data.
        
        Args:
            input_file: Path to input SVG or vector file
            
        Returns:
            Dictionary containing extracted geometry:
            - curves: List of curve definitions
            - points: Key points (vertices, centers)
            - dimensions: Extracted dimension values
            - symmetry: Detected symmetry axes
            - stones: Stone position markers
            - metadata: File metadata
        """
        input_path = Path(input_file)
        
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_file}")
            
        if input_path.suffix.lower() == '.svg':
            return self._process_svg(input_path)
        else:
            raise ValueError(f"Unsupported file format: {input_path.suffix}")
            
    def _process_svg(self, svg_path: Path) -> Dict:
        """
        Process SVG file and extract geometric elements.
        
        Args:
            svg_path: Path to SVG file
            
        Returns:
            Extracted geometry data dictionary
        """
        geometry_data = {
            'curves': [],
            'points': [],
            'dimensions': {},
            'symmetry': None,
            'stones': [],
            'metadata': {},
            'bounds': None
        }
        
        if SVG_TOOLS_AVAILABLE:
            return self._process_svg_advanced(svg_path, geometry_data)
        else:
            return self._process_svg_basic(svg_path, geometry_data)
            
    def _process_svg_advanced(self, svg_path: Path, geometry_data: Dict) -> Dict:
        """
        Advanced SVG processing using svgpathtools.
        
        Args:
            svg_path: Path to SVG file
            geometry_data: Initial geometry data structure
            
        Returns:
            Updated geometry data with extracted curves
        """
        try:
            paths, attributes, svg_attributes = svg2paths2(str(svg_path))
            
            # Extract viewBox and dimensions
            if 'viewBox' in svg_attributes:
                vb = svg_attributes['viewBox'].split()
                geometry_data['metadata']['viewBox'] = {
                    'x': float(vb[0]),
                    'y': float(vb[1]),
                    'width': float(vb[2]),
                    'height': float(vb[3])
                }
            
            # Process each path
            all_points = []
            for i, path in enumerate(paths):
                curve_data = self._extract_curve_data(path, i)
                if curve_data:
                    geometry_data['curves'].append(curve_data)
                    all_points.extend(curve_data['points'])
                    
            # Calculate bounds
            if all_points:
                points_array = np.array(all_points)
                geometry_data['bounds'] = {
                    'min': points_array.min(axis=0).tolist(),
                    'max': points_array.max(axis=0).tolist(),
                    'center': points_array.mean(axis=0).tolist()
                }
                
            # Extract dimensions from text elements
            geometry_data['dimensions'] = self._extract_dimensions(svg_path)
            
            # Detect stones (circles/shapes that might represent gemstones)
            geometry_data['stones'] = self._detect_stones(svg_path)
            
            # Detect symmetry
            if self.config['symmetry_detection']:
                geometry_data['symmetry'] = self._detect_symmetry(geometry_data)
                
        except Exception as e:
            print(f"Warning: Advanced SVG processing failed: {e}")
            return self._process_svg_basic(svg_path, geometry_data)
            
        return geometry_data
        
    def _process_svg_basic(self, svg_path: Path, geometry_data: Dict) -> Dict:
        """
        Basic SVG processing using ElementTree.
        Fallback when svgpathtools is not available.
        
        Args:
            svg_path: Path to SVG file
            geometry_data: Initial geometry data structure
            
        Returns:
            Updated geometry data with extracted elements
        """
        try:
            tree = ET.parse(svg_path)
            root = tree.getroot()
            
            # Extract viewBox
            viewBox = root.get('viewBox', '0 0 100 100')
            if viewBox:
                vb = viewBox.split()
                geometry_data['metadata']['viewBox'] = {
                    'x': float(vb[0]),
                    'y': float(vb[1]),
                    'width': float(vb[2]),
                    'height': float(vb[3])
                }
            
            # Find all path elements
            curve_id = 0
            for elem in root.iter():
                if elem.tag.endswith('path'):
                    d = elem.get('d', '')
                    if d:
                        curve_data = self._parse_path_data(d, curve_id)
                        if curve_data:
                            geometry_data['curves'].append(curve_data)
                            curve_id += 1
                            
                elif elem.tag.endswith('circle'):
                    # Extract circle as potential stone marker
                    cx = float(elem.get('cx', 0))
                    cy = float(elem.get('cy', 0))
                    r = float(elem.get('r', 0))
                    geometry_data['stones'].append({
                        'type': 'circle',
                        'center': [cx, cy],
                        'radius': r
                    })
                    
            # Extract dimensions from text elements
            geometry_data['dimensions'] = self._extract_dimensions_from_tree(tree)
            
            # Detect symmetry
            if self.config['symmetry_detection'] and geometry_data['curves']:
                geometry_data['symmetry'] = self._detect_symmetry(geometry_data)
                
        except Exception as e:
            print(f"Warning: Basic SVG processing failed: {e}")
            
        return geometry_data
        
    def _extract_curve_data(self, path, path_id: int) -> Optional[Dict]:
        """
        Extract curve data from a path object.
        
        Args:
            path: Path object from svgpathtools
            path_id: Unique identifier for this path
            
        Returns:
            Dictionary containing curve data or None if invalid
        """
        if path.length() < self.config['min_curve_length']:
            return None
            
        curve_data = {
            'id': path_id,
            'type': 'composite',
            'segments': [],
            'points': [],
            'length': path.length()
        }
        
        resolution = self.config['curve_resolution']
        
        for segment in path:
            segment_data = {
                'type': type(segment).__name__,
                'start': [segment.start.real, segment.start.imag],
                'end': [segment.end.real, segment.end.imag]
            }
            
            # Extract control points for bezier curves
            if isinstance(segment, CubicBezier):
                segment_data['control1'] = [segment.control1.real, segment.control1.imag]
                segment_data['control2'] = [segment.control2.real, segment.control2.imag]
            elif isinstance(segment, QuadraticBezier):
                segment_data['control'] = [segment.control.real, segment.control.imag]
                
            # Discretize curve into points
            num_points = max(2, int(segment.length() / path.length() * resolution))
            for i in range(num_points):
                t = i / (num_points - 1)
                point = segment.point(t)
                curve_data['points'].append([point.real, point.imag])
                
            curve_data['segments'].append(segment_data)
            
        return curve_data if curve_data['points'] else None
        
    def _parse_path_data(self, d: str, path_id: int) -> Optional[Dict]:
        """
        Parse SVG path data string into curve points.
        
        Args:
            d: SVG path data string (e.g., "M 0 0 L 10 10")
            path_id: Unique identifier for this path
            
        Returns:
            Dictionary containing curve data or None if invalid
        """
        # Simple path parser for M, L, C, Q, Z commands
        commands = re.findall(r'([MLCQAZ])\s*([\d\s,.-]*)', d.upper())
        
        if not commands:
            return None
            
        curve_data = {
            'id': path_id,
            'type': 'composite',
            'segments': [],
            'points': []
        }
        
        current_pos = [0.0, 0.0]
        start_pos = [0.0, 0.0]
        
        for cmd, args_str in commands:
            args = [float(x) for x in re.findall(r'-?\d+\.?\d*', args_str)]
            
            if cmd == 'M' and len(args) >= 2:
                current_pos = [args[0], args[1]]
                start_pos = current_pos.copy()
                curve_data['points'].append(current_pos.copy())
                
            elif cmd == 'L' and len(args) >= 2:
                segment_data = {
                    'type': 'Line',
                    'start': current_pos.copy(),
                    'end': [args[0], args[1]]
                }
                curve_data['segments'].append(segment_data)
                current_pos = [args[0], args[1]]
                curve_data['points'].append(current_pos.copy())
                
            elif cmd == 'C' and len(args) >= 6:
                segment_data = {
                    'type': 'CubicBezier',
                    'start': current_pos.copy(),
                    'control1': [args[0], args[1]],
                    'control2': [args[2], args[3]],
                    'end': [args[4], args[5]]
                }
                curve_data['segments'].append(segment_data)
                
                # Discretize cubic bezier
                points = self._discretize_cubic_bezier(
                    current_pos, [args[0], args[1]], 
                    [args[2], args[3]], [args[4], args[5]]
                )
                curve_data['points'].extend(points)
                current_pos = [args[4], args[5]]
                
            elif cmd == 'Z':
                if start_pos != current_pos:
                    curve_data['points'].append(start_pos.copy())
                    current_pos = start_pos.copy()
                    
        return curve_data if curve_data['points'] else None
        
    def _discretize_cubic_bezier(self, p0, p1, p2, p3, num_points=20) -> List[List[float]]:
        """
        Discretize cubic bezier curve into points.
        
        Args:
            p0, p1, p2, p3: Control points
            num_points: Number of points to generate
            
        Returns:
            List of points along the curve
        """
        points = []
        for i in range(1, num_points + 1):
            t = i / num_points
            # Cubic bezier formula: B(t) = (1-t)^3*P0 + 3*(1-t)^2*t*P1 + 3*(1-t)*t^2*P2 + t^3*P3
            x = (1-t)**3 * p0[0] + 3*(1-t)**2*t * p1[0] + 3*(1-t)*t**2 * p2[0] + t**3 * p3[0]
            y = (1-t)**3 * p0[1] + 3*(1-t)**2*t * p1[1] + 3*(1-t)*t**2 * p2[1] + t**3 * p3[1]
            points.append([x, y])
        return points
        
    def _extract_dimensions(self, svg_path: Path) -> Dict:
        """
        Extract dimension annotations from SVG text elements.
        
        Args:
            svg_path: Path to SVG file
            
        Returns:
            Dictionary of extracted dimensions
        """
        dimensions = {}
        
        try:
            tree = ET.parse(svg_path)
            root = tree.getroot()
            
            pattern = re.compile(self.config['dimension_regex'])
            dim_index = 0
            
            for elem in root.iter():
                if elem.tag.endswith('text') or elem.tag.endswith('tspan'):
                    text = elem.text or ''
                    matches = pattern.findall(text)
                    for match in matches:
                        dim_name = f"dimension_{dim_index}"
                        dimensions[dim_name] = {
                            'value': float(match),
                            'unit': 'mm',
                            'text': text.strip()
                        }
                        dim_index += 1
                        
        except Exception as e:
            print(f"Warning: Dimension extraction failed: {e}")
            
        return dimensions
        
    def _extract_dimensions_from_tree(self, tree) -> Dict:
        """
        Extract dimensions from an ElementTree.
        
        Args:
            tree: ElementTree object
            
        Returns:
            Dictionary of extracted dimensions
        """
        dimensions = {}
        root = tree.getroot()
        
        pattern = re.compile(self.config['dimension_regex'])
        dim_index = 0
        
        for elem in root.iter():
            if elem.tag.endswith('text') or elem.tag.endswith('tspan'):
                text = elem.text or ''
                matches = pattern.findall(text)
                for match in matches:
                    dim_name = f"dimension_{dim_index}"
                    dimensions[dim_name] = {
                        'value': float(match),
                        'unit': 'mm',
                        'text': text.strip()
                    }
                    dim_index += 1
                    
        return dimensions
        
    def _detect_stones(self, svg_path: Path) -> List[Dict]:
        """
        Detect stone markers in the SVG (circles, diamonds, etc.).
        
        Args:
            svg_path: Path to SVG file
            
        Returns:
            List of detected stone positions
        """
        stones = []
        
        try:
            tree = ET.parse(svg_path)
            root = tree.getroot()
            
            stone_id = 0
            for elem in root.iter():
                # Detect circles (common for round stones)
                if elem.tag.endswith('circle'):
                    cx = float(elem.get('cx', 0))
                    cy = float(elem.get('cy', 0))
                    r = float(elem.get('r', 0))
                    
                    # Filter by reasonable stone sizes (0.5mm to 20mm radius)
                    if 0.5 <= r <= 20:
                        stones.append({
                            'id': stone_id,
                            'type': 'round',
                            'center': [cx, cy],
                            'radius': r,
                            'size_mm': r * 2
                        })
                        stone_id += 1
                        
                # Detect polygons (potential fancy cut stones)
                elif elem.tag.endswith('polygon') or elem.tag.endswith('rect'):
                    points_str = elem.get('points', '')
                    if points_str:
                        points = re.findall(r'(\d+\.?\d*)[,\s]+(\d+\.?\d*)', points_str)
                        if points:
                            points_array = np.array([[float(x), float(y)] for x, y in points])
                            center = points_array.mean(axis=0).tolist()
                            stones.append({
                                'id': stone_id,
                                'type': 'fancy',
                                'center': center,
                                'vertices': points_array.tolist()
                            })
                            stone_id += 1
                            
        except Exception as e:
            print(f"Warning: Stone detection failed: {e}")
            
        return stones
        
    def _detect_symmetry(self, geometry_data: Dict) -> Optional[Dict]:
        """
        Detect symmetry axes in the geometry.
        
        Args:
            geometry_data: Extracted geometry data
            
        Returns:
            Dictionary describing detected symmetry or None
        """
        if not geometry_data.get('bounds'):
            return None
            
        bounds = geometry_data['bounds']
        center = bounds['center']
        
        symmetry_info = {
            'center': center,
            'axes': []
        }
        
        # Check for vertical symmetry (common in jewelry)
        all_points = []
        for curve in geometry_data.get('curves', []):
            all_points.extend(curve.get('points', []))
            
        if not all_points:
            return None
            
        points_array = np.array(all_points)
        
        # Test vertical symmetry (reflection across vertical axis through center)
        reflected_x = 2 * center[0] - points_array[:, 0]
        reflected_points = np.column_stack([reflected_x, points_array[:, 1]])
        
        # Check if reflected points are close to any original points
        vertical_symmetric = self._check_point_symmetry(points_array, reflected_points)
        if vertical_symmetric:
            symmetry_info['axes'].append({
                'type': 'vertical',
                'position': center[0]
            })
            
        # Test horizontal symmetry
        reflected_y = 2 * center[1] - points_array[:, 1]
        reflected_points = np.column_stack([points_array[:, 0], reflected_y])
        
        horizontal_symmetric = self._check_point_symmetry(points_array, reflected_points)
        if horizontal_symmetric:
            symmetry_info['axes'].append({
                'type': 'horizontal',
                'position': center[1]
            })
            
        return symmetry_info if symmetry_info['axes'] else None
        
    def _check_point_symmetry(self, original: np.ndarray, reflected: np.ndarray, 
                              tolerance: float = 1.0) -> bool:
        """
        Check if reflected points match original points within tolerance.
        
        Args:
            original: Original point array
            reflected: Reflected point array
            tolerance: Maximum distance for matching
            
        Returns:
            True if points are approximately symmetric
        """
        for point in reflected:
            distances = np.linalg.norm(original - point, axis=1)
            if distances.min() > tolerance:
                return False
        return True