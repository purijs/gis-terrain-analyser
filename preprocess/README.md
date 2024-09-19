
### Generating Data

You may re-run all the data generation steps, however, note that the time taken to run this workflow end-to-end is majorly dependent on your machine resources.

Ensure that you have data files placed as mentioned here:

 - `data/input/parquet/` Place buildings.parquet and parcel.parquet here
 - `data/input/xyz/` Place only xyz files here for DTM data, sourced from External link

Following is the order of execution to run the scripts:

|Execution Order | File | Input | Output |
|--|--|--|--|
| 1 | [terrainDataSourcer.py](https://github.com/purijs/terrain-mapper/blob/main/preprocess/terrainDataSourcer.py "terrainDataSourcer.py") | .xyz | .parquet |
| 2 | [parquetToGridConverter.py](https://github.com/purijs/terrain-mapper/blob/main/preprocess/parquetToGridConverter.py "parquetToGridConverter.py")| .parquet | grid_resolution_6.gpkg, grid_resolution_8.gpkg |
| 3 | [dbGenerator.py](https://github.com/purijs/terrain-mapper/blob/main/preprocess/dbGenerator.py "dbGenerator.py")| .gpkg | db/{geohash}/ |
| 4 | [DTMRasterInterpolator.py](https://github.com/purijs/terrain-mapper/blob/main/preprocess/DTMRasterInterpolator.py "DTMRasterInterpolator.py")| db/{geohash}/ | db/{geohash}/raster/ |
| 5 | [rasterProcessor.py](https://github.com/purijs/terrain-mapper/blob/main/preprocess/rasterProcessor.py "rasterProcessor.py")| db/{geohash}/raster | interpolated_raster.tif |
| 6 | [terrainLayersExtractor.py](https://github.com/purijs/terrain-mapper/blob/main/preprocess/terrainLayersExtractor.py "terrainLayersExtractor.py")| interpolated_raster.tif | {slope,aspect,tri,tpi,roughness}_raster.tif |
| 7 | [derivedVariablesExtractor.py](https://github.com/purijs/terrain-mapper/blob/main/preprocess/derivedVariablesExtractor.py "derivedVariablesExtractor.py")| grid_resolution_8.gpkg | grid_resolution_8_derived.gpkg |
| 8 | [derivedVariablesInterpolator.py](https://github.com/purijs/terrain-mapper/blob/main/preprocess/derivedVariablesInterpolator.py "derivedVariablesInterpolator.py")| grid_resolution_8_derived.gpkg | SER.tif, Solar_Potential.tif, Terrain_Risk.tif |

