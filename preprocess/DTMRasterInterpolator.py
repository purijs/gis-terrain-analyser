import os
import subprocess
import geopandas as gpd
from pyproj import CRS
import tqdm
from multiprocessing import Pool, cpu_count

class RasterGenerator:
    def __init__(self, input_file, output_base_dir, outsize=(130, 90)):
        self.input_file = input_file
        self.output_base_dir = output_base_dir
        self.outsize = outsize
        self.bounds = self.get_bounds()

        # Get filename without extension
        self.filename = os.path.splitext(os.path.basename(input_file))[0]
        self.gpkg_file = os.path.join(self.output_base_dir, f"{self.filename}.gpkg")  # GPKG file

        # Ensure output directory exists
        os.makedirs(self.output_base_dir, exist_ok=True)

    def get_bounds(self):
        """Extract bounds from the GeoParquet file"""
        gdf = gpd.read_parquet(self.input_file)
        bounds = gdf.total_bounds  # Returns (minx, miny, maxx, maxy)
        return bounds

    def convert_parquet_to_gpkg(self):
        """Convert the input Parquet file to GeoPackage."""
        if os.path.exists(self.gpkg_file):
            os.remove(self.gpkg_file)  # Remove existing GPKG file
        gdf = gpd.read_parquet(self.input_file)
        gdf.to_file(self.gpkg_file, driver="GPKG", layer=self.filename)

    def run_gdal_command(self, command):
        """Run a GDAL command using subprocess"""
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode != 0:
            raise Exception(f"GDAL command failed: {result.stderr.decode('utf-8')}")

    def generate_slope_raster(self):
        """Generate the slope raster using gdal_grid"""
        self.convert_parquet_to_gpkg()  # Convert Parquet to GPKG

        output_raster = os.path.join(self.output_base_dir, f"{self.filename}_slope.tif")
        command = [
            "gdal_grid",
            "-zfield", "height",
            "-a", "invdist:power=2.0",
            "-txe", str(self.bounds[0]), str(self.bounds[2]),
            "-tye", str(self.bounds[1]), str(self.bounds[3]),
            "-outsize", str(self.outsize[0]), str(self.outsize[1]),
            "-of", "GTiff",
            "-co", "COMPRESS=LZW",
            "--config", "GDAL_NUM_THREADS", "ALL_CPUS",
            self.gpkg_file, output_raster
        ]
        self.run_gdal_command(command)
        return output_raster

    def generate_analysis_raster(self, raster_type):
        """Generate analysis rasters (aspect, TRI, TPI, roughness)"""
        input_raster = os.path.join(self.output_base_dir, f"{self.filename}_slope.tif")
        output_raster = os.path.join(self.output_base_dir, f"{self.filename}_{raster_type}.tif")
        command = [
            "gdaldem", raster_type, input_raster, output_raster,
            "-co", "COMPRESS=LZW"
        ]
        self.run_gdal_command(command)
        return output_raster

    def reproject_raster(self, input_raster, output_raster):
        """Reproject a raster to EPSG:4326"""
        command = [
            "gdalwarp", "-t_srs", "EPSG:4326", "-r", "bilinear",
            "-co", "COMPRESS=LZW", "--config", "GDAL_NUM_THREADS", "ALL_CPUS",
            input_raster, output_raster
        ]
        self.run_gdal_command(command)

    def cleanup_files(self, *files):
        """Delete raw GeoTIFF files or other temporary files after processing"""
        for file in files:
            if os.path.exists(file):
                os.remove(file)

    def process_parquet(self):
        """Run the entire pipeline on the given parquet file"""
        # Step 1: Generate the slope raster
        slope_raster = self.generate_slope_raster()

        # Step 2: Generate analysis rasters
        aspect_raster = self.generate_analysis_raster("aspect")

        # Step 3: Reproject rasters to EPSG:4326
        reprojected_slope = os.path.join(self.output_base_dir, f"{self.filename}_slope_4326.tif")

        self.reproject_raster(slope_raster, reprojected_slope)

        # Step 4: Cleanup raw GeoTIFFs and GPKG
        self.cleanup_files(slope_raster, aspect_raster, tri_raster, tpi_raster, roughness_raster, self.gpkg_file)

class ParquetProcessor:
    def __init__(self, input_base_dir, output_base_dir):
        self.input_base_dir = input_base_dir
        self.output_base_dir = output_base_dir

    def process_parquet_file(self, args):
        """Helper function for multiprocessing"""
        input_file, relative_path = args
        output_dir = os.path.join(self.output_base_dir, relative_path, "rasters")

        # Instantiate RasterGenerator and process the file
        raster_generator = RasterGenerator(input_file, output_dir)
        raster_generator.process_parquet()

    def process_all_parquets(self):
        """Process all 'dtm.parquet' files in the directory structure using multiprocessing"""
        tasks = []
        for root, dirs, files in os.walk(self.input_base_dir):
            for file in files:
                if file == "dtm.parquet":  # Only process dtm.parquet files
                    input_file = os.path.join(root, file)
                    relative_path = os.path.relpath(root, self.input_base_dir)
                    tasks.append((input_file, relative_path))

        # Use multiprocessing to parallelize the work
        with Pool(processes=cpu_count()) as pool:
            list(tqdm.tqdm(pool.imap(self.process_parquet_file, tasks), total=len(tasks)))

if __name__ == "__main__":
    
    # Base directories for input parquet files and output results
    # The rasters subdirectory under "data/output/db/{geohash}/rasters/" is populated with interpolation of DTM heights
    base_dir = "data/output/db/"

    # Create the processor and process all parquets in parallel
    processor = ParquetProcessor(base_dir, base_dir)
    processor.process_all_parquets()
