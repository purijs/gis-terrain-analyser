import os
from multiprocessing import get_context
from tqdm import tqdm
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from pyproj import CRS

class FileProcessor:
    @staticmethod
    def process_file(file):
        """Process a single xyz file and convert it to GeoParquet format."""
        try:
            base_directory = "data/input/xyz/" 
            file_path = os.path.join(base_directory, file)
            
            # Read the CSV file and process it
            df = pd.read_csv(file_path, sep=" ", header=None, names=["x", "y", "height"])
            df['geometry'] = df.apply(lambda row: Point(row['x'], row['y']), axis=1)

            # Create a GeoDataFrame and set the CRS
            gdf = gpd.GeoDataFrame(df, geometry='geometry')
            gdf.set_crs(CRS.from_epsg(25832), inplace=True)  # ETRS89 / UTM zone 32N
            gdf = gdf.to_crs(CRS.from_epsg(4326))  # WGS84
            gdf.set_crs(CRS.from_epsg(4326), inplace=True, allow_override=True)

            # Output file path
            output_file = os.path.join('data/output/parquet/', file.split('.')[0] + ".parquet")
            
            # Write to GeoParquet
            gdf.to_parquet(output_file, engine="pyarrow")
            return f"{file} processed successfully."
        
        except Exception as e:
            return f"Error processing {file}: {e}"


class ParallelProcessor:
    def __init__(self, base_directory):
        self.base_directory = base_directory

    def get_files(self):
        """Get the list of files to be processed."""
        return [file for file in os.listdir(self.base_directory) if file.endswith('.xyz')]

    def run_parallel(self):
        """Run the file processing in parallel using multiprocessing."""
        files = self.get_files()

        # Use multiprocessing Pool with 'spawn' method
        with get_context("spawn").Pool(processes=os.cpu_count() - 1) as pool:
            # Use tqdm to display progress bar
            results = list(tqdm(pool.imap(FileProcessor.process_file, files), total=len(files)))
        
        return results


if __name__ == "__main__":
    base_directory = "data/input/xyz/"
    processor = ParallelProcessor(base_directory)
    processor.run_parallel()
