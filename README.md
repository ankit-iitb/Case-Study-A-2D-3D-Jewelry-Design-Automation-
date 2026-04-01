# 2D to 3D Jewelry Design Automation System

## Overview

This system automates the conversion of 2D jewelry sketches and vector designs into production-ready 3D CAD models. It reduces the manual CAD effort required in the jewelry design workflow from 1-3 days to minutes.

## Features

- **Input Processing**: Parses SVG files with paths, shapes, and annotations
- **Geometry Reconstruction**: Converts 2D curves to 3D surfaces using extrusion, revolution, or lofting
- **Feature Modeling**: Automatically adds stones, prongs, mounts, and settings
- **Constraint Validation**: Validates models against manufacturing constraints (dimensions, weight, wall thickness)
- **Multi-Format Export**: Outputs to STL, OBJ, and 3DM (Rhino) formats

## Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Setup

```bash
# Clone or download the project
cd jewelry-cad-automation

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Dependencies

- `numpy>=1.21.0` - Numerical computing
- `svgpathtools>=1.6.0` - SVG file parsing
- `trimesh>=3.9.0` - 3D mesh operations (optional)
- `rhino3dm>=0.17.0` - Rhino 3DM export (optional)

## Usage

### Web Interface (Streamlit)

The easiest way to use the system is through the web interface:

```bash
# Install dependencies
pip install -r requirements.txt

# Run the Streamlit app
streamlit run app.py
```

The web interface allows you to:
- Upload SVG files directly in your browser
- Configure parameters through an interactive UI
- Preview your SVG design
- Download the generated STL file

### Command Line Interface

```bash
python -m src.jewelry_cad.main input_design.svg -o ./output
```

### Command Line Options

```
usage: main.py [-h] [-o OUTPUT_DIR] [-f {stl,3dm,obj} [{stl,3dm,obj} ...]]
               [-c CONFIG] [-v] input

Convert 2D jewelry designs to 3D CAD models

positional arguments:
  input                 Input SVG or vector file path

optional arguments:
  -h, --help            show this help message and exit
  -o OUTPUT_DIR, --output-dir OUTPUT_DIR
                        Output directory for generated files (default: ./output)
  -f {stl,3dm,obj} [{stl,3dm,obj} ...], --formats {stl,3dm,obj} [{stl,3dm,obj} ...]
                        Output formats (default: stl)
  -c CONFIG, --config CONFIG
                        Configuration file path (JSON)
  -v, --verbose         Enable verbose output
```

### Examples

```bash
# Convert SVG to STL
python -m src.jewelry_cad.main ring_design.svg

# Convert to multiple formats
python -m src.jewelry_cad.main necklace.svg -f stl obj 3dm -o ./results

# Use custom configuration
python -m src.jewelry_cad.main bracelet.svg -c config.json -v
```

### Configuration File

Create a JSON configuration file to customize behavior:

```json
{
  "input": {
    "curve_resolution": 50,
    "symmetry_detection": true
  },
  "geometry": {
    "default_thickness": 1.5,
    "default_depth": 2.0,
    "reconstruction_method": "extrude"
  },
  "features": {
    "default_prong_count": 4,
    "prong_radius": 0.3
  },
  "constraints": {
    "metal_type": "gold_18k",
    "min_wall_thickness": 0.5
  },
  "output": {
    "stl_format": "binary",
    "precision": 6
  }
}
```

## Architecture

### Pipeline Stages

1. **Input Processing** (`input_processor.py`)
   - Parses SVG files
   - Extracts curves, points, and dimensions
   - Detects symmetry axes and stone markers

2. **Geometry Reconstruction** (`geometry_reconstructor.py`)
   - Converts 2D curves to 3D meshes
   - Supports extrusion, revolution, and lofting
   - Generates vertex normals

3. **Feature Modeling** (`feature_modeler.py`)
   - Adds stones (round brilliant, princess cut)
   - Creates prong settings (4-prong, 6-prong)
   - Supports bezel and pave settings

4. **Constraint Handling** (`constraint_handler.py`)
   - Validates dimensions and tolerances
   - Estimates metal weight
   - Checks manufacturability

5. **Output Generation** (`output_generator.py`)
   - Exports to STL (binary/ASCII)
   - Exports to OBJ format
   - Exports to 3DM (Rhino) format

## Input Format

### SVG File Requirements

- Use standard SVG format with paths and shapes
- Dimensions can be annotated in text elements (e.g., "10mm")
- Stone positions can be indicated with circles
- The system extracts:
  - Path curves (M, L, C, Q commands)
  - Circle positions (stone markers)
  - Dimension annotations

### Example SVG Structure

```svg
<svg viewBox="0 0 100 100">
  <!-- Ring band -->
  <path d="M 10 50 C 10 30 90 30 90 50 C 90 70 10 70 10 50" />
  
  <!-- Stone marker -->
  <circle cx="50" cy="50" r="5" fill="red" />
  
  <!-- Dimension annotation -->
  <text x="50" y="20">10mm</text>
</svg>
```

## Output Files

The system generates:

- `model.stl` - 3D mesh for 3D printing
- `model.obj` - Universal mesh format
- `model.3dm` - Rhino format (if rhino3dm installed)
- `validation_report.txt` - Manufacturing validation report
- `metadata.json` - Model metadata

## Manufacturing Constraints

### Supported Metals

| Metal | Density (g/cm³) |
|-------|-----------------|
| Gold 24K | 19.32 |
| Gold 18K | 15.60 |
| Gold 14K | 13.10 |
| Silver 925 | 10.36 |
| Platinum | 21.45 |
| Palladium | 12.02 |

### Validation Checks

- **Wall Thickness**: 0.5mm minimum for lost-wax casting
- **Feature Size**: 0.3mm minimum detail size
- **Weight Range**: 2-30 grams typical for jewelry
- **Mesh Quality**: Checks for degenerate faces and isolated vertices

## Technical Details

### Supported Reconstruction Methods

1. **Extrusion**: Extends 2D profile along depth axis
2. **Revolution**: Rotates 2D profile around an axis
3. **Lofting**: Blends between multiple 2D profiles

### Stone Types

- Round Brilliant Cut
- Princess Cut
- Custom sizes supported

### Setting Types

- 4-Prong Setting
- 6-Prong Setting
- Bezel Setting
- Pave Setting

## Limitations

- Input must be in SVG format
- Complex organic shapes may require manual refinement
- 3DM export requires rhino3dm library
- Weight estimation is approximate

## Future Enhancements

- Support for DXF and AI file formats
- Machine learning-based feature detection
- Automatic stone type detection from markers
- Integration with Rhino/Matrix plugins
- Real-time weight optimization
- Batch processing support

## License

This project is developed for educational purposes as part of a college project.

## Contact

For questions or issues, please refer to the project documentation or contact the development team.

---

**Note**: This system is designed to assist jewelry CAD designers, not replace them. Final models should always be reviewed by experienced professionals before manufacturing.