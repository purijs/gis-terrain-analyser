import os
import tqdm
import geopandas as gpd
import pandas as pd
import multiprocessing
from shapely.geometry import box


class GeohashPartitioner:
    def __init__(self, geohash_grid_file, dtm_parquet_files, buildings_parquet_files, parcels_parquet_files, output_base_dir, num_workers=4):
        """
        Initialize the GeohashPartitioner with the required parameters.
        """
        self.geohash_grid_file = geohash_grid_file
        self.dtm_parquet_files = dtm_parquet_files
        self.buildings_parquet_files = buildings_parquet_files
        self.parcels_parquet_files = parcels_parquet_files
        self.output_base_dir = output_base_dir
        self.num_workers = num_workers

    @staticmethod
    def create_folder_structure(output_base_dir, geohash):
        """
        Create folder structure for storing results for each geohash.
        """
        geohash_folder = os.path.join(output_base_dir, geohash)
        os.makedirs(geohash_folder, exist_ok=True)
        raster_folder = os.path.join(geohash_folder, 'rasters')
        os.makedirs(raster_folder, exist_ok=True)
        return geohash_folder

    @staticmethod
    def get_parquet_file_bounds(parquet_file):
        """
        Get the bounding box (minx, miny, maxx, maxy) of a GeoParquet file.
        """
        gdf = gpd.read_parquet(parquet_file)
        return gdf.total_bounds  # Returns (minx, miny, maxx, maxy)

    @staticmethod
    def clip_and_save_geoparquet(gdfs, geohash_geom, output_file):
        """
        Clip and save the combined GeoDataFrames to a GeoParquet file.
        """
        # Concatenate all the GeoDataFrames before clipping
        combined_gdf = gpd.GeoDataFrame(pd.concat(gdfs, ignore_index=True))
        
        # Clip the combined GeoDataFrame
        clipped_gdf = combined_gdf[combined_gdf.intersects(geohash_geom)]
        
        if not clipped_gdf.empty:
            clipped_gdf.to_parquet(output_file)

    def process_geohash_grid(self, geohash_row, dtm_parquet_bounds, buildings_parquet_bounds, parcels_parquet_bounds):
        """
        Process and save clipped data for each geohash.
        """
        geohash_string = geohash_row['geohash_string']
        geohash_geom = geohash_row['geometry']

        # Step 1: Create folder structure for the current geohash
        geohash_folder = self.create_folder_structure(self.output_base_dir, geohash_string)

        # Step 2: Accumulate and save DTM data for this geohash
        self._process_data_for_geohash(geohash_geom, dtm_parquet_bounds, geohash_folder, "dtm.parquet")

        # Step 3: Accumulate and save Buildings data for this geohash
        self._process_data_for_geohash(geohash_geom, buildings_parquet_bounds, geohash_folder, "buildings.parquet")

        # Step 4: Accumulate and save Parcels data for this geohash
        self._process_data_for_geohash(geohash_geom, parcels_parquet_bounds, geohash_folder, "parcel.parquet")

        return f"Processed {geohash_string}"

    def _process_data_for_geohash(self, geohash_geom, parquet_bounds, geohash_folder, output_filename):
        """
        Helper function to process data for a specific geohash and save the output.
        """
        gdfs = []
        for parquet_file, bounds in parquet_bounds.items():
            if geohash_geom.intersects(box(*bounds)):
                gdf = gpd.read_parquet(parquet_file)
                gdfs.append(gdf)

        if gdfs:
            output_file = os.path.join(geohash_folder, output_filename)
            self.clip_and_save_geoparquet(gdfs, geohash_geom, output_file)

    def worker_process(self, args):
        """
        Wrapper function for multiprocessing workers.
        """
        geohash_row, dtm_parquet_bounds, buildings_parquet_bounds, parcels_parquet_bounds = args
        try:
            return self.process_geohash_grid(geohash_row, dtm_parquet_bounds, buildings_parquet_bounds, parcels_parquet_bounds)
        except Exception as e:
            return f"Failed {geohash_row['geohash_string']}: {e}"

    def partition_data(self):
        """
        Main function to partition spatial data by geohash using multiprocessing.
        """
        # Step 1: Load geohash grid from the provided GeoPackage file
        geohash_grid = gpd.read_file(self.geohash_grid_file)
        print('Read Geohash Grid')

        # Step 2: Calculate bounds of each parquet file
        dtm_parquet_bounds = self._calculate_bounds(self.dtm_parquet_files)
        buildings_parquet_bounds = self._calculate_bounds(self.buildings_parquet_files)
        parcels_parquet_bounds = self._calculate_bounds(self.parcels_parquet_files)
        print('Calculated Parquet File Bounds')

        # Step 3: Create tasks for multiprocessing
        tasks = [
            (geohash_row, dtm_parquet_bounds, buildings_parquet_bounds, parcels_parquet_bounds)
            for _, geohash_row in geohash_grid.iterrows()
        ]

        # Step 4: Process geohashes using parallel workers with a multiprocessing pool
        with multiprocessing.Pool(processes=self.num_workers) as pool:
            for _ in tqdm.tqdm(pool.imap_unordered(self.worker_process, tasks), total=len(tasks)):
                pass  # Progress bar will update with each completed task

        print("Processing complete!")

    def _calculate_bounds(self, parquet_files):
        """
        Helper function to calculate the bounding boxes of parquet files.
        """
        return {file: self.get_parquet_file_bounds(file) for file in tqdm.tqdm(parquet_files)}


if __name__ == "__main__":

    # Ideally, Output from parquetToGridConverter.py -> 'data/output/gpkg/geohash_resolution_6.gpkg'
    geohash_grid_file = 'data/output/gpkg/geohash_resolution_6.gpkg' # Geohash grid file of lower resolution, 6

    # Input parquet files
    dtm_parquet_files = [os.path.join('data/output/parquet/', file) for file in os.listdir('data/output/parquet/')]
    
    buildings_parquet_files = ['data/input/parquet/buildings.parquet']
    parcels_parquet_files = ['data/input/parquet/parcels.parquet']
    
    # Output base directory
    output_base_dir = 'data/output/db/'
    
    # Create an instance of the GeohashPartitioner class and run the partitioning process
    partitioner = GeohashPartitioner(
        geohash_grid_file=geohash_grid_file,
        dtm_parquet_files=dtm_parquet_files,
        buildings_parquet_files=buildings_parquet_files,
        parcels_parquet_files=parcels_parquet_files,
        output_base_dir=output_base_dir,
        num_workers=os.cpu_count()-1
    )
    
    # Run the partitioning process
    partitioner.partition_data()
