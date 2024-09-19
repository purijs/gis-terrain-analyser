# Terrain Mapper

<p align="center">
  <img width="600" src="https://user-images.githubusercontent.com/your-username/screenshot.png" alt="Terrain Mapper Screenshot"/>
  <p align="center">A FastAPI application for terrain mapping and analysis</p>
</p>

<p align="center">
  <a href="https://github.com/purijs/terrain-mapper/actions?query=workflow%3ACI" target="_blank">
      <img src="https://github.com/purijs/terrain-mapper/workflows/CI/badge.svg" alt="CI Status">
  </a>
  <a href="https://codecov.io/gh/purijs/terrain-mapper" target="_blank">
      <img src="https://codecov.io/gh/purijs/terrain-mapper/branch/main/graph/badge.svg" alt="Coverage">
  </a>
  <a href="https://hub.docker.com/r/purijs/terrain-mapper" target="_blank">
      <img src="https://img.shields.io/docker/v/purijs/terrain-mapper?color=%2334D058&label=docker%20hub" alt="Docker">
  </a>
</p>

---

**Live Application**: [Terrain Mapper](https://3.124.67.243:8081)

**Documentation**: [Swagger API Documentation](https://3.124.67.243:8080/docs)

**Infrastructure Dashboard**: [Infra Dashboard](https://3.124.67.243:8080/infra)

---

## Overview

`Terrain Mapper` is PoC application that uses a combination of Digital Terrain Data ([source](https://opengeodata.lgl-bw.de/#/(sidenav:product/3))) and building footprints for 3 cities in Germany. The terrain data is interpolated as raster and different analytical layers are dervied from the interpolation. User can visually make interpretations, interact with app to get insights for specific footprints and developers can use API endpoints to extract data for machine learning purposes. The application runs in Docker Swarm environment, with 5 services to simulate a scalable workload.

## Features

- **Interactive Terrain Mapping**: Visualize raster layers and vector footprints with Mapbox Maps UI
- **Zonal and Neighborhood Analysis**: Split building footprints into directional zones (North, South, East, West) and assess surrounding terrain variations.
- **Dynamic Raster and Vector Layers**: Display map layers over each other for better inference
- **Real-time Logging**: Monitor application performance and logs using Dozzle
- **Infrastructure**: Built with Docker and FastAPI, hosted on a single EC2 instance
- **API Integration**: Enable interaction with backend through a Swagger API

## Technologies Used

### Docker Services

- **Dozzle**
  - **Description**: A lightweight real-time log viewer for Docker containers.
  - **Usage**: Monitors and displays logs from all running services, facilitating easier debugging and monitoring
  - **Resources**:
    - CPUs: 0.25
    - Memory: 1G
  - **Ports**: `9200:9200`

- **Frontend**
  - **Description**: The user interface of the application
  - **Usage**: User can render layers or draw polygons for interaciton on the map
  - **Resources**:
    - CPUs: 0.25
    - Memory: 1G
  - **Ports**: `8081:80`

- **Backend**
  - **Description**: Backend service handling data processing and API endpoints.
  - **Usage**: Manages terrain data processing, zonal and neighborhood analyses, and serves API requests
  - **Resources**:
    - CPUs: 1
    - Memory: 2G
  - **Ports**: `8080:8080`

- **Raster Titiler**
  - **Description**: A dynamic tile server for raster data rendering
  - **Usage**: Processes and serves raster layers through Titiler.
  - **Resources**:
    - CPUs: 1
    - Memory: 1G
  - **Ports**: `8000:8000`

- **Vector TileServer**
  - **Description**: Serves vector tiles for dynamic map rendering
  - **Usage**: Renders vector layers from MBTiles using Protocolbuffer Binary Format (PBF)
  - **Resources**:
    - CPUs: 1
    - Memory: 1G
  - **Ports**: `9100:9100`

### Application Components

- **Swagger API**: [Access the Swagger API Documentation](https://3.124.67.243:8080/docs)
  - Provides a detailed overview of all available endpoints, request/response schemas, and interactive testing UI

- **Infra Dashboard**: [View the Infrastructure Dashboard](https://3.124.67.243:8080/infra)
  - Provides breif monitoring of all docker services. Python logging is also enabled for the backend service to observe how a request propogates through various functions

### Geospatial Data Handling

#### Raster Layers

- **Integration with FastAPI**: FastAPI handles API requests for raster data, performing min-max scaling to normalize terrain attributes
- **Titiler Rendering**: Raster data in form of Cloud Optimised Tif (COG) is rendered dynamically using Titiler, data is returned in the form of ...

#### Vector Layers

- **TileServer Integration**: Vector layers are served as MBTiles (Mapbox Format) using a vector tile server, which leverages PBF for optimized data transmission
- **Dynamic Rendering**: Allows for smooth and interactive rendering of vector data on the frontend, enhancing the user experience

## Backend Structure

### GeoApp

- **Description**: Initializes the FastAPI application, configures middleware, services, and routes
- **Responsibilities**:
  - Sets up CORS policies.
  - Integrates various services such as RasterService, GeohashService, and BuildingService
  - Defines API endpoints for raster statistics, health checks, and building insights

### Services

- **ReportCleaner**
  - **Description**: Cleans report data by removing NaN and infinite values
  - **Responsibilities**:
    - Ensures data integrity before it's sent to the frontend
  
- **BuildingService**
  - **Description**: Handles the core logic for processing building footprints and generating reports
  - **Responsibilities**:
    - Splits building geometries into zonal and neighborhood variations
    - Retrieves and processes raster statistics for each zone
    - Performs multiprocessing for faster processing

- **ReportService**
  - **Description**: Generates textual reports based on raster and terrain data
  - **Responsibilities**:
    - Interprets slope, aspect, and solar potential data
    - Constructs human-readable descriptions for zonal and neighborhood analyses

- **InterpretationService**
  - **Description**: Interprets raw terrain data into meaningful descriptions
  - **Responsibilities**:
    - Categorizes slope values (gentle, moderate, steep)
    - Determines aspect directions (north, south, east, west)
    - Assesses solar potential levels based on min-max values

- **GeohashService**
  - **Description**: Manages geohash encoding and spatial indexing
  - **Responsibilities**:
    - Generates geohash grids of resolution 6 covering input polygon

- **RasterService**
  - **Description**: Handles raster data processing and statistics retrieval
  - **Responsibilities**:
    - Clips raster files based on GeoJSON geometries
    - Calculates minimum and maximum values within clipped areas

### Pydantic Models

- **GeoClipRequest**
  - **Description**: Defines the structure for raster clipping requests
  - **Fields**:
    - `geojson`: GeoJSON feature collection defining the clipping geometry
    - `tif_url`: URL to the target raster file.

- **GeoInsights**
  - **Description**: Represents the structure for generating building insights
  - **Fields**:
    - `geojson`: GeoJSON feature collection for analysis

- **HealthResponse**
  - **Description**: Provides a simple health status response
  - **Fields**:
    - `status`: Health status string

- **RasterStatsResponse**
  - **Description**: Returns statistical data for raster files
  - **Fields**:
    - `min`: Minimum raster value
    - `max`: Maximum raster value

- **StatsResponse**
  - **Description**: Aggregates building reports
  - **Fields**:
    - `building_reports`: List of `BuildingReport` objects

- **BuildingReport**
  - **Description**: Contains detailed reports for individual buildings
  - **Fields**:
    - `building_id`: Identifier for the building
    - `zonal_variation`: Raster statistics for each zone
    - `zonal_variation_text`: Textual description of zonal variation
    - `neighborhood_understanding`: Raster statistics for neighborhood zones
    - `neighborhood_understanding_text`: Textual description of neighborhood analysis

## Acknowledgments

- Utilizes technologies like FastAPI, Rasterio, GeoPandas, TiTiler, Dask-GeoPandas and Docker for spatial data processing and visualization

---

## Database

Terrain Mapper utilizes a **file-based spatial partitioning system** inspired by Hive's partitioning strategy, enhanced with spatial indexing through [PyGeohash](https://pypi.org/project/pygeohash/). This approach enables efficient data storage and rapid query responses without the overhead of managing a traditional database system.

### **Structure and Organization**

- **Spatial Partitioning with Geohash:**
  - The entire dataset is partitioned based on the footprint locations using Geohash at **resolution 6**. Each Geohash string at this resolution represents an area approximately 1.2 kilometers by 0.6 kilometers, balancing granularity and performance.
  
- **Directory-Based Storage:**
  - The database is organized into a hierarchical folder structure where each top-level folder corresponds to a unique Geohash identifier.
  - **Files Within Each Geohash Folder:**
    - `buildings.parquet`: Contains building footprint data within the Geohash area.
    - `parcels.parquet`: Contains parcel boundary data within the Geohash area.
    - `rasters`: (Futuristic) Raster can also be divided by these partitions, however, wasn't implemented in this PoC
  
### **Query Handling**

When a user submits a polygon query through the API endpoint, the system performs the following steps to retrieve relevant data:

1. **Geohash Calculation:**
   - The input polygon's bounding box is analyzed to determine all overlapping Geohash partitions at **resolution 6** using the `GeohashService` class.
   
2. **Partition Identification:**
   - Based on the calculated Geohashes, the system identifies the corresponding folders within the `/db/` directory.
   
3. **Data Retrieval:**
   - The `BuildingService` class accesses the relevant `buildings.parquet` and `parcels.parquet` files from the identified Geohash partitions.
   - Utilizing GeoPandas, the service performs spatial joins to filter and retrieve only those records that intersect with the input polygon.
   
4. **Multiprocessing for Scalability:**
   - To handle multiple Geohash partitions concurrently, the `BuildingService` employs Python's `multiprocessing` module. This parallel processing significantly reduces query response times, especially for large and complex polygons spanning numerous partitions.

### **Advantages of the Spatial File-Based Database**

- **Performance and Speed:**
  - **Efficient Data Access:** Spatial partitioning ensures that only relevant data partitions are accessed during a query, minimizing I/O operations.
  - **Parallel Processing:** Leveraging multiprocessing allows for simultaneous data retrieval from multiple partitions, significantly reducing query times.

- **Scalability:**
  - **No Database Overhead:** Being file-based eliminates the need for a separate database management system, simplifying deployment and scaling.
  - **Flexible Storage:** Easily accommodates growing datasets by simply adding more Geohash partitions without restructuring existing data. This solution can also be migrated to cloud based object storate like Azure Blob, as is

- **Cost-Effective:**
  - Reduced over-head of deploying and managing servers for a database system reduces overall costs to maintain the system as object storage is comparatively cheaper

- **Flexibility:**
  - **Adaptable Partitioning:** Geohash-based partitioning can be easily adjusted by changing the resolution, allowing for different levels of data granularity as needed.

---

## How To Use The App

Currently, the application has data for only three cities: Karlsruhe, Stuttgart and Tiengen. You can click on either of locations to start your anaylsis. Stuttgart and Tiengen are observed to have interesting results

### Raster Layers

You can load these layers individually or overlay them for comprehensive analysis.

1. **Slope**
   - **Description**: Represents the steepness or incline of the terrain. Higher slope values indicate steeper areas. Interpolated from DTM points
   
2. **Aspect**
   - **Description**: Indicates the compass direction that a slope faces. It helps in understanding sun exposure and wind patterns. Dervied from interpolated slope raster
   
3. **Tri (Topographic Ruggedness Index)**
   - **Description**: Measures the ruggedness of the terrain by analyzing the variation in elevation. Dervied from interpolated slope raster
   
4. **TPI (Topographic Position Index)**
   - **Description**: Identifies the topographic position of each cell relative to its surroundings, distinguishing between peaks, valleys, and flat areas. Dervied from interpolated slope raster
   
5. **Solar Potential**
   - **Description**: Assesses the potential for solar energy generation based on slope and aspect. 
   
6. **Soil Erosion Risk**
   - **Description**: Evaluates the risk of soil erosion in different terrain sections, considering factors like slope and soil properties.
   
7. **Terrain Risk**
   - **Description**: A composite layer that combines multiple factors (excluding solar potential) to provide an overall risk assessment of the terrain.

### Vector Layers

In addition to raster data, buildings and parcels are also included for rendering

### Layer Loading and Customization

Users have the flexibility to load multiple layers simultaneously for their analysis:

- **Overlaying Layers**: You can load a vector layer such as **Buildings** and then overlay it with a raster layer like **Solar Potential** to visualize how building locations correlate with solar output.
- **Layer Management**: Toggle layers on and off to focus on specific data points or to declutter the map view.

### Interactive Features

- **Drawing Polygons**
  - **Usage**: Draw a polygon over an area of interest to perform detailed footprint analysis and assess surrounding terrain variations.
  
- **Dropping Pins**
  - **Usage**: Place a pin on a specific location to retrieve immediate terrain data and insights for that footprint.
  
- **Detailed Analysis**
  - Upon interacting with the map (drawing a polygon or dropping a pin), the app provides a reports on the selected area's footprint and its surrounding environment.

### Usage Scenarios

1. **Urban Planning**
   - Analyze building placements relative to terrain features to optimize infrastructure development.
   
2. **Environmental Assessment**
   - Evaluate soil erosion risks and terrain ruggedness to inform conservation efforts.
   
3. **Renewable Energy Planning**
   - Assess solar potential across different zones to identify optimal locations for solar panel installations.

### Important Warning

- **Polygon Size Recommendation**: For optimal performance and accurate results, **draw small polygons** that encompass **5-10 buildings**. Large polygons may lead to longer processing times and less precise analyses.

### Tracking and Monitoring Requests

Users can monitor their polygonal or point-based requests through the Infrastructure Dashboard:

- **Tracking Steps**:
  1. Navigate to the **Infrastructure Monitor**.
  2. Select the `credium_backend.1` container.
  3. View the logs for FastAPI endpoint interactions related to your requests (Polygonal/Point requests only)

### Testing with Swagger API

Terrain Mapper provides a Swagger API interface for testing and exploring backend endpoints:

- **Swagger API Documentation**: [Swagger API](https://terrain-mapper.example.com/docs)
  
- **Testing the `/rasterstats` Endpoint**:
  - **Purpose**: Clip raster files based on GeoJSON geometries and retrieve min/max values
  - **Supported `tif_url` Values**:
    - `cog_global_solar_potential.tif`
    - `cog_merged_aspect.tif`
    - `cog_merged_tpi.tif`
    - `cog_global_terrain_risk.tif`
    - `cog_merged_roughness.tif`
    - `cog_merged_tri.tif`
    - `cog_global_terrain_ser.tif`
    - `cog_merged_slope.tif`
    
  - **Usage**:
    1. Navigate to the `/rasterstats` endpoint in the Swagger UI.
    2. Provide the necessary GeoJSON geometry and select one of the recommended `tif_url` files.
    3. Execute the request to receive min and max raster values for the specified area.

## Deploying the Application Locally

To run the **Terrain Mapper** application on your local machine, follow the instructions below. The application only requires data to be downloaded and docker for running the app

### Data Section

Before running the application, you'll need to download the necessary raster and vector data, as well as the database files.

1. **Raster Data**
   - The raster data needs to be downloaded into the `data/raster/` folder.
   - Please refer to the [Raster Data Readme](data/raster/README.md) for instructions on where and how to download the data.

2. **Vector Data**
   - The vector data needs to be downloaded into the `data/vector/` folder.
   - For details on how to obtain this data, refer to the [Vector Data Readme](data/vector/README.md).

3. **Database**
   - The database files should be downloaded and stored in the `db/` folder.
   - For guidance on how to get these files, check the [Database Readme](db/README.md).

### Prerequisites

The only prerequisite for running this application locally is **Docker**. You can download Docker from the following sources, depending on your operating system:

- **Windows**: [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop)
- **Mac**: [Docker Desktop for Mac](https://www.docker.com/products/docker-desktop)
- **Linux**: [Install Docker on Linux](https://docs.docker.com/engine/install/)

Ensure that Docker is installed and running before proceeding with the deployment steps.

### Cloning the Repository

First, you'll need to clone the **Terrain Mapper** repository to your local machine. Run the following command in your terminal:

```
git clone https://github.com/purijs/terrain-mapper.git
cd terrain-mapper
```

### Deploying the Application

Once the repository is cloned, follow these steps to deploy the application locally using Docker Swarm:

- Initialize Docker Swarm

```
docker swarm init
```

- Deploy Docker Services

```
docker stack deploy --compose-file app/docker-compose.yml credium
```

This will start the various services (frontend, backend, raster titiler, vector tileserver, and monitoring) as defined in the Docker Compose file.

### Warning: Port Availability

Make sure the following ports are free on your local machine before deploying the application, as they will be used by the services:

- **9200**: Dozzle (Docker logs UI)
- **8081**: Frontend (App UI)
- **8080**: Backend (API)
- **8000**: Raster Tililer (Raster tiles)
- **9100**: Vector Tileserver (Vector tiles)
