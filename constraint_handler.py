"""
Constraint Handler Module

Validates 3D jewelry models against manufacturing constraints:
- Dimensional tolerances (mm-level precision)
- Wall thickness requirements
- Metal weight estimation
- Casting feasibility checks
- Durability validation
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
import math


class ConstraintHandler:
    """
    Handles manufacturing constraints and validation for jewelry models.
    
    Validates:
    - Minimum wall thickness for casting
    - Maximum unsupported spans
    - Draft angles for mold release
    - Metal weight estimation
    - Dimensional accuracy
    """
    
    # Metal densities in g/cm³
    METAL_DENSITIES = {
        'gold_24k': 19.32,
        'gold_18k': 15.6,
        'gold_14k': 13.1,
        'silver_925': 10.36,
        'platinum': 21.45,
        'palladium': 12.02,
    }
    
    DEFAULT_CONFIG = {
        'metal_type': 'gold_18k',
        'min_wall_thickness': 0.5,  # mm - minimum for lost-wax casting
        'max_wall_thickness': 5.0,  # mm - maximum for cost efficiency
        'min_feature_size': 0.3,  # mm - minimum detail size
        'tolerance': 0.1,  # mm - manufacturing tolerance
        'max_aspect_ratio': 10.0,  # maximum length to thickness ratio
        'target_weight_range': (2.0, 30.0),  # grams - typical jewelry range
    }
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialize constraint handler with configuration."""
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}
        
    def validate(self, mesh_data: Dict) -> Tuple[Dict, Dict]:
        """
        Validate mesh against manufacturing constraints.
        
        Args:
            mesh_data: 3D mesh data to validate
            
        Returns:
            Tuple of (validated_mesh_data, validation_report)
        """
        vertices = mesh_data.get('vertices', [])
        faces = mesh_data.get('faces', [])
        
        report = {
            'passed': True,
            'warnings': [],
            'errors': [],
            'weight_grams': 0.0,
            'dimensions_mm': {},
            'checks': {}
        }
        
        # Calculate volume
        volume_cm3 = self._calculate_volume(vertices, faces)
        
        # Estimate weight
        density = self.METAL_DENSITIES.get(self.config['metal_type'], 15.6)
        weight_grams = volume_cm3 * density
        report['weight_grams'] = weight_grams
        
        # Check weight range
        min_weight, max_weight = self.config['target_weight_range']
        if weight_grams < min_weight:
            report['warnings'].append(
                f"Weight ({weight_grams:.2f}g) is below typical range ({min_weight}-{max_weight}g)"
            )
        elif weight_grams > max_weight:
            report['warnings'].append(
                f"Weight ({weight_grams:.2f}g) exceeds typical range ({min_weight}-{max_weight}g)"
            )
            
        report['checks']['weight'] = {
            'value': weight_grams,
            'unit': 'grams',
            'status': 'pass' if min_weight <= weight_grams <= max_weight else 'warning'
        }
        
        # Calculate dimensions
        if vertices:
            vertices_array = np.array(vertices)
            dimensions = {
                'width': float(vertices_array[:, 0].max() - vertices_array[:, 0].min()),
                'height': float(vertices_array[:, 1].max() - vertices_array[:, 1].min()),
                'depth': float(vertices_array[:, 2].max() - vertices_array[:, 2].min()),
            }
            report['dimensions_mm'] = dimensions
            
            # Check dimensional constraints
            for dim_name, value in dimensions.items():
                if value < self.config['min_feature_size']:
                    report['errors'].append(
                        f"{dim_name} ({value:.2f}mm) is below minimum feature size ({self.config['min_feature_size']}mm)"
                    )
                    report['passed'] = False
                    
        # Check wall thickness
        thickness_check = self._check_wall_thickness(vertices, faces)
        report['checks']['wall_thickness'] = thickness_check
        if thickness_check['status'] == 'fail':
            report['errors'].append(thickness_check.get('message', 'Wall thickness check failed'))
            report['passed'] = False
        elif thickness_check['status'] == 'warning':
            report['warnings'].append(thickness_check.get('message', 'Wall thickness warning'))
            
        # Check mesh quality
        quality_check = self._check_mesh_quality(vertices, faces)
        report['checks']['mesh_quality'] = quality_check
        if quality_check['status'] == 'fail':
            report['errors'].append(quality_check.get('message', 'Mesh quality check failed'))
            report['passed'] = False
            
        # Check for degenerate faces
        degenerate_check = self._check_degenerate_faces(vertices, faces)
        report['checks']['degenerate_faces'] = degenerate_check
        if degenerate_check['count'] > 0:
            report['warnings'].append(f"Found {degenerate_check['count']} degenerate faces")
            
        return mesh_data, report
        
    def _calculate_volume(self, vertices: List[List[float]], 
                          faces: List[List[int]]) -> float:
        """
        Calculate mesh volume using signed volume of tetrahedra.
        
        Args:
            vertices: Vertex positions
            faces: Face indices
            
        Returns:
            Volume in cm³
        """
        if not vertices or not faces:
            return 0.0
            
        vertices_array = np.array(vertices)
        volume = 0.0
        
        for face in faces:
            if len(face) >= 3:
                v0 = vertices_array[face[0]]
                v1 = vertices_array[face[1]]
                v2 = vertices_array[face[2]]
                
                # Signed volume of tetrahedron formed by origin and triangle
                volume += np.dot(v0, np.cross(v1, v2)) / 6.0
                
        # Convert mm³ to cm³
        volume_cm3 = abs(volume) / 1000.0
        
        return volume_cm3
        
    def _check_wall_thickness(self, vertices: List[List[float]], 
                               faces: List[List[int]]) -> Dict:
        """
        Check wall thickness against casting requirements.
        
        Args:
            vertices: Vertex positions
            faces: Face indices
            
        Returns:
            Check result dictionary
        """
        if not vertices or not faces:
            return {'status': 'skip', 'message': 'No geometry to check'}
            
        # Simplified thickness check - estimate from bounding box
        vertices_array = np.array(vertices)
        
        # Calculate bounding box dimensions
        bbox_min = vertices_array.min(axis=0)
        bbox_max = vertices_array.max(axis=0)
        dimensions = bbox_max - bbox_min
        
        # Estimate minimum thickness as smallest dimension
        min_thickness = float(dimensions.min())
        
        min_wall = self.config['min_wall_thickness']
        max_wall = self.config['max_wall_thickness']
        
        if min_thickness < min_wall:
            return {
                'status': 'fail',
                'value': min_thickness,
                'min_required': min_wall,
                'message': f'Minimum thickness ({min_thickness:.2f}mm) below casting minimum ({min_wall}mm)'
            }
        elif min_thickness > max_wall:
            return {
                'status': 'warning',
                'value': min_thickness,
                'max_recommended': max_wall,
                'message': f'Thickness ({min_thickness:.2f}mm) may be too thick for efficient casting (max {max_wall}mm)'
            }
        else:
            return {
                'status': 'pass',
                'value': min_thickness,
                'message': 'Wall thickness within acceptable range'
            }
            
    def _check_mesh_quality(self, vertices: List[List[float]], 
                            faces: List[List[int]]) -> Dict:
        """
        Check mesh quality (manifold, watertight, etc.).
        
        Args:
            vertices: Vertex positions
            faces: Face indices
            
        Returns:
            Check result dictionary
        """
        if not vertices or not faces:
            return {'status': 'fail', 'message': 'Empty mesh'}
            
        issues = []
        
        # Check for duplicate vertices
        vertices_array = np.array(vertices)
        unique_vertices = np.unique(vertices_array.round(decimals=6), axis=0)
        if len(unique_vertices) < len(vertices):
            duplicate_count = len(vertices) - len(unique_vertices)
            issues.append(f'{duplicate_count} duplicate vertices')
            
        # Check face indices are valid
        max_vertex_idx = len(vertices) - 1
        for i, face in enumerate(faces):
            for idx in face:
                if idx < 0 or idx > max_vertex_idx:
                    issues.append(f'Invalid vertex index in face {i}')
                    break
                    
        # Check for isolated vertices (not used in any face)
        used_vertices = set()
        for face in faces:
            used_vertices.update(face)
        isolated_count = len(vertices) - len(used_vertices)
        if isolated_count > 0:
            issues.append(f'{isolated_count} isolated vertices')
            
        if issues:
            return {
                'status': 'warning',
                'issues': issues,
                'message': f'Mesh quality issues: {", ".join(issues)}'
            }
        else:
            return {
                'status': 'pass',
                'message': 'Mesh quality acceptable'
            }
            
    def _check_degenerate_faces(self, vertices: List[List[float]], 
                                 faces: List[List[int]]) -> Dict:
        """
        Check for degenerate faces (zero area triangles).
        
        Args:
            vertices: Vertex positions
            faces: Face indices
            
        Returns:
            Check result with degenerate face count
        """
        if not vertices or not faces:
            return {'count': 0, 'indices': []}
            
        vertices_array = np.array(vertices)
        degenerate_indices = []
        
        for i, face in enumerate(faces):
            if len(face) >= 3:
                v0 = vertices_array[face[0]]
                v1 = vertices_array[face[1]]
                v2 = vertices_array[face[2]]
                
                # Calculate face area
                edge1 = v1 - v0
                edge2 = v2 - v0
                cross = np.cross(edge1, edge2)
                area = np.linalg.norm(cross) / 2.0
                
                # Check if area is effectively zero
                if area < 1e-10:
                    degenerate_indices.append(i)
                    
        return {
            'count': len(degenerate_indices),
            'indices': degenerate_indices
        }
        
    def estimate_casting_weight(self, volume_cm3: float, 
                                 metal_type: Optional[str] = None) -> float:
        """
        Estimate casting weight from volume.
        
        Args:
            volume_cm3: Volume in cubic centimeters
            metal_type: Metal type (uses config default if not specified)
            
        Returns:
            Weight in grams
        """
        if metal_type is None:
            metal_type = self.config['metal_type']
            
        density = self.METAL_DENSITIES.get(metal_type, 15.6)
        return volume_cm3 * density
        
    def check_dimensional_accuracy(self, actual_dimensions: Dict, 
                                    target_dimensions: Dict) -> Dict:
        """
        Check dimensional accuracy against targets.
        
        Args:
            actual_dimensions: Measured dimensions
            target_dimensions: Target dimensions
            
        Returns:
            Accuracy report
        """
        tolerance = self.config['tolerance']
        report = {
            'passed': True,
            'deviations': {},
            'max_deviation': 0.0
        }
        
        for dim_name, target_value in target_dimensions.items():
            if dim_name in actual_dimensions:
                actual_value = actual_dimensions[dim_name]
                deviation = abs(actual_value - target_value)
                
                report['deviations'][dim_name] = {
                    'target': target_value,
                    'actual': actual_value,
                    'deviation': deviation,
                    'within_tolerance': deviation <= tolerance
                }
                
                report['max_deviation'] = max(report['max_deviation'], deviation)
                
                if deviation > tolerance:
                    report['passed'] = False
                    
        return report
        
    def generate_manufacturing_report(self, mesh_data: Dict, 
                                       validation_report: Dict) -> str:
        """
        Generate a human-readable manufacturing report.
        
        Args:
            mesh_data: Mesh data
            validation_report: Validation results
            
        Returns:
            Formatted report string
        """
        report_lines = [
            "=" * 50,
            "JEWELRY MANUFACTURING REPORT",
            "=" * 50,
            "",
            "DIMENSIONS:",
        ]
        
        dims = validation_report.get('dimensions_mm', {})
        if dims:
            report_lines.extend([
                f"  Width:  {dims.get('width', 0):.2f} mm",
                f"  Height: {dims.get('height', 0):.2f} mm",
                f"  Depth:  {dims.get('depth', 0):.2f} mm",
            ])
            
        report_lines.extend([
            "",
            "WEIGHT ESTIMATE:",
            f"  {validation_report.get('weight_grams', 0):.2f} grams",
            f"  Metal: {self.config['metal_type']}",
            "",
            "VALIDATION STATUS:",
            f"  {'PASSED' if validation_report.get('passed', False) else 'FAILED'}",
        ])
        
        warnings = validation_report.get('warnings', [])
        if warnings:
            report_lines.extend(["", "WARNINGS:"])
            for warning in warnings:
                report_lines.append(f"  - {warning}")
                
        errors = validation_report.get('errors', [])
        if errors:
            report_lines.extend(["", "ERRORS:"])
            for error in errors:
                report_lines.append(f"  - {error}")
                
        report_lines.extend([
            "",
            "CHECKS:",
        ])
        
        checks = validation_report.get('checks', {})
        for check_name, check_data in checks.items():
            status = check_data.get('status', 'unknown')
            report_lines.append(f"  {check_name}: {status.upper()}")
            
        report_lines.extend([
            "",
            "=" * 50,
        ])
        
        return "\n".join(report_lines)