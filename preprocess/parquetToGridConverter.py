import dask_geopandas as dgpd
from dask.distributed import Client, LocalCluster
import geopandas as gpd
import pandas as pd
import pygeohash as pgh
from shapely.geometry import Polygon
from dask.diagnostics import ProgressBar
import os, gc

cluster = LocalCluster(n_workers=os.cpu_count()-1, memory_limit='8GB')
client = Client(cluster)
gc.collect()

class GeohashProcessor:
    def __init__(self, parquet_path, resolution, partition_size="75MB"):
        self.parquet_path = parquet_path
        self.partition_size = partition_size
        self.resolution = resolution

    def geohash_to_polygon(self, geohash):
        """
        Convert a geohash string to a polygon representing the bounding box.
        """
        lat, lon, lat_err, lon_err = pgh.decode_exactly(geohash)
        min_lon = lon - lon_err
        max_lon = lon + lon_err
        min_lat = lat - lat_err
        max_lat = lat + lat_err
        return Polygon([
            (min_lon, min_lat),
            (min_lon, max_lat),
            (max_lon, max_lat),
            (max_lon, min_lat),
            (min_lon, min_lat)
        ])

    def add_geohash(self, df):
        """
        Adds geohash to each Point geometry in the DataFrame.
        Returns the aggregated result with mean height for each geohash.
        """
        points_df = df[df.geometry.type == "Point"].copy()
        if points_df.empty:
            return pd.DataFrame(columns=["geohash_string", "height", "geometry"])

        # Add geohash for each point geometry
        points_df['geohash_string'] = points_df.geometry.apply(lambda geom: pgh.encode(geom.y, geom.x, precision=self.resolution))

        # Group by geohash and calculate mean DTM height
        result = points_df.groupby('geohash_string').agg({'height': 'mean'}).reset_index()

        # Add geometry (polygon) for each geohash
        result['geometry'] = result['geohash_string'].apply(self.geohash_to_polygon)

        return result

    def load_and_repartition_data(self):
        """
        Load the parquet files as a Dask Geopandas DataFrame and repartition it.
        """
        dask_gdf = dgpd.read_parquet(self.parquet_path)
        print(f"Number of partitions before repartition: {dask_gdf.npartitions}")
        dask_gdf = dask_gdf.repartition(partition_size=self.partition_size)
        print(f"Number of partitions after repartition: {dask_gdf.npartitions}")
        return dask_gdf

    def process_partitions(self, dask_gdf):
        """
        Process the partitions of the Dask Geopandas DataFrame and compute the final result.
        """
        # Define metadata (meta) for Dask
        meta = pd.DataFrame({
            'geohash_string': pd.Series(dtype='str'),
            'height': pd.Series(dtype='float'),
            'geometry': pd.Series(dtype='object')  # Use 'object' for geometry as it's complex
        })

        # Apply the add_geohash function to each partition
        aggregated_result = dask_gdf.map_partitions(self.add_geohash, meta=meta)

        with ProgressBar():
            final_result = aggregated_result.compute()

        return gpd.GeoDataFrame(final_result, geometry='geometry', crs="EPSG:4326")

    def save_result(self, gdf, output_path):
        """
        Save the result as a GeoPackage.
        """
        gdf.to_file(output_path, driver='GPKG')
        print(f"Result saved to {output_path}")


if __name__ == "__main__":

    '''
    Run this script twice, with precision 6 and 8 as outputs
    
    data/output/gpkg/geohash_resolution_6.gpkg
    data/output/gpkg/geohash_resolution_8.gpkg
    
    '''
    
    parquet_path = "data/output/parquet/*.parquet"
    output_path = "data/output/gpkg/.gpkg"

    resolution = 

    processor = GeohashProcessor(parquet_path, resolution)
    dask_gdf = processor.load_and_repartition_data()
    aggregated_gdf = processor.process_partitions(dask_gdf)
    processor.save_result(aggregated_gdf, output_path)
