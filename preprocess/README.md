
### Generating Data

You may re-run all the data generation steps, however, note that the time taken to run this workflow end-to-end is majorly dependent on your machine resources.

Ensure that you have data files placed as mentioned here:

 - `data/input/parquet/` Place buildings.parquet and parcel.parquet here
 - `data/input/xyz/` Place only xyz files here for DTM data, sourced from External link

Following is the order of execution to run the scripts:

|Execution Order | File | Input | Output |
|--|--|--|--|
| 1 | [terrainDataSourcer.py](./terrainDataSourcer.py "terrainDataSourcer.py") | .xyz | .parquet |
| 2 | [parquetToGridConverter.py](./parquetToGridConverter.py "parquetToGridConverter.py")| .parquet | grid_resolution_6.gpkg, grid_resolution_8.gpkg |
| 3 | [dbGenerator.py](./dbGenerator.py "dbGenerator.py")| .gpkg | db/{geohash}/ |
| 4 | [DTMRasterInterpolator.py](./DTMRasterInterpolator.py "DTMRasterInterpolator.py")| db/{geohash}/ | db/{geohash}/raster/ |
| 5 | [rasterProcessor.py](./rasterProcessor.py "rasterProcessor.py")| db/{geohash}/raster | interpolated_raster.tif |
| 6 | [terrainLayersExtractor.py](./terrainLayersExtractor.py "terrainLayersExtractor.py")| interpolated_raster.tif | {slope,aspect,tri,tpi,roughness}_raster.tif |
| 7 | [derivedVariablesExtractor.py](./derivedVariablesExtractor.py "derivedVariablesExtractor.py")| grid_resolution_8.gpkg | grid_resolution_8_derived.gpkg |
| 8 | [derivedVariablesInterpolator.py](./derivedVariablesInterpolator.py "derivedVariablesInterpolator.py")| grid_resolution_8_derived.gpkg | SER.tif, Solar_Potential.tif, Terrain_Risk.tif |

