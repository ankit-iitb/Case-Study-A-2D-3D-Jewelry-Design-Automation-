"""
Geometry Reconstruction Module

Converts 2D extracted curves and points into 3D mesh geometry.
Handles surface generation, extrusion, revolution, and lofting operations
to create production-ready 3D jewelry models.
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import math

try:
    import trimesh
    TRIMESH_AVAILABLE = True
except ImportError:
    TRIMESH_AVAILABLE = False
    print("Warning: trimesh not available. Using basic mesh operations.")


@dataclass
class Vertex:
    """3D vertex with position and optional normal."""
    x: float
    y: float
    z: float
    nx: float = 0.0
    ny: float = 0.0
    nz: float = 1.0


@dataclass
class Face:
    """Triangle face defined by vertex indices."""
    v1: int
    v2: int
    v3: int


class GeometryReconstructor:
    """
    Reconstructs 3D geometry from 2D extracted curves.
    
    Supports multiple reconstruction methods:
    - Extrusion: Extend 2D profile along depth axis
    - Revolution: Rotate 2D profile around an axis
    - Lofting: Blend between multiple 2D profiles
    - Surface fitting: Generate smooth surfaces from point clouds
    """
    
    DEFAULT_CONFIG = {
        'default_thickness': 1.5,  # mm - typical jewelry thickness
        'default_depth': 2.0,  # mm - default extrusion depth
        'revolution_segments': 64,  # Segments for revolution surfaces
        'smoothing_iterations': 3,  # Mesh smoothing passes
        'target_edge_length': 0.5,  # mm - target mesh edge length
        'reconstruction_method': 'extrude',  # 'extrude', 'revolution', 'loft'
    }
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialize geometry reconstructor with configuration."""
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}
        
    def reconstruct(self, geometry_data: Dict) -> Dict:
        """
        Reconstruct 3D mesh from 2D geometry data.
        
        Args:
            geometry_data: Extracted 2D geometry from input processor
            
        Returns:
            Dictionary containing:
            - vertices: List of 3D vertices
            - faces: List of triangle faces
            - normals: Vertex normals
            - dimensions: Bounding box dimensions
        """
        method = self.config['reconstruction_method']
        
        if method == 'extrude':
            return self._extrude_geometry(geometry_data)
        elif method == 'revolution':
            return self._revolution_geometry(geometry_data)
        elif method == 'loft':
            return self._loft_geometry(geometry_data)
        else:
            return self._extrude_geometry(geometry_data)
            
    def _extrude_geometry(self, geometry_data: Dict) -> Dict:
        """
        Extrude 2D curves to create 3D geometry.
        
        Args:
            geometry_data: 2D geometry data
            
        Returns:
            3D mesh data
        """
        all_vertices = []
        all_faces = []
        
        depth = self.config['default_depth']
        thickness = self.config['default_thickness']
        
        for curve in geometry_data.get('curves', []):
            points_2d = curve.get('points', [])
            if len(points_2d) < 3:
                continue
                
            # Convert 2D points to 3D by extruding
            mesh_data = self._extrude_closed_curve(points_2d, depth, thickness)
            
            # Offset vertex indices
            vertex_offset = len(all_vertices)
            all_vertices.extend(mesh_data['vertices'])
            all_faces.extend([
                [f[0] + vertex_offset, f[1] + vertex_offset, f[2] + vertex_offset]
                for f in mesh_data['faces']
            ])
            
        # If no curves, create a simple default shape
        if not all_vertices:
            mesh_data = self._create_default_ring()
            all_vertices = mesh_data['vertices']
            all_faces = mesh_data['faces']
            
        # Calculate dimensions
        vertices_array = np.array(all_vertices)
        dimensions = {
            'width': float(vertices_array[:, 0].max() - vertices_array[:, 0].min()),
            'height': float(vertices_array[:, 1].max() - vertices_array[:, 1].min()),
            'depth': float(vertices_array[:, 2].max() - vertices_array[:, 2].min()),
            'center': vertices_array.mean(axis=0).tolist()
        }
        
        # Calculate normals
        normals = self._calculate_normals(all_vertices, all_faces)
        
        return {
            'vertices': all_vertices,
            'faces': all_faces,
            'normals': normals,
            'dimensions': dimensions
        }
        
    def _extrude_closed_curve(self, points_2d: List[List[float]], 
                               depth: float, thickness: float) -> Dict:
        """
        Extrude a closed 2D curve into a 3D solid.
        
        Args:
            points_2d: List of 2D points defining the curve
            depth: Extrusion depth
            thickness: Shell thickness for hollow parts
            
        Returns:
            Mesh data with vertices and faces
        """
        vertices = []
        faces = []
        
        # Create top and bottom faces by offsetting Z
        num_points = len(points_2d)
        
        # Bottom face vertices (z = 0)
        for point in points_2d:
            vertices.append([point[0], point[1], 0.0])
            
        # Top face vertices (z = depth)
        for point in points_2d:
            vertices.append([point[0], point[1], depth])
            
        # Create side faces
        for i in range(num_points):
            next_i = (i + 1) % num_points
            
            # Bottom to top quad (two triangles)
            v1 = i
            v2 = next_i
            v3 = num_points + i
            v4 = num_points + next_i
            
            faces.append([v1, v2, v3])
            faces.append([v2, v4, v3])
            
        # Create top and bottom caps using fan triangulation
        if num_points >= 3:
            # Bottom cap
            for i in range(1, num_points - 1):
                faces.append([0, i, i + 1])
                
            # Top cap
            for i in range(1, num_points - 1):
                faces.append([num_points, num_points + i + 1, num_points + i])
                
        return {'vertices': vertices, 'faces': faces}
        
    def _revolution_geometry(self, geometry_data: Dict) -> Dict:
        """
        Create revolution surface by rotating 2D profile around an axis.
        
        Args:
            geometry_data: 2D geometry data
            
        Returns:
            3D mesh data
        """
        all_vertices = []
        all_faces = []
        
        segments = self.config['revolution_segments']
        
        for curve in geometry_data.get('curves', []):
            points_2d = curve.get('points', [])
            if len(points_2d) < 2:
                continue
                
            mesh_data = self._create_revolution_surface(points_2d, segments)
            
            vertex_offset = len(all_vertices)
            all_vertices.extend(mesh_data['vertices'])
            all_faces.extend([
                [f[0] + vertex_offset, f[1] + vertex_offset, f[2] + vertex_offset]
                for f in mesh_data['faces']
            ])
            
        if not all_vertices:
            mesh_data = self._create_default_ring()
            all_vertices = mesh_data['vertices']
            all_faces = mesh_data['faces']
            
        vertices_array = np.array(all_vertices)
        dimensions = {
            'width': float(vertices_array[:, 0].max() - vertices_array[:, 0].min()),
            'height': float(vertices_array[:, 1].max() - vertices_array[:, 1].min()),
            'depth': float(vertices_array[:, 2].max() - vertices_array[:, 2].min()),
            'center': vertices_array.mean(axis=0).tolist()
        }
        
        normals = self._calculate_normals(all_vertices, all_faces)
        
        return {
            'vertices': all_vertices,
            'faces': all_faces,
            'normals': normals,
            'dimensions': dimensions
        }
        
    def _create_revolution_surface(self, profile_points: List[List[float]], 
                                    segments: int) -> Dict:
        """
        Create surface of revolution from a 2D profile.
        
        Args:
            profile_points: 2D profile points (x, y) where x is radius, y is height
            segments: Number of angular segments
            
        Returns:
            Mesh data
        """
        vertices = []
        faces = []
        
        num_profile = len(profile_points)
        
        # Generate vertices by rotating profile around Y axis
        for i in range(segments):
            angle = 2 * math.pi * i / segments
            cos_a = math.cos(angle)
            sin_a = math.sin(angle)
            
            for point in profile_points:
                radius = point[0]
                height = point[1]
                x = radius * cos_a
                z = radius * sin_a
                vertices.append([x, height, z])
                
        # Generate faces
        for i in range(segments):
            next_i = (i + 1) % segments
            
            for j in range(num_profile - 1):
                v1 = i * num_profile + j
                v2 = i * num_profile + j + 1
                v3 = next_i * num_profile + j
                v4 = next_i * num_profile + j + 1
                
                faces.append([v1, v2, v3])
                faces.append([v2, v4, v3])
                
        return {'vertices': vertices, 'faces': faces}
        
    def _loft_geometry(self, geometry_data: Dict) -> Dict:
        """
        Create lofted surface between multiple 2D profiles.
        
        Args:
            geometry_data: 2D geometry data with multiple profiles
            
        Returns:
            3D mesh data
        """
        all_vertices = []
        all_faces = []
        
        curves = geometry_data.get('curves', [])
        
        if len(curves) < 2:
            # Fall back to extrusion if not enough profiles
            return self._extrude_geometry(geometry_data)
            
        # Create loft between consecutive profiles
        for i in range(len(curves) - 1):
            profile1 = curves[i].get('points', [])
            profile2 = curves[i + 1].get('points', [])
            
            if len(profile1) < 3 or len(profile2) < 3:
                continue
                
            # Assign Z values based on profile index
            z1 = i * self.config['default_depth']
            z2 = (i + 1) * self.config['default_depth']
            
            mesh_data = self._create_loft_surface(profile1, profile2, z1, z2)
            
            vertex_offset = len(all_vertices)
            all_vertices.extend(mesh_data['vertices'])
            all_faces.extend([
                [f[0] + vertex_offset, f[1] + vertex_offset, f[2] + vertex_offset]
                for f in mesh_data['faces']
            ])
            
        if not all_vertices:
            return self._create_default_ring()
            
        vertices_array = np.array(all_vertices)
        dimensions = {
            'width': float(vertices_array[:, 0].max() - vertices_array[:, 0].min()),
            'height': float(vertices_array[:, 1].max() - vertices_array[:, 1].min()),
            'depth': float(vertices_array[:, 2].max() - vertices_array[:, 2].min()),
            'center': vertices_array.mean(axis=0).tolist()
        }
        
        normals = self._calculate_normals(all_vertices, all_faces)
        
        return {
            'vertices': all_vertices,
            'faces': all_faces,
            'normals': normals,
            'dimensions': dimensions
        }
        
    def _create_loft_surface(self, profile1: List[List[float]], 
                              profile2: List[List[float]],
                              z1: float, z2: float) -> Dict:
        """
        Create lofted surface between two profiles.
        
        Args:
            profile1: First profile 2D points
            profile2: Second profile 2D points
            z1: Z coordinate for first profile
            z2: Z coordinate for second profile
            
        Returns:
            Mesh data
        """
        vertices = []
        faces = []
        
        # Resample profiles to same number of points
        n = max(len(profile1), len(profile2))
        profile1_resampled = self._resample_points(profile1, n)
        profile2_resampled = self._resample_points(profile2, n)
        
        # Create vertices
        for point in profile1_resampled:
            vertices.append([point[0], point[1], z1])
        for point in profile2_resampled:
            vertices.append([point[0], point[1], z2])
            
        # Create faces
        for i in range(n):
            next_i = (i + 1) % n
            v1 = i
            v2 = next_i
            v3 = n + i
            v4 = n + next_i
            
            faces.append([v1, v2, v3])
            faces.append([v2, v4, v3])
            
        return {'vertices': vertices, 'faces': faces}
        
    def _resample_points(self, points: List[List[float]], n: int) -> List[List[float]]:
        """
        Resample a list of points to have exactly n points.
        
        Args:
            points: Original points
            n: Target number of points
            
        Returns:
            Resampled points
        """
        if len(points) == n:
            return points
        elif len(points) < 1:
            return [[0.0, 0.0]] * n
            
        # Calculate cumulative arc lengths
        points_array = np.array(points)
        diffs = np.diff(points_array, axis=0)
        segment_lengths = np.linalg.norm(diffs, axis=1)
        arc_lengths = np.concatenate([[0], np.cumsum(segment_lengths)])
        total_length = arc_lengths[-1]
        
        if total_length == 0:
            return [points[0]] * n
            
        # Sample at equal arc length intervals
        target_lengths = np.linspace(0, total_length, n)
        resampled = []
        
        for target in target_lengths:
            # Find segment containing this arc length
            idx = np.searchsorted(arc_lengths, target) - 1
            idx = max(0, min(idx, len(points) - 2))
            
            # Interpolate within segment
            seg_start = arc_lengths[idx]
            seg_end = arc_lengths[idx + 1]
            if seg_end > seg_start:
                t = (target - seg_start) / (seg_end - seg_start)
            else:
                t = 0
                
            point = points_array[idx] + t * (points_array[idx + 1] - points_array[idx])
            resampled.append(point.tolist())
            
        return resampled
        
    def _create_default_ring(self) -> Dict:
        """
        Create a default ring shape when no geometry is provided.
        
        Returns:
            Mesh data for a simple ring
        """
        vertices = []
        faces = []
        
        inner_radius = 8.0  # mm
        outer_radius = 10.0  # mm
        height = 2.0  # mm
        segments = 64
        
        # Create inner and outer cylinder vertices
        for i in range(segments):
            angle = 2 * math.pi * i / segments
            cos_a = math.cos(angle)
            sin_a = math.sin(angle)
            
            # Inner bottom
            vertices.append([inner_radius * cos_a, inner_radius * sin_a, 0])
            # Inner top
            vertices.append([inner_radius * cos_a, inner_radius * sin_a, height])
            # Outer bottom
            vertices.append([outer_radius * cos_a, outer_radius * sin_a, 0])
            # Outer top
            vertices.append([outer_radius * cos_a, outer_radius * sin_a, height])
            
        # Create faces
        for i in range(segments):
            next_i = (i + 1) % segments
            
            # Indices for current and next segment
            curr = i * 4
            next_seg = next_i * 4
            
            # Inner wall
            faces.append([curr, next_seg, curr + 1])
            faces.append([next_seg, next_seg + 1, curr + 1])
            
            # Outer wall
            faces.append([curr + 2, curr + 3, next_seg + 2])
            faces.append([next_seg + 2, curr + 3, next_seg + 3])
            
            # Top surface
            faces.append([curr + 1, next_seg + 1, curr + 3])
            faces.append([next_seg + 1, next_seg + 3, curr + 3])
            
            # Bottom surface
            faces.append([curr, curr + 2, next_seg])
            faces.append([next_seg, curr + 2, next_seg + 2])
            
        return {'vertices': vertices, 'faces': faces}
        
    def _calculate_normals(self, vertices: List[List[float]], 
                           faces: List[List[int]]) -> List[List[float]]:
        """
        Calculate vertex normals from face data.
        
        Args:
            vertices: List of vertex positions
            faces: List of face indices
            
        Returns:
            List of vertex normals
        """
        vertices_array = np.array(vertices)
        normals = np.zeros_like(vertices_array)
        
        for face in faces:
            v1 = vertices_array[face[0]]
            v2 = vertices_array[face[1]]
            v3 = vertices_array[face[2]]
            
            # Calculate face normal
            edge1 = v2 - v1
            edge2 = v3 - v1
            face_normal = np.cross(edge1, edge2)
            
            # Add to vertex normals (will be normalized later)
            normals[face[0]] += face_normal
            normals[face[1]] += face_normal
            normals[face[2]] += face_normal
            
        # Normalize
        norms = np.linalg.norm(normals, axis=1)
        norms[norms == 0] = 1  # Avoid division by zero
        normals = normals / norms[:, np.newaxis]
        
        return normals.tolist()
        
    def smooth_mesh(self, vertices: List[List[float]], 
                    faces: List[List[int]], 
                    iterations: int = None) -> Tuple[List, List]:
        """
        Apply Laplacian smoothing to mesh.
        
        Args:
            vertices: Vertex positions
            faces: Face indices
            iterations: Number of smoothing iterations
            
        Returns:
            Smoothed vertices and faces
        """
        if iterations is None:
            iterations = self.config['smoothing_iterations']
            
        vertices_array = np.array(vertices)
        
        # Build adjacency map
        adjacency = self._build_adjacency(vertices, faces)
        
        for _ in range(iterations):
            new_vertices = vertices_array.copy()
            
            for i in range(len(vertices)):
                if i in adjacency and len(adjacency[i]) > 0:
                    # Average with neighbors
                    neighbors = adjacency[i]
                    neighbor_positions = vertices_array[neighbors]
                    new_vertices[i] = neighbor_positions.mean(axis=0)
                    
            vertices_array = new_vertices
            
        return vertices_array.tolist(), faces
        
    def _build_adjacency(self, vertices: List[List[float]], 
                         faces: List[List[int]]) -> Dict[int, List[int]]:
        """
        Build vertex adjacency map from faces.
        
        Args:
            vertices: Vertex positions
            faces: Face indices
            
        Returns:
            Dictionary mapping vertex index to neighbor indices
        """
        adjacency = {i: set() for i in range(len(vertices))}
        
        for face in faces:
            adjacency[face[0]].update([face[1], face[2]])
            adjacency[face[1]].update([face[0], face[2]])
            adjacency[face[2]].update([face[0], face[1]])
            
        return {k: list(v) for k, v in adjacency.items()}