"""
Feature Modeling Module

Adds jewelry-specific features to 3D geometry including:
- Stone placement and settings
- Prongs and mounts
- Pave settings
- Joints and connectors
- Decorative elements
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
import math


class FeatureModeler:
    """
    Models jewelry features on 3D geometry.
    
    Supports:
    - Round brilliant cut stones
    - Princess cut stones
    - Prong settings (4-prong, 6-prong)
    - Bezel settings
    - Pave settings
    - Channel settings
    """
    
    DEFAULT_CONFIG = {
        'default_prong_count': 4,
        'prong_radius': 0.3,  # mm
        'prong_height': 1.5,  # mm - height above stone
        'bezel_thickness': 0.5,  # mm
        'pave_spacing': 0.2,  # mm between stones
        'stone_recess': 0.1,  # mm - how deep stone sits in setting
    }
    
    # Standard stone sizes (diameter in mm)
    STONE_SIZES = {
        'round_0.5ct': 5.2,
        'round_1ct': 6.5,
        'round_1.5ct': 7.4,
        'round_2ct': 8.1,
        'princess_0.5ct': 4.4,
        'princess_1ct': 5.5,
        'princess_1.5ct': 6.3,
        'princess_2ct': 7.0,
    }
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialize feature modeler with configuration."""
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}
        
    def add_features(self, mesh_data: Dict, geometry_data: Dict) -> Dict:
        """
        Add jewelry features to the mesh.
        
        Args:
            mesh_data: 3D mesh data from geometry reconstructor
            geometry_data: Original 2D geometry with stone markers
            
        Returns:
            Enhanced mesh data with features
        """
        vertices = mesh_data.get('vertices', []).copy()
        faces = mesh_data.get('faces', []).copy()
        
        stone_count = 0
        prong_count = 0
        
        # Process detected stones from input
        stones = geometry_data.get('stones', [])
        for stone_info in stones:
            stone_result = self._add_stone_with_setting(
                vertices, faces, stone_info, mesh_data.get('dimensions', {})
            )
            if stone_result:
                vertices = stone_result['vertices']
                faces = stone_result['faces']
                stone_count += stone_result.get('stones_added', 0)
                prong_count += stone_result.get('prongs_added', 0)
                
        # If no stones detected, add a default center stone
        if stone_count == 0 and mesh_data.get('dimensions'):
            stone_result = self._add_default_center_stone(
                vertices, faces, mesh_data['dimensions']
            )
            if stone_result:
                vertices = stone_result['vertices']
                faces = stone_result['faces']
                stone_count = stone_result.get('stones_added', 0)
                prong_count = stone_result.get('prongs_added', 0)
                
        # Calculate new normals
        normals = self._calculate_normals(vertices, faces)
        
        # Update dimensions
        vertices_array = np.array(vertices)
        dimensions = {
            'width': float(vertices_array[:, 0].max() - vertices_array[:, 0].min()),
            'height': float(vertices_array[:, 1].max() - vertices_array[:, 1].min()),
            'depth': float(vertices_array[:, 2].max() - vertices_array[:, 2].min()),
            'center': vertices_array.mean(axis=0).tolist()
        }
        
        return {
            'vertices': vertices,
            'faces': faces,
            'normals': normals,
            'dimensions': dimensions,
            'stone_count': stone_count,
            'prong_count': prong_count
        }
        
    def _add_stone_with_setting(self, vertices: List, faces: List, 
                                 stone_info: Dict, dimensions: Dict) -> Optional[Dict]:
        """
        Add a stone with appropriate setting to the mesh.
        
        Args:
            vertices: Current vertices
            faces: Current faces
            stone_info: Stone information from input processing
            dimensions: Mesh dimensions for positioning
            
        Returns:
            Updated mesh data or None if failed
        """
        stone_type = stone_info.get('type', 'round')
        center_2d = stone_info.get('center', [0, 0])
        
        # Convert 2D center to 3D (place on top surface)
        if dimensions.get('center'):
            base_z = dimensions['center'][2] + dimensions.get('depth', 2.0) / 2
        else:
            base_z = 2.0
            
        center_3d = [center_2d[0], center_2d[1], base_z]
        
        # Determine stone size
        if stone_info.get('radius'):
            stone_diameter = stone_info['radius'] * 2
        elif stone_info.get('size_mm'):
            stone_diameter = stone_info['size_mm']
        else:
            stone_diameter = self.STONE_SIZES['round_1ct']
            
        # Create stone geometry
        stone_vertices, stone_faces = self._create_round_stone(
            center_3d, stone_diameter
        )
        
        # Create prong setting
        prong_count = self.config['default_prong_count']
        prong_vertices, prong_faces = self._create_prong_setting(
            center_3d, stone_diameter, prong_count
        )
        
        # Combine with existing mesh
        vertex_offset = len(vertices)
        vertices.extend(stone_vertices)
        faces.extend([[f[0] + vertex_offset, f[1] + vertex_offset, f[2] + vertex_offset] 
                      for f in stone_faces])
        
        prong_offset = len(vertices)
        vertices.extend(prong_vertices)
        faces.extend([[f[0] + prong_offset, f[1] + prong_offset, f[2] + prong_offset] 
                      for f in prong_faces])
        
        return {
            'vertices': vertices,
            'faces': faces,
            'stones_added': 1,
            'prongs_added': prong_count
        }
        
    def _add_default_center_stone(self, vertices: List, faces: List, 
                                   dimensions: Dict) -> Dict:
        """
        Add a default center stone when none detected.
        
        Args:
            vertices: Current vertices
            faces: Current faces
            dimensions: Mesh dimensions
            
        Returns:
            Updated mesh data
        """
        center = dimensions.get('center', [0, 0, 0])
        stone_diameter = self.STONE_SIZES['round_1ct']
        
        # Place stone on top surface
        stone_center = [center[0], center[1], center[2] + dimensions.get('depth', 2.0) / 2]
        
        # Create stone
        stone_vertices, stone_faces = self._create_round_stone(
            stone_center, stone_diameter
        )
        
        # Create prong setting
        prong_count = self.config['default_prong_count']
        prong_vertices, prong_faces = self._create_prong_setting(
            stone_center, stone_diameter, prong_count
        )
        
        # Add to mesh
        vertex_offset = len(vertices)
        vertices.extend(stone_vertices)
        faces.extend([[f[0] + vertex_offset, f[1] + vertex_offset, f[2] + vertex_offset] 
                      for f in stone_faces])
        
        prong_offset = len(vertices)
        vertices.extend(prong_vertices)
        faces.extend([[f[0] + prong_offset, f[1] + prong_offset, f[2] + prong_offset] 
                      for f in prong_faces])
        
        return {
            'vertices': vertices,
            'faces': faces,
            'stones_added': 1,
            'prongs_added': prong_count
        }
        
    def _create_round_stone(self, center: List[float], diameter: float, 
                             segments: int = 32) -> Tuple[List, List]:
        """
        Create a round brilliant cut stone geometry.
        
        Args:
            center: Center position [x, y, z]
            diameter: Stone diameter
            segments: Number of angular segments
            
        Returns:
            Vertices and faces for the stone
        """
        vertices = []
        faces = []
        
        radius = diameter / 2
        crown_height = radius * 0.16  # Crown is ~16% of diameter
        pavilion_depth = radius * 0.43  # Pavilion is ~43% of diameter
        
        cx, cy, cz = center
        
        # Create crown (top part)
        # Table (flat top)
        table_radius = radius * 0.53
        for i in range(segments):
            angle = 2 * math.pi * i / segments
            x = cx + table_radius * math.cos(angle)
            y = cy + table_radius * math.sin(angle)
            vertices.append([x, y, cz + crown_height])
            
        # Crown facets
        crown_base_idx = len(vertices)
        for i in range(segments):
            angle = 2 * math.pi * i / segments
            x = cx + radius * math.cos(angle)
            y = cy + radius * math.sin(angle)
            vertices.append([x, y, cz])
            
        # Create crown faces
        for i in range(segments):
            next_i = (i + 1) % segments
            # Table to crown edge
            faces.append([i, next_i, crown_base_idx + i])
            faces.append([next_i, crown_base_idx + next_i, crown_base_idx + i])
            
        # Create pavilion (bottom part)
        pavilion_start = len(vertices)
        for i in range(segments):
            angle = 2 * math.pi * i / segments
            x = cx + radius * math.cos(angle)
            y = cy + radius * math.sin(angle)
            vertices.append([x, y, cz])
            
        # Culet (bottom point)
        culet_idx = len(vertices)
        vertices.append([cx, cy, cz - pavilion_depth])
        
        # Create pavilion faces
        for i in range(segments):
            next_i = (i + 1) % segments
            faces.append([pavilion_start + i, culet_idx, pavilion_start + next_i])
            
        return vertices, faces
        
    def _create_prong_setting(self, stone_center: List[float], stone_diameter: float,
                               prong_count: int = 4) -> Tuple[List, List]:
        """
        Create prong setting geometry.
        
        Args:
            stone_center: Center of the stone
            stone_diameter: Diameter of the stone
            prong_count: Number of prongs (4 or 6)
            
        Returns:
            Vertices and faces for prongs
        """
        vertices = []
        faces = []
        
        radius = stone_diameter / 2
        prong_radius = self.config['prong_radius']
        prong_height = self.config['prong_height']
        
        cx, cy, cz = stone_center
        
        # Create prongs at evenly spaced angles
        for i in range(prong_count):
            angle = 2 * math.pi * i / prong_count
            
            # Prong base position (on stone edge)
            base_x = cx + radius * math.cos(angle)
            base_y = cy + radius * math.sin(angle)
            base_z = cz
            
            # Prong tip position (above stone center, slightly inward)
            tip_radius = radius * 0.7  # Prongs curve inward
            tip_x = cx + tip_radius * math.cos(angle)
            tip_y = cy + tip_radius * math.sin(angle)
            tip_z = cz + prong_height
            
            # Create prong as tapered cylinder
            prong_verts, prong_faces = self._create_tapered_cylinder(
                [base_x, base_y, base_z],
                [tip_x, tip_y, tip_z],
                prong_radius,
                prong_radius * 0.6,  # Taper to smaller tip
                segments=8
            )
            
            # Offset and add
            offset = len(vertices)
            vertices.extend(prong_verts)
            faces.extend([[f[0] + offset, f[1] + offset, f[2] + offset] 
                          for f in prong_faces])
            
        return vertices, faces
        
    def _create_tapered_cylinder(self, base_center: List[float], 
                                  tip_center: List[float],
                                  base_radius: float, tip_radius: float,
                                  segments: int = 8) -> Tuple[List, List]:
        """
        Create a tapered cylinder between two points.
        
        Args:
            base_center: Base center position
            tip_center: Tip center position
            base_radius: Radius at base
            tip_radius: Radius at tip
            segments: Number of angular segments
            
        Returns:
            Vertices and faces
        """
        vertices = []
        faces = []
        
        # Direction vector
        direction = np.array(tip_center) - np.array(base_center)
        length = np.linalg.norm(direction)
        if length == 0:
            return vertices, faces
            
        direction = direction / length
        
        # Find perpendicular vectors
        if abs(direction[2]) < 0.9:
            perp1 = np.cross(direction, [0, 0, 1])
        else:
            perp1 = np.cross(direction, [1, 0, 0])
        perp1 = perp1 / np.linalg.norm(perp1)
        perp2 = np.cross(direction, perp1)
        
        # Create base and tip circles
        base_center = np.array(base_center)
        tip_center = np.array(tip_center)
        
        for i in range(segments):
            angle = 2 * math.pi * i / segments
            cos_a = math.cos(angle)
            sin_a = math.sin(angle)
            
            # Base vertex
            offset = base_radius * (cos_a * perp1 + sin_a * perp2)
            vertices.append((base_center + offset).tolist())
            
            # Tip vertex
            offset = tip_radius * (cos_a * perp1 + sin_a * perp2)
            vertices.append((tip_center + offset).tolist())
            
        # Create side faces
        for i in range(segments):
            next_i = (i + 1) % segments
            v1 = i * 2
            v2 = i * 2 + 1
            v3 = next_i * 2
            v4 = next_i * 2 + 1
            
            faces.append([v1, v3, v2])
            faces.append([v3, v4, v2])
            
        # Create base cap
        base_center_idx = len(vertices)
        vertices.append(base_center.tolist())
        for i in range(segments):
            next_i = (i + 1) % segments
            faces.append([base_center_idx, i * 2, next_i * 2])
            
        # Create tip cap
        tip_center_idx = len(vertices)
        vertices.append(tip_center.tolist())
        for i in range(segments):
            next_i = (i + 1) % segments
            faces.append([tip_center_idx, next_i * 2 + 1, i * 2 + 1])
            
        return vertices, faces
        
    def create_bezel_setting(self, stone_center: List[float], 
                              stone_diameter: float) -> Tuple[List, List]:
        """
        Create a bezel setting (rim around stone).
        
        Args:
            stone_center: Center of the stone
            stone_diameter: Diameter of the stone
            
        Returns:
            Vertices and faces for bezel
        """
        vertices = []
        faces = []
        
        radius = stone_diameter / 2
        bezel_thickness = self.config['bezel_thickness']
        bezel_height = stone_diameter * 0.3
        
        cx, cy, cz = stone_center
        segments = 32
        
        # Create inner and outer walls
        for i in range(segments):
            angle = 2 * math.pi * i / segments
            cos_a = math.cos(angle)
            sin_a = math.sin(angle)
            
            # Inner wall
            inner_r = radius
            vertices.append([
                cx + inner_r * cos_a,
                cy + inner_r * sin_a,
                cz
            ])
            vertices.append([
                cx + inner_r * cos_a,
                cy + inner_r * sin_a,
                cz + bezel_height
            ])
            
            # Outer wall
            outer_r = radius + bezel_thickness
            vertices.append([
                cx + outer_r * cos_a,
                cy + outer_r * sin_a,
                cz
            ])
            vertices.append([
                cx + outer_r * cos_a,
                cy + outer_r * sin_a,
                cz + bezel_height
            ])
            
        # Create faces
        for i in range(segments):
            next_i = (i + 1) % segments
            
            # Indices
            inner_bot = i * 4
            inner_top = i * 4 + 1
            outer_bot = i * 4 + 2
            outer_top = i * 4 + 3
            
            inner_bot_n = next_i * 4
            inner_top_n = next_i * 4 + 1
            outer_bot_n = next_i * 4 + 2
            outer_top_n = next_i * 4 + 3
            
            # Inner wall
            faces.append([inner_bot, inner_bot_n, inner_top])
            faces.append([inner_bot_n, inner_top_n, inner_top])
            
            # Outer wall
            faces.append([outer_bot, outer_top, outer_bot_n])
            faces.append([outer_bot_n, outer_top, outer_top_n])
            
            # Top rim
            faces.append([inner_top, inner_top_n, outer_top])
            faces.append([inner_top_n, outer_top_n, outer_top])
            
            # Bottom
            faces.append([inner_bot, outer_bot, inner_bot_n])
            faces.append([inner_bot_n, outer_bot, outer_bot_n])
            
        return vertices, faces
        
    def create_pave_setting(self, center: List[float], area_radius: float,
                             stone_diameter: float = 1.5) -> Tuple[List, List]:
        """
        Create pave setting (many small stones).
        
        Args:
            center: Center of the pave area
            area_radius: Radius of the area to fill
            stone_diameter: Diameter of each small stone
            
        Returns:
            Vertices and faces for pave stones
        """
        vertices = []
        faces = []
        
        spacing = stone_diameter + self.config['pave_spacing']
        
        # Calculate grid of stone positions
        num_rows = int(2 * area_radius / spacing)
        
        for row in range(-num_rows // 2, num_rows // 2 + 1):
            for col in range(-num_rows // 2, num_rows // 2 + 1):
                # Offset alternate rows
                x_offset = (row % 2) * spacing / 2
                
                x = center[0] + col * spacing + x_offset
                y = center[1] + row * spacing * 0.866  # Hexagonal packing
                z = center[2]
                
                # Check if within area
                dist = math.sqrt((x - center[0])**2 + (y - center[1])**2)
                if dist <= area_radius:
                    # Create small stone
                    stone_verts, stone_faces = self._create_round_stone(
                        [x, y, z], stone_diameter, segments=16
                    )
                    
                    offset = len(vertices)
                    vertices.extend(stone_verts)
                    faces.extend([[f[0] + offset, f[1] + offset, f[2] + offset] 
                                  for f in stone_faces])
                    
        return vertices, faces
        
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
            
            # Add to vertex normals
            normals[face[0]] += face_normal
            normals[face[1]] += face_normal
            normals[face[2]] += face_normal
            
        # Normalize
        norms = np.linalg.norm(normals, axis=1)
        norms[norms == 0] = 1
        normals = normals / norms[:, np.newaxis]
        
        return normals.tolist()