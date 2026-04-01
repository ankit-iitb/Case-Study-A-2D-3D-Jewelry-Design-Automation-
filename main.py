"""
2D to 3D Jewelry Design Automation System
Main application entry point

This module provides automated conversion of 2D jewelry sketches/vector files
into production-ready 3D CAD models with parametric editing capabilities.
"""

import argparse
import sys
from pathlib import Path

from .input_processor import InputProcessor
from .geometry_reconstructor import GeometryReconstructor
from .feature_modeler import FeatureModeler
from .constraint_handler import ConstraintHandler
from .output_generator import OutputGenerator


class JewelryCADPipeline:
    """
    End-to-end pipeline for converting 2D jewelry designs to 3D CAD models.
    
    Pipeline stages:
    1. Input Processing: Parse SVG/vector files, extract geometry
    2. Geometry Reconstruction: Convert 2D curves to 3D surfaces
    3. Feature Modeling: Add stones, prongs, mounts
    4. Constraint Handling: Validate dimensions, weight, manufacturability
    5. Output Generation: Export as STL/3DM files
    """
    
    def __init__(self, config=None):
        """Initialize the pipeline with optional configuration."""
        self.config = config or {}
        self.input_processor = InputProcessor(self.config.get('input', {}))
        self.geometry_reconstructor = GeometryReconstructor(self.config.get('geometry', {}))
        self.feature_modeler = FeatureModeler(self.config.get('features', {}))
        self.constraint_handler = ConstraintHandler(self.config.get('constraints', {}))
        self.output_generator = OutputGenerator(self.config.get('output', {}))
        
    def process(self, input_file: str, output_dir: str, output_formats: list = None) -> dict:
        """
        Process a 2D jewelry design file and generate 3D CAD output.
        
        Args:
            input_file: Path to input SVG/vector file
            output_dir: Directory for output files
            output_formats: List of output formats ['stl', '3dm']
            
        Returns:
            Dictionary containing processing results and metadata
        """
        if output_formats is None:
            output_formats = ['stl']
            
        results = {
            'input_file': input_file,
            'output_dir': output_dir,
            'stages': {},
            'metadata': {}
        }
        
        try:
            # Stage 1: Input Processing
            print("Stage 1: Processing input file...")
            geometry_data = self.input_processor.process(input_file)
            results['stages']['input_processing'] = {
                'status': 'success',
                'geometry_extracted': len(geometry_data.get('curves', [])),
                'symmetry_detected': geometry_data.get('symmetry', None)
            }
            
            # Stage 2: Geometry Reconstruction
            print("Stage 2: Reconstructing 3D geometry...")
            mesh_data = self.geometry_reconstructor.reconstruct(geometry_data)
            results['stages']['geometry_reconstruction'] = {
                'status': 'success',
                'vertices': len(mesh_data.get('vertices', [])),
                'faces': len(mesh_data.get('faces', []))
            }
            
            # Stage 3: Feature Modeling
            print("Stage 3: Modeling features (stones, prongs, mounts)...")
            featured_mesh = self.feature_modeler.add_features(mesh_data, geometry_data)
            results['stages']['feature_modeling'] = {
                'status': 'success',
                'stones_added': featured_mesh.get('stone_count', 0),
                'prongs_added': featured_mesh.get('prong_count', 0)
            }
            
            # Stage 4: Constraint Handling
            print("Stage 4: Validating constraints...")
            validated_mesh, validation_report = self.constraint_handler.validate(featured_mesh)
            results['stages']['constraint_handling'] = {
                'status': 'success',
                'validation_passed': validation_report.get('passed', False),
                'warnings': validation_report.get('warnings', []),
                'weight_estimate': validation_report.get('weight_grams', 0)
            }
            
            # Stage 5: Output Generation
            print("Stage 5: Generating output files...")
            output_files = self.output_generator.generate(
                validated_mesh, 
                output_dir, 
                output_formats
            )
            results['stages']['output_generation'] = {
                'status': 'success',
                'files_generated': output_files
            }
            
            results['metadata'] = {
                'total_vertices': len(validated_mesh.get('vertices', [])),
                'total_faces': len(validated_mesh.get('faces', [])),
                'dimensions_mm': validated_mesh.get('dimensions', {}),
                'estimated_weight_grams': validation_report.get('weight_grams', 0)
            }
            
            print("\n✓ Pipeline completed successfully!")
            return results
            
        except Exception as e:
            print(f"\n✗ Pipeline failed: {str(e)}")
            results['error'] = str(e)
            return results


def main():
    """Main entry point for the jewelry CAD automation system."""
    parser = argparse.ArgumentParser(
        description='Convert 2D jewelry designs to 3D CAD models'
    )
    parser.add_argument(
        'input',
        help='Input SVG or vector file path'
    )
    parser.add_argument(
        '-o', '--output-dir',
        default='./output',
        help='Output directory for generated files (default: ./output)'
    )
    parser.add_argument(
        '-f', '--formats',
        nargs='+',
        default=['stl'],
        choices=['stl', '3dm', 'obj'],
        help='Output formats (default: stl)'
    )
    parser.add_argument(
        '-c', '--config',
        help='Configuration file path (JSON)'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    
    args = parser.parse_args()
    
    # Load configuration if provided
    config = {}
    if args.config:
        import json
        with open(args.config, 'r') as f:
            config = json.load(f)
    
    # Create output directory
    Path(args.output_dir).mkdir(parents=True, exist_ok=True)
    
    # Initialize and run pipeline
    pipeline = JewelryCADPipeline(config)
    results = pipeline.process(args.input, args.output_dir, args.formats)
    
    # Print summary
    if args.verbose:
        import json
        print("\n" + "="*50)
        print("PROCESSING SUMMARY")
        print("="*50)
        print(json.dumps(results, indent=2))
    
    # Exit with appropriate code
    if 'error' in results:
        sys.exit(1)
    sys.exit(0)


if __name__ == '__main__':
    main()