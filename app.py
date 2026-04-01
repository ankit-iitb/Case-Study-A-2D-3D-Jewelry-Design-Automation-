"""
Streamlit Web Interface for Jewelry CAD Automation System

This app provides a user-friendly interface to convert 2D jewelry designs
to 3D CAD models with configurable parameters.
"""

import streamlit as st
import json
import os
import tempfile
import zipfile
from pathlib import Path
from io import BytesIO

# Import the pipeline
from src.jewelry_cad.main import JewelryCADPipeline


def get_default_config():
    """Return default configuration dictionary."""
    return {
        "input": {
            "curve_resolution": 50,
            "dimension_regex": "(\\d+\\.?\\d*)\\s*mm",
            "symmetry_detection": True,
            "min_curve_length": 0.1
        },
        "geometry": {
            "default_thickness": 1.5,
            "default_depth": 2.0,
            "revolution_segments": 64,
            "smoothing_iterations": 3,
            "target_edge_length": 0.5,
            "reconstruction_method": "extrude"
        },
        "features": {
            "default_prong_count": 4,
            "prong_radius": 0.3,
            "prong_height": 1.5,
            "bezel_thickness": 0.5,
            "pave_spacing": 0.2,
            "stone_recess": 0.1
        },
        "constraints": {
            "metal_type": "gold_18k",
            "min_wall_thickness": 0.5,
            "max_wall_thickness": 5.0,
            "min_feature_size": 0.3,
            "tolerance": 0.1,
            "max_aspect_ratio": 10.0,
            "target_weight_range": [2.0, 30.0]
        },
        "output": {
            "stl_format": "binary",
            "include_normals": True,
            "units": "mm",
            "precision": 6
        }
    }


def merge_configs(user_config, default_config):
    """
    Merge user configuration with defaults.
    Missing fields will be filled with default values.
    """
    merged = default_config.copy()
    
    for section, values in user_config.items():
        if section in merged:
            if isinstance(values, dict):
                for key, value in values.items():
                    merged[section][key] = value
            else:
                merged[section] = values
        else:
            merged[section] = values
    
    return merged


def main():
    """Main Streamlit application."""
    
    st.set_page_config(
        page_title="Jewelry CAD Automation",
        page_icon="💎",
        layout="wide"
    )
    
    st.title("💎 2D to 3D Jewelry Design Automation")
    st.markdown("---")
    
    st.markdown("""
    Convert your 2D jewelry sketches and vector designs into production-ready 3D CAD models.
    Upload an SVG file and configure the processing parameters to generate STL output.
    """)
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Option to upload config or use defaults
        config_option = st.radio(
            "Configuration Source",
            ["Use Defaults", "Upload Config File", "Manual Configuration"]
        )
        
        config = get_default_config()
        
        if config_option == "Upload Config File":
            config_file = st.file_uploader("Upload Configuration (JSON)", type=["json"])
            if config_file:
                try:
                    user_config = json.loads(config_file.read())
                    config = merge_configs(user_config, get_default_config())
                    st.success("Configuration loaded successfully!")
                except Exception as e:
                    st.error(f"Error loading config: {e}")
                    st.info("Using default configuration.")
        
        elif config_option == "Manual Configuration":
            st.subheader("Input Processing")
            config["input"]["curve_resolution"] = st.slider(
                "Curve Resolution", 10, 100, 50,
                help="Points per curve segment"
            )
            config["input"]["symmetry_detection"] = st.checkbox(
                "Detect Symmetry", True
            )
            
            st.subheader("Geometry Reconstruction")
            config["geometry"]["default_thickness"] = st.number_input(
                "Default Thickness (mm)", 0.1, 10.0, 1.5
            )
            config["geometry"]["default_depth"] = st.number_input(
                "Default Depth (mm)", 0.1, 20.0, 2.0
            )
            config["geometry"]["reconstruction_method"] = st.selectbox(
                "Reconstruction Method",
                ["extrude", "revolution", "loft"]
            )
            
            st.subheader("Features")
            config["features"]["default_prong_count"] = st.selectbox(
                "Prong Count", [4, 6], index=0
            )
            config["features"]["prong_radius"] = st.number_input(
                "Prong Radius (mm)", 0.1, 2.0, 0.3
            )
            config["features"]["prong_height"] = st.number_input(
                "Prong Height (mm)", 0.5, 5.0, 1.5
            )
            
            st.subheader("Constraints")
            config["constraints"]["metal_type"] = st.selectbox(
                "Metal Type",
                ["gold_24k", "gold_18k", "gold_14k", "silver_925", "platinum", "palladium"],
                index=1
            )
            config["constraints"]["min_wall_thickness"] = st.number_input(
                "Min Wall Thickness (mm)", 0.1, 2.0, 0.5
            )
            
            st.subheader("Output")
            config["output"]["stl_format"] = st.selectbox(
                "STL Format", ["binary", "ascii"], index=0
            )
        
        st.markdown("---")
        st.markdown("### About")
        st.markdown("""
        This system automates the conversion of 2D jewelry designs 
        to 3D CAD models for manufacturing.
        
        **Supported Features:**
        - SVG file parsing
        - Automatic stone detection
        - Prong/bezel settings
        - Manufacturing validation
        - STL export
        """)
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("📁 Upload Design")
        
        # File uploader
        uploaded_file = st.file_uploader(
            "Upload SVG File",
            type=["svg"],
            help="Upload your 2D jewelry design in SVG format"
        )
        
        if uploaded_file:
            st.success(f"File uploaded: {uploaded_file.name}")
            
            # Display file info
            file_details = {
                "Filename": uploaded_file.name,
                "File size": f"{uploaded_file.size} bytes",
                "File type": uploaded_file.type
            }
            st.json(file_details)
            
            # Preview SVG
            with st.expander("Preview SVG", expanded=False):
                svg_content = uploaded_file.read().decode("utf-8")
                st.components.v1.html(svg_content, height=400, scrolling=True)
                uploaded_file.seek(0)  # Reset file pointer
    
    with col2:
        st.header("📊 Configuration Summary")
        
        # Display current configuration
        with st.expander("View Configuration", expanded=False):
            st.json(config)
    
    # Processing section
    st.markdown("---")
    st.header("🔄 Process Design")
    
    if uploaded_file:
        if st.button("Generate 3D Model", type="primary", use_container_width=True):
            with st.spinner("Processing your design..."):
                try:
                    # Create temporary directories
                    with tempfile.TemporaryDirectory() as temp_dir:
                        # Save uploaded file
                        input_path = os.path.join(temp_dir, "input.svg")
                        with open(input_path, "wb") as f:
                            f.write(uploaded_file.getbuffer())
                        
                        # Save config
                        config_path = os.path.join(temp_dir, "config.json")
                        with open(config_path, "w") as f:
                            json.dump(config, f, indent=2)
                        
                        # Create output directory
                        output_dir = os.path.join(temp_dir, "output")
                        os.makedirs(output_dir, exist_ok=True)
                        
                        # Run pipeline
                        pipeline = JewelryCADPipeline(config)
                        results = pipeline.process(input_path, output_dir, ["stl"])
                        
                        if "error" in results:
                            st.error(f"Processing failed: {results['error']}")
                        else:
                            st.success("✅ Model generated successfully!")
                            
                            # Display results
                            col1, col2, col3 = st.columns(3)
                            
                            with col1:
                                st.metric(
                                    "Vertices",
                                    results["metadata"]["total_vertices"]
                                )
                            
                            with col2:
                                st.metric(
                                    "Faces",
                                    results["metadata"]["total_faces"]
                                )
                            
                            with col3:
                                weight = results["metadata"]["estimated_weight_grams"]
                                st.metric(
                                    "Weight",
                                    f"{weight:.2f}g"
                                )
                            
                            # Display dimensions
                            dims = results["metadata"]["dimensions_mm"]
                            st.info(
                                f"📐 Dimensions: {dims['width']:.1f}mm × "
                                f"{dims['height']:.1f}mm × {dims['depth']:.1f}mm"
                            )
                            
                            # Display warnings if any
                            warnings = results["stages"]["constraint_handling"].get("warnings", [])
                            if warnings:
                                with st.expander("⚠️ Warnings", expanded=True):
                                    for warning in warnings:
                                        st.warning(warning)
                            
                            # Provide download
                            stl_path = os.path.join(output_dir, "model.stl")
                            if os.path.exists(stl_path):
                                with open(stl_path, "rb") as f:
                                    stl_bytes = f.read()
                                
                                st.download_button(
                                    label="📥 Download STL File",
                                    data=stl_bytes,
                                    file_name="jewelry_model.stl",
                                    mime="application/octet-stream",
                                    type="primary",
                                    use_container_width=True
                                )
                                
                                st.info(
                                    f"File size: {len(stl_bytes):,} bytes"
                                )
                
                except Exception as e:
                    st.error(f"An error occurred: {str(e)}")
                    st.exception(e)
    else:
        st.info("👆 Please upload an SVG file to begin processing.")
    
    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center'>
            <p>Jewelry CAD Automation System | Built with Streamlit</p>
            <p>Convert 2D jewelry designs to production-ready 3D CAD models</p>
        </div>
        """,
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()