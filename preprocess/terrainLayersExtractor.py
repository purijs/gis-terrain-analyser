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

def generate_terrain_layers(interpolated_raster):
    """
    Generate TPI, TRI, Roughness, and Aspect layers from the input slope raster.
    
    Parameters:
    - interpolated_raster: str, path to the input slope raster
    """
    output_paths = {
        "tri": "data/output/tif/cog_merged_tri.tif",
        "tpi": "data/output/tif/cog_merged_tpi.tif",
        "roughness": "data/output/tif/cog_merged_roughness.tif",
        "aspect": "data/output/tif/cog_merged_aspect.tif",
        "slope": "data/output/tif/cog_merged_slope.tif"
    }

    intermediate_files = {
        "tri": "data/output/tif/temp_tri.tif",
        "tpi": "data/output/tif/temp_tpi.tif",
        "roughness": "data/output/tif/temp_roughness.tif",
        "aspect": "data/output/tif/temp_aspect.tif",
        "slope": "data/output/tif/temp_slope.tif"
    }

    # Generate TRI (Terrain Ruggedness Index)
    run_gdaldem(
        ["gdaldem", "TRI", interpolated_raster, intermediate_files["tri"], "-co", "COMPRESS=LZW"],
        intermediate_files["tri"],
        output_paths["tri"]
    )

    # Generate TPI (Topographic Position Index)
    run_gdaldem(
        ["gdaldem", "TPI", interpolated_raster, intermediate_files["tpi"], "-co", "COMPRESS=LZW"],
        intermediate_files["tpi"],
        output_paths["tpi"]
    )

    # Generate Roughness
    run_gdaldem(
        ["gdaldem", "roughness", interpolated_raster, intermediate_files["roughness"], "-co", "COMPRESS=LZW"],
        intermediate_files["roughness"],
        output_paths["roughness"]
    )

    # Generate Aspect
    run_gdaldem(
        ["gdaldem", "aspect", interpolated_raster, intermediate_files["aspect"], "-co", "COMPRESS=LZW"],
        intermediate_files["aspect"],
        output_paths["aspect"]
    )

    # Generate Slope
    run_gdaldem(
        ["gdaldem", "slope", interpolated_raster, intermediate_files["slope"], "-co", "COMPRESS=LZW"],
        intermediate_files["slope"],
        output_paths["slope"]
    )

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python terrainLayersExtractor.py <input_interpolated_raster>")
        sys.exit(1)

    # Get the input slope raster from command-line argument
    input_interpolated_raster = sys.argv[1]

    if not os.path.exists(input_interpolated_raster):
        print(f"Error: Input file '{input_interpolated_raster}' does not exist.")
        sys.exit(1)

    # Generate terrain layers
    generate_terrain_layers(input_interpolated_raster)
