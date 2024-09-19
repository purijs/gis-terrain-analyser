The project is built on majorly three sources of original data inputs and one external _soil data source_:
1. buildings.parquet
2. parcels.parquet
3. Digital Terrain Data from [German State Gov.](bw.de/#/%28sidenav:product/3%29)

**Soil Data**

To estimate soil erosion risk that could be potentially useful for terrain risk analysis, following soil property rasters were acquired
`pH, Soil Organic Carbon, Bulk Density, clay, sand`

---

The CRS of the provided parquet file was observed to be in [EPSG:25832 - ETRS89 / UTM zone 32N](https://epsg.io/25832) projection and was converted to something more standard `EPSG:4326`

The DTM data extracted was divided by tile grids, while the usable data was in files with `.xyz` extension, also re-projected to `EPSG:4326`

---
This table provides a high-level summary for different stages of processing the files undergo to generate analytical layers from the input data

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

---

### Data Flow Architecture

This diagram depicts the high-level working of different scripts for preparing the data

![](https://github.com/purijs/terrain-mapper/blob/main/images/credium.drawio.png)

### Workflow Highlights

The data preparation steps are broken into multiple files so as to scale each component independently, this section provides more conceptual detail for each step considering data engineering best practices

The nature of this project makes it a `OLAP` heavy workload rather than a `OLTP`, this understanding can help us choose the relevant tools and ensure a relevant system design. As a first, we would like to extract insights at scale (Country level or continent level) and not really perform any real-time transactions. The real-time querying is however a secondary objective where users would like to interact with the derived results in real-time.

**Data Normalisation (xyz To Parquet)**

Before any kind of analysis is performed, it is ideal to have multiple data sources converged into a cost-efficient and scalable format. Spatial data have particularly this problem where each `coordinate` is a `float` value, this becomes potentially costly in terms of cost and performance when we talk about complex `Polygons` or a lot of **simple Polygons**.
´üp
`Parquet` supports complex data types, is columnar (`OLAP` friendly) making it an ideal format to store any `on-disk` data. As a result, all input `xyz` files are converted into `Parquet` or rather `GeoParquet` because it stores the spatial attributes as well.

**Interpolation of DTM**

While it is possible to use the original DTM points for any spatial analysis, however, this method of inferring DTM especially to analyse how terrain features change is not ideal as terrain can not be quantified as distinct number but is rasther a continupus change over a spatial area. For instance, if there is an elevation, earth's terrain isn't distinct that we suddenly see a Mountain rather what we have is gradual increase in elevation that leads to the mountain.

To incorporate this concept that terrains are best represented by continuous numbers, it makes sense to first interpolate these points into something more of a gradient of values. This comes at a cost however, where we previously had a single `Point` with a constant number for region of area, we would now have to represent each region on land with a `float` number, significantly more points/pixels to store.

In a constrained environment of computed resources, it is hard to automate and scale this interpolation and this is what leads us to first design a efficient Database or storage schema so we can instead scale our interpolation logic and make it work in limited amount of `memory/CPU`. 

**Hive Like Spatial DB**

We'd want to perform OLAP based processing (interpolation in this case) on our parquet files. For this project's extent we're talking around `220 Million DTM Points` to interpolate. 

To have such a system running, especially locally and/or cheaply, needs a step away from traditional storage engines. `PostgreSQL` is of course the last choice once can make, but we can ask a question `Do I need a Database?`. To cut it short, in this case not necessarily. We want a system design that can perform interpolation at scale but we should be able to control the cost of the scaling factor.

For example, this means that the `220 Million DTM Points` that are roughly the size of `5GB` in `parquet` format need a resources that has at least twice the memory to be hold the data and results at the same time. Answer is, `spatial indexes`, or to be specific [GeoHashes](https://www.movable-type.co.uk/scripts/geohash.html). You can imagine this as a QR-code for any piece of land on Earth, identified by an `alphanumeric` string

In this project, it was founder cheaper and faster to partition the `220 Million DTM Points, buildings and parcels` to be partitioned and grouped by a GeoHash string of precision 6 `(1.2 km x 0.6 km)`. This design made the following two things easier, faster and cheaper (less resources):

1. Faster user querying simulating a DB because data is already partitioned and each partition is insignificant
2. Interpolation can be limited to the bounds of the GeoHash, cheaper on the memory use

This structure was produced dynamically using `dask-geopandas` which can scale across CPUs. 

The final structure is something like this:

```
    /db/
      ├── u4pruyd/
      │   ├── buildings.parquet
      │   └── parcels.parquet
      │   └── dtm.parquet
      │   └── rasters/interpolation.tif (interpolated DTM heights as raster by grid)
      ├── u4pruyf/
      │   ├── buildings.parquet
      │   └── parcels.parquet
      │   └── dtm.parquet
      │   └── rasters/interpolation.tif
      └── ...
```

**Generating Layers from Interpolation**

Once we have merged all the interpolation rasters into a single layer (not important though) we can use `gdaldem` to extract the following layers from it:

* Slope: This represents the steepness or gradient of the terrain at a specific pixel
* Aspect: The compass direction that a slope faces. `0° = North 90° = East 180° = South 270° = West`
* TRI: Terrain Ruggedness Index quantifies the amount of elevation difference between adjacent pixels
* TPI: Topographic Position Index compares the elevation of a pixel to the mean elevation of its surrounding pixels
* Roughness: Roughness is the measure of the variation in elevation within a neighborhood around a pixel. It indicates how much the surface varies vertically

### Deriving Custom Layers

To further perform feature engineering for example as something that can be used for Machine Learning purposes, following features were derived at the GeoHash level at resolution 8.

**1. Soil Erosion Risk (SER) Calculation**

Soil Erosion Risk (SER) is calculated by considering both **terrain factors** (e.g., slope) and **soil properties** (e.g., clay content, sand content, soil organic carbon). A higher SER score indicates a higher risk of soil erosion.

_Terrain Factors:_
- **Slope**: Steeper slopes increase soil erosion as water moves faster and carries soil away.
- **TPI (Topographic Position Index)**: Higher TPI values (ridges) reduce erosion risk as water runs off rather than accumulates.
- **TRI (Terrain Ruggedness Index)**: Rugged terrain increases erosion risk due to greater surface exposure.

_Soil Factors:_
- **Clay Content** (`clay.tif`): Higher clay content **reduces** erosion risk by stabilizing soil and improving water retention.
- **Sand Content** (`sand.tif`): Higher sand content **increases** erosion risk, as sandy soils are less cohesive and more prone to being washed away.
- **Soil Organic Carbon (SOC)** (`soc.tif`): Higher SOC content **reduces** erosion risk by improving soil structure and water retention.
- **pH Level** (`ph.tif`): Extremes in pH (either very high or very low) can affect plant growth and indirectly increase erosion risk. However, its impact on erosion is generally **neutral**.
- **Bulk Density (BD)** (`BD.tif`): Higher bulk density (compacted soil) **increases** erosion risk by reducing water infiltration and increasing runoff.

_SER Calculation Process:_
1. **Terrain Contribution**: The terrain factors (e.g., slope, TPI, TRI) are processed first using raster data to determine their contribution to erosion risk.
2. **Soil Contribution**: Soil factors are processed next, and the impact of these factors is adjusted based on their positive or negative effect on erosion.
3. **Slope Amplification**: The slope factor amplifies the effect of soil properties on erosion, meaning that steeper slopes will lead to a higher SER score.
4. The final SER score is a weighted sum of these factors, with higher values indicating a higher erosion risk.

**2. Solar Energy Potential Calculation**

The solar energy potential for each geohash is determined by calculating the **angle of incidence** of sunlight on the surface based on the terrain's slope and aspect.

_Solar Energy Calculation Process:_
1. **Slope and Aspect**: The terrain's slope and aspect are used to calculate how directly sunlight hits the surface.
2. **Angle of Incidence**: The function `calculate_angle_of_incidence` computes the angle between the sun's rays and the terrain surface based on the solar altitude and azimuth.
3. **Solar Potential**: The solar potential is calculated as the cosine of the angle of incidence, determining how much sunlight directly strikes the surface. Higher cosine values mean higher solar potential.

The solar energy potential is stored in the `solar` column for each geohash, representing the available solar energy in that area.

**3. Terrain Risk Calculation**

The **Terrain Risk Map** is created by combining SER, solar potential, and additional terrain factors such as slope, TPI, and TRI.

_Weights for Terrain Risk:_
- **Slope**: 15% weight
- **TPI**: 25% weight (higher TPI reduces risk)
- **TRI**: 25% weight (higher TRI increases risk)
- **SER**: 35% weight (direct contribution from soil erosion risk)

_Terrain Risk Calculation Process:_
1. The **SER** is incorporated with a positive impact, meaning higher SER values increase terrain risk.
2. Each **terrain factor** (e.g., slope, TPI, TRI) is processed based on its contribution to terrain risk. Slope and TRI increase risk, while TPI reduces it.
3. The terrain risk score is the weighted sum of these factors, providing a comprehensive risk assessment for each geohash.

---

## Raster and Vector Rendering

**COG For Rasters:**

- **Tiled Structure**: COGs are internally organized into tiles, making it possible to fetch only the required portions of the raster data, rather than downloading the entire file.
- **Overviews**: COGs can include multiple resolutions (overviews) of the raster, allowing access to lower-resolution data quickly when zoomed out, and higher resolution when zoomed in.
- **HTTP Range Requests**: COGs leverage HTTP range requests, allowing to request specific parts of the file without downloading everything
- **Cloud Friendly**: COGs are natively designed for cloud-based environments, making them efficient for retrieval from object storage

In this application, COG files are used to render raster layers such as **slope**, **aspect**, **terrain risk**, and **solar potential**

**Tippecanoe and Vector Tile Rendering**

For rendering vector data (like building footprints or parcel boundaries), **Tippecanoe** to generate **MBTiles** was used. Tippecanoe is a tool for converting large GeoJSON/GPKG into vector tilesets that can be rendered by web maps.

_What is MBTiles?_

**MBTiles** is a format for storing map tiles (both raster and vector) in a single SQLite database. It allows for efficient storage and retrieval of pre-rendered map tiles.

_How MBTiles Works:_

- **Tiles**: Map tiles are small images or data chunks representing a small section of the map at a given zoom level.
- **Zoom Levels**: MBTiles organizes the data into different zoom levels. At higher zoom levels, more detailed tiles are available; at lower zoom levels, fewer tiles cover larger areas.

_Tippecanoe and PBF (Protocolbuffer Binary Format)_

Tippecanoe converts vector data into vector tiles stored in the **PBF (Protocolbuffer Binary Format)**, which is a highly efficient binary format used for transmitting data over the web. PBF reduces the size of the vector tile data, making it faster to send and render in web applications.

