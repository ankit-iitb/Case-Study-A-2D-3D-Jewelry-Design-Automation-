"""
Jewelry CAD Automation System

A system for converting 2D jewelry designs to 3D CAD models.
"""

__version__ = "1.0.0"
__author__ = "Jewelry CAD Team"

from .main import JewelryCADPipeline
from .input_processor import InputProcessor
from .geometry_reconstructor import GeometryReconstructor
from .feature_modeler import FeatureModeler
from .constraint_handler import ConstraintHandler
from .output_generator import OutputGenerator

__all__ = [
    'JewelryCADPipeline',
    'InputProcessor',
    'GeometryReconstructor',
    'FeatureModeler',
    'ConstraintHandler',
    'OutputGenerator',
]