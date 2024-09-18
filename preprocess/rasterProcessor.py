import os
import sys
import subprocess
from osgeo import gdal

class RasterProcessor:
    def __init__(self, input_path, output_path):
        self.input_path = input_path
        self.output_path = output_path

    def merge_rasters(self):
        """
        Merge all raster files in the given input directory using GDAL.
        """
        try:
            # Find all .tif files in the input directory
            raster_files = [os.path.join(self.input_path, file) for file in os.listdir(self.input_path) if file.endswith('.tif')]

            if not raster_files:
                raise Exception("No .tif files found in the specified directory.")

            # Use gdal_merge.py for merging rasters
            merge_command = ["gdal_merge.py", "-o", self.output_path, "-co", "COMPRESS=LZW"] + raster_files
            print(f"Running command: {' '.join(merge_command)}")
            subprocess.run(merge_command, check=True)

            print(f"Successfully merged rasters into {self.output_path}")

        except Exception as e:
            print(f"Error during raster merge: {e}")

    def convert_to_cog(self):
        """
        Convert a single raster file into a Cloud Optimized GeoTIFF (COG) using GDAL.
        """
        try:
            cog_command = [
                "gdal_translate",
                self.input_path,
                self.output_path,
                "-of", "COG",
                "-co", "BIGTIFF=YES"
            ]
            print(f"Running command: {' '.join(cog_command)}")
            subprocess.run(cog_command, check=True)

            print(f"Successfully converted {self.input_path} to COG at {self.output_path}")

        except Exception as e:
            print(f"Error during COG conversion: {e}")

def main():
    if len(sys.argv) < 4:
        print("Usage:")
        print("  python myscript.py merge /path/to/dir output_merged.tif")
        print("  python myscript.py cog /path/to/raster.tif /path/to/cog_raster.tif")
        sys.exit(1)

    command = sys.argv[1]
    input_path = sys.argv[2]
    output_path = sys.argv[3]

    processor = RasterProcessor(input_path, output_path)

    if command == "merge":
        processor.merge_rasters()
    elif command == "cog":
        processor.convert_to_cog()
    else:
        print("Invalid command. Use 'merge' or 'cog'.")

if __name__ == "__main__":
    main()
