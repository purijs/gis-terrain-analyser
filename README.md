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

`Terrain Mapper` is PoC application that uses a combination of Digital Terrain Data ([source][https://opengeodata.lgl-bw.de/#/(sidenav:product/3)]) and building footprints for 3 cities in Germany. The terrain data is interpolated as raster and different analytical layers are dervied from the interpolation. User can visually make interpretations, interact with app to get insights for specific footprints and developers can use API endpoints to extract data for machine learning purposes. The application runs in Docker Swarm environment, with 5 services to simulate a scalable workload.

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
