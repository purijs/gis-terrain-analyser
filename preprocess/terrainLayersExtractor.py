import subprocess
import os
import sys

def run_gdaldem(command, output_file, cog_output_file):
    """
    Run the gdaldem command and convert the result to COG format.
    
    Parameters:
    - command: list, the gdaldem command to run
    - output_file: str, path to the intermediate output file
    - cog_output_file: str, path to the final COG file
    """
    try:
        # Run the gdaldem command
        print(f"Running: {' '.join(command)}")
        subprocess.run(command, check=True)
        print(f"Generated: {output_file}")

        # Convert to COG
        cog_command = [
            "gdal_translate",
            output_file,
            cog_output_file,
            "-of", "COG",
            "-co", "COMPRESS=LZW"
        ]
        print(f"Converting to COG: {' '.join(cog_command)}")
        subprocess.run(cog_command, check=True)
        print(f"COG Created: {cog_output_file}")

        # Delete the intermediate file
        if os.path.exists(output_file):
            os.remove(output_file)
            print(f"Deleted intermediate file: {output_file}")

    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")
        sys.exit(1)

def generate_terrain_layers(slope_raster):
    """
    Generate TPI, TRI, Roughness, and Aspect layers from the input slope raster.
    
    Parameters:
    - slope_raster: str, path to the input slope raster
    """
    output_paths = {
        "tri": "global_rasters/merged_tri.tif",
        "tpi": "global_rasters/merged_tpi.tif",
        "roughness": "global_rasters/merged_roughness.tif",
        "aspect": "global_rasters/merged_aspect.tif"
    }

    intermediate_files = {
        "tri": "temp_tri.tif",
        "tpi": "temp_tpi.tif",
        "roughness": "temp_roughness.tif",
        "aspect": "temp_aspect.tif"
    }

    # Generate TRI (Terrain Ruggedness Index)
    run_gdaldem(
        ["gdaldem", "TRI", slope_raster, intermediate_files["tri"], "-co", "COMPRESS=LZW"],
        intermediate_files["tri"],
        output_paths["tri"]
    )

    # Generate TPI (Topographic Position Index)
    run_gdaldem(
        ["gdaldem", "TPI", slope_raster, intermediate_files["tpi"], "-co", "COMPRESS=LZW"],
        intermediate_files["tpi"],
        output_paths["tpi"]
    )

    # Generate Roughness
    run_gdaldem(
        ["gdaldem", "roughness", slope_raster, intermediate_files["roughness"], "-co", "COMPRESS=LZW"],
        intermediate_files["roughness"],
        output_paths["roughness"]
    )

    # Generate Aspect
    run_gdaldem(
        ["gdaldem", "aspect", slope_raster, intermediate_files["aspect"], "-co", "COMPRESS=LZW"],
        intermediate_files["aspect"],
        output_paths["aspect"]
    )

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python terrainLayersExtractor.py <input_slope_raster>")
        sys.exit(1)

    # Get the input slope raster from command-line argument
    input_slope_raster = sys.argv[1]

    if not os.path.exists(input_slope_raster):
        print(f"Error: Input file '{input_slope_raster}' does not exist.")
        sys.exit(1)

    # Generate terrain layers
    generate_terrain_layers(input_slope_raster)
