import subprocess
import os
import sys
import geopandas as gpd

def get_bounding_box_from_gpkg(input_gpkg):
    """
    Get the bounding box from the input GeoPackage file.
    
    Parameters:
    - input_gpkg: str, path to the input GeoPackage file
    
    Returns:
    - tuple: (minx, miny, maxx, maxy) coordinates of the bounding box
    """
    gdf = gpd.read_file(input_gpkg)
    bounds = gdf.total_bounds  # (minx, miny, maxx, maxy)
    return bounds

def interpolate_raster(input_gpkg, output_raster, attribute_name):
    """
    Interpolates the specified attribute from the input GeoPackage file to create a raster.
    
    Parameters:
    - input_gpkg: str, path to the input GeoPackage file
    - output_raster: str, path to the output raster file (GeoTIFF)
    - attribute_name: str, attribute field in the input GeoPackage to interpolate
    
    Returns:
    - None
    """
    try:
        # Check if input file exists
        if not os.path.exists(input_gpkg):
            print(f"Error: Input file '{input_gpkg}' does not exist.")
            sys.exit(1)

        # Get the bounding box from the input GeoPackage
        minx, miny, maxx, maxy = get_bounding_box_from_gpkg(input_gpkg)

        # Construct the gdal_grid command for interpolation
        command = [
            "gdal_grid",
            "-zfield", attribute_name,
            "-a", "invdist:power=2.0",
            "-txe", str(minx), str(maxx),  # Use the bounding box values
            "-tye", str(miny), str(maxy),  # Use the bounding box values
            "-outsize", "800", "800",  # You can adjust the output size as needed
            "-of", "GTiff",
            "-co", "COMPRESS=LZW",
            "--config", "GDAL_NUM_THREADS", "ALL_CPUS",
            input_gpkg,
            output_raster
        ]

        # Run the gdal_grid command
        print(f"Running command: {' '.join(command)}")
        subprocess.run(command, check=True)
        print(f"Raster interpolated and saved to '{output_raster}'.")

    except subprocess.CalledProcessError as e:
        print(f"Error running gdal_grid: {e}")
        sys.exit(1)

def mask_raster(input_gpkg, raster_to_mask, output_masked_raster):
    """
    Masks the raster using the input GeoPackage file and saves the result.

    Parameters:
    - input_gpkg: str, path to the input GeoPackage file for masking
    - raster_to_mask: str, path to the raster file to mask
    - output_masked_raster: str, path to save the masked raster

    Returns:
    - None
    """
    try:
        # Check if input files exist
        if not os.path.exists(raster_to_mask):
            print(f"Error: Raster file '{raster_to_mask}' does not exist.")
            sys.exit(1)

        if not os.path.exists(input_gpkg):
            print(f"Error: GeoPackage file '{input_gpkg}' does not exist.")
            sys.exit(1)

        # Construct the gdalwarp command to mask the raster
        command = [
            "gdalwarp",
            "-cutline", input_gpkg,
            "-crop_to_cutline",
            "-dstalpha",
            "-of", "GTiff",
            raster_to_mask,
            output_masked_raster
        ]

        # Run the gdalwarp command
        print(f"Running command: {' '.join(command)}")
        subprocess.run(command, check=True)
        print(f"Raster masked and saved to '{output_masked_raster}'.")

    except subprocess.CalledProcessError as e:
        print(f"Error running gdalwarp: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Ensure proper arguments are provided
    if len(sys.argv) != 4:
        print("Usage: python script.py <input_gpkg> <attribute_name> <output_raster>")
        sys.exit(1)

    # Parse command-line arguments
    input_gpkg = sys.argv[1]
    attribute_name = sys.argv[2]
    output_raster = sys.argv[3]
    temp_raster = "temp_interpolated_raster.tif"

    # Interpolate the raster based on the attribute
    interpolate_raster(input_gpkg, temp_raster, attribute_name)

    # Mask the raster using the input GeoPackage file
    mask_raster(input_gpkg, temp_raster, output_raster)

    # Remove the temporary raster
    if os.path.exists(temp_raster):
        os.remove(temp_raster)
