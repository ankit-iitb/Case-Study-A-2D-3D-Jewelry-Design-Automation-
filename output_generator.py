"""
Output Generator Module

Exports 3D jewelry models to various CAD formats:
- STL (for 3D printing)
- OBJ (universal mesh format)
- 3DM (Rhino format)
- Generates validation reports
"""

import os
import struct
from pathlib import Path
from typing import Dict, List, Optional
import numpy as np


class OutputGenerator:
    """
    Generates output files from 3D mesh data.
    
    Supports formats:
    - STL (binary and ASCII)
    - OBJ (Wavefront)
    - 3DM (Rhino - basic support)
    """
    
    DEFAULT_CONFIG = {
        'stl_format': 'binary',  # 'binary' or 'ascii'
        'include_normals': True,
        'units': 'mm',
        'precision': 6,  # decimal places for ASCII output
    }
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialize output generator with configuration."""
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}
        
    def generate(self, mesh_data: Dict, output_dir: str, 
                 formats: List[str] = None) -> Dict[str, str]:
        """
        Generate output files in specified formats.
        
        Args:
            mesh_data: 3D mesh data with vertices, faces, normals
            output_dir: Output directory path
            formats: List of output formats ['stl', 'obj', '3dm']
            
        Returns:
            Dictionary mapping format to output file path
        """
        if formats is None:
            formats = ['stl']
            
        # Create output directory if it doesn't exist
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        output_files = {}
        vertices = mesh_data.get('vertices', [])
        faces = mesh_data.get('faces', [])
        normals = mesh_data.get('normals', [])
        
        for fmt in formats:
            try:
                if fmt.lower() == 'stl':
                    filepath = self._generate_stl(vertices, faces, normals, output_dir)
                    output_files['stl'] = filepath
                elif fmt.lower() == 'obj':
                    filepath = self._generate_obj(vertices, faces, normals, output_dir)
                    output_files['obj'] = filepath
                elif fmt.lower() == '3dm':
                    filepath = self._generate_3dm(vertices, faces, output_dir)
                    output_files['3dm'] = filepath
                else:
                    print(f"Warning: Unsupported format '{fmt}'")
            except Exception as e:
                print(f"Error generating {fmt} output: {e}")
                
        return output_files
        
    def _generate_stl(self, vertices: List[List[float]], faces: List[List[int]],
                       normals: List[List[float]], output_dir: str) -> str:
        """
        Generate STL file.
        
        Args:
            vertices: Vertex positions
            faces: Face indices
            normals: Vertex normals
            output_dir: Output directory
            
        Returns:
            Path to generated STL file
        """
        filepath = os.path.join(output_dir, 'model.stl')
        
        if self.config['stl_format'] == 'binary':
            self._write_stl_binary(filepath, vertices, faces, normals)
        else:
            self._write_stl_ascii(filepath, vertices, faces, normals)
            
        print(f"Generated STL: {filepath}")
        return filepath
        
    def _write_stl_binary(self, filepath: str, vertices: List[List[float]], 
                          faces: List[List[int]], normals: List[List[float]]):
        """
        Write binary STL file.
        
        Args:
            filepath: Output file path
            vertices: Vertex positions
            faces: Face indices
            normals: Vertex normals
        """
        with open(filepath, 'wb') as f:
            # Write header (80 bytes)
            header = b'Binary STL - Jewelry CAD Automation' + b'\0' * 47
            f.write(header[:80])
            
            # Write number of triangles
            f.write(struct.pack('<I', len(faces)))
            
            # Write each triangle
            for face in faces:
                if len(face) >= 3:
                    v0 = np.array(vertices[face[0]])
                    v1 = np.array(vertices[face[1]])
                    v2 = np.array(vertices[face[2]])
                    
                    # Calculate face normal
                    edge1 = v1 - v0
                    edge2 = v2 - v0
                    normal = np.cross(edge1, edge2)
                    norm_length = np.linalg.norm(normal)
                    if norm_length > 0:
                        normal = normal / norm_length
                    else:
                        normal = np.array([0, 0, 1])
                        
                    # Write normal
                    f.write(struct.pack('<3f', *normal))
                    
                    # Write vertices
                    f.write(struct.pack('<3f', *v0))
                    f.write(struct.pack('<3f', *v1))
                    f.write(struct.pack('<3f', *v2))
                    
                    # Write attribute byte count
                    f.write(struct.pack('<H', 0))
                    
    def _write_stl_ascii(self, filepath: str, vertices: List[List[float]], 
                         faces: List[List[int]], normals: List[List[float]]):
        """
        Write ASCII STL file.
        
        Args:
            filepath: Output file path
            vertices: Vertex positions
            faces: Face indices
            normals: Vertex normals
        """
        precision = self.config['precision']
        
        with open(filepath, 'w') as f:
            f.write("solid jewelry_model\n")
            
            for face in faces:
                if len(face) >= 3:
                    v0 = np.array(vertices[face[0]])
                    v1 = np.array(vertices[face[1]])
                    v2 = np.array(vertices[face[2]])
                    
                    # Calculate face normal
                    edge1 = v1 - v0
                    edge2 = v2 - v0
                    normal = np.cross(edge1, edge2)
                    norm_length = np.linalg.norm(normal)
                    if norm_length > 0:
                        normal = normal / norm_length
                    else:
                        normal = np.array([0, 0, 1])
                        
                    f.write(f"  facet normal {normal[0]:.{precision}f} {normal[1]:.{precision}f} {normal[2]:.{precision}f}\n")
                    f.write("    outer loop\n")
                    f.write(f"      vertex {v0[0]:.{precision}f} {v0[1]:.{precision}f} {v0[2]:.{precision}f}\n")
                    f.write(f"      vertex {v1[0]:.{precision}f} {v1[1]:.{precision}f} {v1[2]:.{precision}f}\n")
                    f.write(f"      vertex {v2[0]:.{precision}f} {v2[1]:.{precision}f} {v2[2]:.{precision}f}\n")
                    f.write("    endloop\n")
                    f.write("  endfacet\n")
                    
            f.write("endsolid jewelry_model\n")
            
    def _generate_obj(self, vertices: List[List[float]], faces: List[List[int]],
                      normals: List[List[float]], output_dir: str) -> str:
        """
        Generate OBJ file.
        
        Args:
            vertices: Vertex positions
            faces: Face indices
            normals: Vertex normals
            output_dir: Output directory
            
        Returns:
            Path to generated OBJ file
        """
        filepath = os.path.join(output_dir, 'model.obj')
        precision = self.config['precision']
        
        with open(filepath, 'w') as f:
            f.write("# Jewelry CAD Model\n")
            f.write("# Generated by Jewelry CAD Automation System\n\n")
            
            # Write vertices
            f.write("# Vertices\n")
            for v in vertices:
                f.write(f"v {v[0]:.{precision}f} {v[1]:.{precision}f} {v[2]:.{precision}f}\n")
                
            f.write("\n")
            
            # Write normals if available
            if normals and self.config['include_normals']:
                f.write("# Normals\n")
                for n in normals:
                    f.write(f"vn {n[0]:.{precision}f} {n[1]:.{precision}f} {n[2]:.{precision}f}\n")
                f.write("\n")
                
            # Write faces (OBJ uses 1-based indexing)
            f.write("# Faces\n")
            for face in faces:
                if len(face) >= 3:
                    if normals:
                        f.write(f"f {face[0]+1}//{face[0]+1} {face[1]+1}//{face[1]+1} {face[2]+1}//{face[2]+1}\n")
                    else:
                        f.write(f"f {face[0]+1} {face[1]+1} {face[2]+1}\n")
                        
        print(f"Generated OBJ: {filepath}")
        return filepath
        
    def _generate_3dm(self, vertices: List[List[float]], faces: List[List[int]],
                       output_dir: str) -> str:
        """
        Generate basic 3DM file (Rhino format).
        
        Note: Full 3DM support requires the rhino3dm library.
        This generates a simplified version that can be imported.
        
        Args:
            vertices: Vertex positions
            faces: Face indices
            output_dir: Output directory
            
        Returns:
            Path to generated 3DM file
        """
        # Try to use rhino3dm if available
        try:
            import rhino3dm as rh
            
            filepath = os.path.join(output_dir, 'model.3dm')
            
            # Create Rhino file
            model = rh.File3dm()
            
            # Create mesh
            mesh = rh.Mesh()
            
            # Add vertices
            for v in vertices:
                mesh.Vertices.Add(v[0], v[1], v[2])
                
            # Add faces
            for face in faces:
                if len(face) >= 3:
                    mesh.Faces.AddFace(face[0], face[1], face[2])
                    
            # Compute normals
            mesh.Normals.ComputeNormals()
            
            # Add mesh to document
            model.Objects.AddMesh(mesh)
            
            # Set units to millimeters
            model.Settings.ModelUnitSystem = rh.UnitSystem.Millimeters
            
            # Save file
            model.Write(filepath, 5)  # Version 5
            
            print(f"Generated 3DM: {filepath}")
            return filepath
            
        except ImportError:
            print("Warning: rhino3dm not available. Generating OBJ as fallback.")
            return self._generate_obj(vertices, [], [], output_dir)
            
    def generate_report(self, validation_report: Dict, output_dir: str) -> str:
        """
        Generate validation report file.
        
        Args:
            validation_report: Validation results
            output_dir: Output directory
            
        Returns:
            Path to generated report file
        """
        filepath = os.path.join(output_dir, 'validation_report.txt')
        
        lines = [
            "=" * 60,
            "JEWELRY CAD MODEL - VALIDATION REPORT",
            "=" * 60,
            "",
            f"Status: {'PASSED' if validation_report.get('passed', False) else 'FAILED'}",
            "",
        ]
        
        # Dimensions
        dims = validation_report.get('dimensions_mm', {})
        if dims:
            lines.extend([
                "DIMENSIONS (mm):",
                f"  Width:  {dims.get('width', 0):.2f}",
                f"  Height: {dims.get('height', 0):.2f}",
                f"  Depth:  {dims.get('depth', 0):.2f}",
                "",
            ])
            
        # Weight
        lines.extend([
            "WEIGHT ESTIMATE:",
            f"  {validation_report.get('weight_grams', 0):.2f} grams",
            "",
        ])
        
        # Checks
        checks = validation_report.get('checks', {})
        if checks:
            lines.append("VALIDATION CHECKS:")
            for check_name, check_data in checks.items():
                status = check_data.get('status', 'unknown').upper()
                lines.append(f"  {check_name}: {status}")
            lines.append("")
            
        # Warnings
        warnings = validation_report.get('warnings', [])
        if warnings:
            lines.append("WARNINGS:")
            for warning in warnings:
                lines.append(f"  - {warning}")
            lines.append("")
            
        # Errors
        errors = validation_report.get('errors', [])
        if errors:
            lines.append("ERRORS:")
            for error in errors:
                lines.append(f"  - {error}")
            lines.append("")
            
        lines.extend([
            "=" * 60,
            "Generated by Jewelry CAD Automation System",
            "=" * 60,
        ])
        
        with open(filepath, 'w') as f:
            f.write('\n'.join(lines))
            
        print(f"Generated report: {filepath}")
        return filepath
        
    def generate_metadata(self, mesh_data: Dict, output_dir: str) -> str:
        """
        Generate metadata JSON file.
        
        Args:
            mesh_data: Mesh data
            output_dir: Output directory
            
        Returns:
            Path to generated metadata file
        """
        import json
        
        filepath = os.path.join(output_dir, 'metadata.json')
        
        metadata = {
            'vertex_count': len(mesh_data.get('vertices', [])),
            'face_count': len(mesh_data.get('faces', [])),
            'dimensions': mesh_data.get('dimensions', {}),
            'units': self.config['units'],
            'format_version': '1.0',
        }
        
        with open(filepath, 'w') as f:
            json.dump(metadata, f, indent=2)
            
        print(f"Generated metadata: {filepath}")
        return filepath