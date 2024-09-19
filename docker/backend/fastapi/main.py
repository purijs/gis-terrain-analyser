from typing import List, Dict, Optional
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import rasterio
from rasterio.mask import mask
import os
import numpy as np
from shapely.geometry import shape, Polygon
import geopandas as gpd
import pygeohash as pgh
import math
from multiprocessing import Pool, cpu_count
import logging
from fastapi.openapi.docs import get_swagger_ui_html

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------
# Pydantic Models
# ---------------------------

class GeoClipRequest(BaseModel):
    geojson: dict = Field(..., example={
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
          [
            [
              9.176925637402405,
              48.773048426764745
            ],
            [
              9.177896941776226,
              48.77325189677234
            ],
            [
              9.177966320660289,
              48.77301184779935
            ],
            [
              9.177282938654315,
              48.772611763627964
            ],
            [
              9.176842382742109,
              48.772915827889165
            ],
            [
              9.176925637402405,
              48.773048426764745
            ]
          ]
        ]
                },
                "properties": {}
            }
        ]
    })
    tif_url: str = Field(..., example="cog_merged_slope.tif")

class GeoInsights(BaseModel):
    geojson: dict = Field(..., example={
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
          [
            [
              9.176925637402405,
              48.773048426764745
            ],
            [
              9.177896941776226,
              48.77325189677234
            ],
            [
              9.177966320660289,
              48.77301184779935
            ],
            [
              9.177282938654315,
              48.772611763627964
            ],
            [
              9.176842382742109,
              48.772915827889165
            ],
            [
              9.176925637402405,
              48.773048426764745
            ]
          ]
        ]
                },
                "properties": {}
            }
        ]
    })

class RasterStatsResponse(BaseModel):
    min: Optional[float]
    max: Optional[float]

class HealthResponse(BaseModel):
    status: str

class BuildingReport(BaseModel):
    building_id: str
    zonal_variation: dict
    zonal_variation_text: dict
    neighborhood_understanding: dict
    neighborhood_understanding_text: dict

class StatsResponse(BaseModel):
    building_reports: List[BuildingReport]


# ---------------------------
# Services
# ---------------------------

class RasterService:
    def __init__(self, raster_paths: Dict[str, str]):
        self.raster_paths = raster_paths
        logger.info("RasterService initialized with raster paths.")

    def get_raster_stats(self, raster_key: str, zone_geom: Polygon) -> Optional[float]:
        logger.info(f"Starting get_raster_stats for raster_key: {raster_key}")
        raster_path = self.raster_paths.get(raster_key)
        if not raster_path:
            logger.error(f"No raster path found for key: {raster_key}")
            return None

        try:
            logger.info(f"Opening raster file: {raster_path}")
            with rasterio.open(raster_path) as src:
                logger.info(f"Masking raster with provided geometry.")
                out_image, _ = mask(src, [zone_geom], crop=True, all_touched=True)
                data = out_image

                if src.nodata is not None:
                    logger.info(f"Removing nodata values from raster data.")
                    data = data[data != src.nodata]
                if data.size == 0:
                    logger.warning(f"No data found in raster {raster_path} for zone {zone_geom}.")
                    return np.nan
                mean_val = float(data.mean())
                logger.info(f"Computed mean value for raster {raster_key}: {mean_val}")
                return mean_val
        except Exception as e:
            logger.error(f"Error processing raster {raster_path} for zone {zone_geom}: {e}")
            return np.nan

    def clip_raster_stats(self, geojson: dict, tif_path: str) -> Dict[str, Optional[float]]:
        logger.info(f"Starting clip_raster_stats for TIFF path: {tif_path}")
        try:
            logger.info(f"Opening raster file: {tif_path}")
            with rasterio.open(tif_path) as src:
                geometries = [shape(feature['geometry']) for feature in geojson['features']]
                logger.info(f"Masking raster with provided GeoJSON geometries.")
                clipped_image, _ = mask(src, geometries, crop=True, all_touched=True)

                if clipped_image.size == 0:
                    logger.warning("Clipped image has no data.")
                    return {"min": None, "max": None}

                # Remove nodata values
                if src.nodata is not None:
                    logger.info("Removing nodata values from clipped raster data.")
                    clipped_image = clipped_image[clipped_image != src.nodata]

                if clipped_image.size == 0:
                    logger.warning("Clipped image has no valid data after masking.")
                    return {"min": None, "max": None}

                min_val = float(np.min(clipped_image))
                max_val = float(np.max(clipped_image))

                logger.info(f"Raster stats - min: {min_val}, max: {max_val}")

                return {"min": min_val, "max": max_val}
        except Exception as e:
            logger.error(f"Error processing raster {tif_path}: {e}")
            raise

class GeohashService:
    def get_geohash_bbox(self, geohash: str) -> Polygon:
        logger.info(f"Starting get_geohash_bbox for geohash: {geohash}")
        try:
            lat_min, lon_min, lat_max, lon_max = pgh.decode_exactly(geohash)[:4]
            bbox = Polygon([
                (lon_min, lat_min),
                (lon_max, lat_min),
                (lon_max, lat_max),
                (lon_min, lat_max),
                (lon_min, lat_min)
            ])
            logger.info(f"Generated bounding box for geohash {geohash}.")
            return bbox
        except Exception as e:
            logger.error(f"Error decoding geohash {geohash}: {e}")
            return Polygon()

    def geohash_grid_covering_polygon(self, polygon: Polygon, resolution: int) -> List[str]:
        logger.info(f"Starting geohash_grid_covering_polygon with resolution: {resolution}")
        try:
            minx, miny, maxx, maxy = polygon.bounds
            lat_steps = 100  
            lon_steps = 100

            latitudes = np.linspace(miny, maxy, lat_steps)
            longitudes = np.linspace(minx, maxx, lon_steps)

            geohashes = set()
            logger.info("Generating geohash grid covering the polygon.")
            for lat in latitudes:
                for lon in longitudes:
                    geohash = pgh.encode(lat, lon, precision=resolution)
                    geohashes.add(geohash)

            logger.info(f"Generated {len(geohashes)} geohashes covering the polygon.")
            return list(geohashes)
        except Exception as e:
            logger.error(f"Error generating geohash grid: {e}")
            return []

    def filter_intersecting_geohashes(self, polygon: Polygon, geohashes: List[str]) -> List[str]:
        logger.info("Starting filter_intersecting_geohashes.")
        intersecting_geohashes = []
        for geohash in geohashes:
            logger.info(f"Checking intersection for geohash: {geohash}")
            geohash_polygon = self.get_geohash_bbox(geohash)
            if polygon.intersects(geohash_polygon):
                logger.info(f"Geohash {geohash} intersects with the polygon.")
                intersecting_geohashes.append(geohash)
            else:
                logger.info(f"Geohash {geohash} does not intersect with the polygon.")
        logger.info(f"Total intersecting geohashes: {len(intersecting_geohashes)}")
        return intersecting_geohashes

class InterpretationService:
    def interpret_slope(self, slope_value: float) -> str:
        logger.info(f"Interpreting slope value: {slope_value}")
        if slope_value < 10:
            return "gentle"
        elif 10 <= slope_value < 30:
            return "moderate"
        else:
            return "steep"

    def interpret_aspect(self, aspect_value: float) -> str:
        logger.info(f"Interpreting aspect value: {aspect_value}")
        if 0 <= aspect_value < 45 or 315 <= aspect_value <= 360:
            return "north"
        elif 45 <= aspect_value < 135:
            return "east"
        elif 135 <= aspect_value < 225:
            return "south"
        elif 225 <= aspect_value < 315:
            return "west"
        else:
            return "unknown"

    def interpret_solar_potential(self, solar_value: float, solar_min: float, solar_max: float) -> str:
        logger.info(f"Interpreting solar potential value: {solar_value} with min: {solar_min}, max: {solar_max}")
        if solar_value is None or np.isnan(solar_value):
            return "unknown"
        if solar_value < solar_min + (solar_max - solar_min) * 0.33:
            return "lower end"
        elif solar_min + (solar_max - solar_min) * 0.33 <= solar_value < solar_min + (solar_max - solar_min) * 0.66:
            return "middle range"
        else:
            return "higher end"

    def determine_aspect_relation(self, direction: str, aspect_value: float) -> str:
        logger.info(f"Determining aspect relation for direction: {direction}, aspect_value: {aspect_value}")
        towards_aspect = {
            'north': 180,
            'south': 0,    # or 360
            'east': 270,
            'west': 90
        }

        threshold = 45  # degrees
        expected = towards_aspect.get(direction, None)

        if expected is None:
            logger.warning(f"Unknown direction: {direction}")
            return "unknown relation"

        lower = (expected - threshold) % 360
        upper = (expected + threshold) % 360

        if lower < upper:
            if lower <= aspect_value < upper:
                return 'towards'
            else:
                return 'away'
        else:
            if aspect_value >= lower or aspect_value < upper:
                return 'towards'
            else:
                return 'away'

class ReportService:
    def __init__(self, interpretation_service: InterpretationService):
        self.interpretation_service = interpretation_service
        logger.info("ReportService initialized with InterpretationService.")

    def generate_textual_report(self, zonal_variation: dict, raster_stats: dict) -> dict:
        logger.info("Generating textual report for zonal variation.")
        descriptions = {}
        solar_min, solar_max = raster_stats.get('solar', (0, 1))  # Avoid division by zero

        for zone, values in zonal_variation.items():
            slope_value = np.round(values.get('slope', np.nan), 2)
            aspect_value = np.round(values.get('aspect', np.nan), 2)
            solar_value = np.round(values.get('solar', np.nan), 2)

            logger.info(f"Processing zone: {zone} with slope: {slope_value}, aspect: {aspect_value}, solar: {solar_value}")

            slope_description = self.interpretation_service.interpret_slope(slope_value)
            aspect_description = self.interpretation_service.interpret_aspect(aspect_value)

            if solar_value is not None and not np.isnan(solar_value):
                solar_description = self.interpretation_service.interpret_solar_potential(solar_value, solar_min, solar_max)
                solar_text = f"The solar potential is in the {solar_description}. Value is {solar_value}."
            else:
                solar_text = "The solar potential data is unavailable."

            descriptions[zone] = {
                'slope': f"The slope is {slope_description}. Value is {slope_value}.",
                'aspect': f"The aspect is facing {aspect_description}. Value is {aspect_value}.",
                'solar': solar_text
            }
            logger.info(f"Generated textual description for zone {zone}.")

        logger.info("Completed generating textual report for zonal variation.")
        return descriptions

    def generate_neighborhood_report(self, neighborhood_stats: dict, raster_stats: dict) -> dict:
        logger.info("Generating neighborhood report.")
        descriptions = {}
        solar_min, solar_max = raster_stats.get('solar', (0, 1))  # Avoid division by zero

        for direction, stats in neighborhood_stats.items():
            slope_value = stats.get('slope', None)
            aspect_value = stats.get('aspect', None)

            logger.info(f"Processing neighborhood direction: {direction} with slope: {slope_value}, aspect: {aspect_value}")

            if slope_value is not None and not np.isnan(slope_value):
                slope_description = self.interpretation_service.interpret_slope(slope_value)
            else:
                slope_description = "unknown slope"

            if aspect_value is not None and not np.isnan(aspect_value):
                aspect_direction = self.interpretation_service.interpret_aspect(aspect_value)
                relation = self.interpretation_service.determine_aspect_relation(direction, aspect_value)
                if relation == 'towards':
                    relation_text = "facing towards the building."
                elif relation == 'away':
                    relation_text = "facing away from the building."
                else:
                    relation_text = "facing an unknown direction relative to the building."
            else:
                aspect_direction = "unknown aspect"
                relation_text = "unknown relation to the building."

            descriptions[direction] = {
                'slope': f"The terrain to the {direction} has a {slope_description} slope.",
                'aspect': f"It is facing {aspect_direction} and is {relation_text}"
            }
            logger.info(f"Generated neighborhood description for direction {direction}.")

        logger.info("Completed generating neighborhood report.")
        return descriptions

class BuildingService:
    def __init__(self, raster_service: RasterService, geohash_service: GeohashService, report_service: ReportService, db_path: str):
        self.raster_service = raster_service
        self.geohash_service = geohash_service
        self.report_service = report_service
        self.db_path = db_path
        logger.info("BuildingService initialized with RasterService, GeohashService, and ReportService.")

    def get_raster_stats_for_zone(self, raster_key: str, zone_geom: Polygon) -> Optional[float]:
        logger.info(f"Retrieving raster stats for key: {raster_key}")
        stats = self.raster_service.get_raster_stats(raster_key, zone_geom)
        if stats is not None:
            logger.info(f"Retrieved raster stats for {raster_key}: {stats}")
        else:
            logger.warning(f"Raster stats for {raster_key} could not be retrieved.")
        return stats

    def calculate_zonal_variation(self, building_geom: Polygon) -> dict:
        logger.info("Calculating zonal variation for building geometry.")
        minx, miny, maxx, maxy = building_geom.bounds
        width = maxx - minx
        height = maxy - miny

        zone_percentage = 0.4  # Adjust this value to change the size of the zones

        zones = {
            'north': building_geom.intersection(Polygon([
                (minx, maxy - height * zone_percentage),
                (maxx, maxy - height * zone_percentage),
                (maxx, maxy),
                (minx, maxy)
            ])),
            'south': building_geom.intersection(Polygon([
                (minx, miny),
                (maxx, miny),
                (maxx, miny + height * zone_percentage),
                (minx, miny + height * zone_percentage)
            ])),
            'east': building_geom.intersection(Polygon([
                (maxx - width * zone_percentage, miny),
                (maxx, miny),
                (maxx, maxy),
                (maxx - width * zone_percentage, maxy)
            ])),
            'west': building_geom.intersection(Polygon([
                (minx, miny),
                (minx + width * zone_percentage, miny),
                (minx + width * zone_percentage, maxy),
                (minx, maxy)
            ]))
        }

        logger.info("Generated zonal geometries for north, south, east, and west.")

        zonal_stats = {}
        for zone_name, zone_geom in zones.items():
            if not zone_geom.is_empty:
                logger.info(f"Calculating raster stats for zone: {zone_name}")
                zonal_stats[zone_name] = {
                    'slope': self.get_raster_stats_for_zone('slope', zone_geom),
                    'aspect': self.get_raster_stats_for_zone('aspect', zone_geom),
                    'solar': self.get_raster_stats_for_zone('solar', zone_geom)
                }
            else:
                logger.info(f"No geometry found for zone: {zone_name}. Setting stats to None.")
                zonal_stats[zone_name] = {
                    'slope': None,
                    'aspect': None,
                    'solar': None
                }

        logger.info("Completed calculating zonal variation.")
        return zonal_stats

    def calculate_neighborhood_analysis(self, building_geom: Polygon) -> dict:
        logger.info("Starting neighborhood analysis for building geometry.")
        buffer_distance = 0.0001  # Adjust this value as needed
        buffered_polygon = building_geom.buffer(buffer_distance).simplify(0.5)
        buffer_ring = buffered_polygon.difference(building_geom)

        minx, miny, maxx, maxy = buffer_ring.bounds
        width = maxx - minx
        height = maxy - miny

        direction_percentage = 0.4

        directions = {
            'north': buffer_ring.intersection(Polygon([
                (minx, maxy - height * direction_percentage),
                (maxx, maxy - height * direction_percentage),
                (maxx, maxy),
                (minx, maxy)
            ])),
            'south': buffer_ring.intersection(Polygon([
                (minx, miny),
                (maxx, miny),
                (maxx, miny + height * direction_percentage),
                (minx, miny + height * direction_percentage)
            ])),
            'east': buffer_ring.intersection(Polygon([
                (maxx - width * direction_percentage, miny),
                (maxx, miny),
                (maxx, maxy),
                (maxx - width * direction_percentage, maxy)
            ])),
            'west': buffer_ring.intersection(Polygon([
                (minx, miny),
                (minx + width * direction_percentage, miny),
                (minx + width * direction_percentage, maxy),
                (minx, maxy)
            ]))
        }

        logger.info("Generated neighborhood geometries for north, south, east, and west.")

        neighborhood_stats = {}
        for direction, direction_geom in directions.items():
            if not direction_geom.is_empty:
                logger.info(f"Calculating raster stats for neighborhood direction: {direction}")
                neighborhood_stats[direction] = {
                    'slope': self.get_raster_stats_for_zone('slope', direction_geom),
                    'aspect': self.get_raster_stats_for_zone('aspect', direction_geom)
                }
            else:
                logger.info(f"No geometry found for neighborhood direction: {direction}. Setting stats to None.")
                neighborhood_stats[direction] = {
                    'slope': None,
                    'aspect': None
                }

        logger.info("Completed neighborhood analysis.")
        return neighborhood_stats

    def generate_textual_report(self, zonal_variation: dict, raster_stats: dict) -> dict:
        logger.info("Generating textual report for building.")
        return self.report_service.generate_textual_report(zonal_variation, raster_stats)

    def generate_neighborhood_report(self, neighborhood_stats: dict, raster_stats: dict) -> dict:
        logger.info("Generating textual neighborhood report for building.")
        return self.report_service.generate_neighborhood_report(neighborhood_stats, raster_stats)

    def process_building(self, building: gpd.GeoSeries, input_geom: Polygon, raster_stats: dict) -> Optional[dict]:
        building_id = building.get('gmlid', 'unknown')
        logger.info(f"Processing building with ID: {building_id}")

        building_geom = building['geometry']

        if not building_geom.intersects(input_geom):
            logger.info(f"Building ID {building_id} does not intersect with input geometry. Skipping.")
            return None

        logger.info(f"Building ID {building_id} intersects with input geometry. Calculating zonal variation.")
        zonal_variation = self.calculate_zonal_variation(building_geom)
        zonal_text = self.generate_textual_report(zonal_variation, raster_stats)

        logger.info(f"Building ID {building_id}: Completed zonal variation report. Starting neighborhood analysis.")
        neighborhood_understanding = self.calculate_neighborhood_analysis(building_geom)
        neighborhood_text = self.generate_neighborhood_report(neighborhood_understanding, raster_stats)

        logger.info(f"Building ID {building_id}: Completed neighborhood analysis.")

        report = {
            'building_id': building_id,
            'zonal_variation': zonal_variation,
            'zonal_variation_text': zonal_text,
            'neighborhood_understanding': neighborhood_understanding,
            'neighborhood_understanding_text': neighborhood_text
        }

        logger.info(f"Building ID {building_id}: Report generation complete.")
        return report

    def process_geohash(self, geohash: str, input_geom: Polygon, raster_stats: dict) -> List[dict]:
        logger.info(f"Processing geohash: {geohash}")
        building_path = os.path.join(self.db_path, f"{geohash}/buildings.parquet")

        if not os.path.exists(building_path):
            logger.warning(f"Building path {building_path} does not exist. Skipping geohash {geohash}.")
            return []

        try:
            logger.info(f"Reading buildings from {building_path}")
            building_df = gpd.read_parquet(building_path).sjoin(
                gpd.GeoDataFrame(geometry=[input_geom], crs='EPSG:4326'),
                how='inner',
                predicate='intersects'
            )
            building_df = building_df.drop_duplicates(subset='geometry')
            logger.info(f"Found {building_df.shape[0]} buildings intersecting with input geometry in geohash {geohash}.")

            if building_df.shape[0] > 10:
                logger.info(f"Sampling 10 buildings from geohash {geohash} for processing.")
                building_df = building_df.sample(10)

        except Exception as e:
            logger.error(f"Error reading/parsing buildings for geohash {geohash}: {e}")
            return []

        if building_df.empty:
            logger.info(f"No intersecting buildings found in geohash {geohash}.")
            return []

        args = [(building, input_geom, raster_stats) for _, building in building_df.iterrows()]
        logger.info(f"Starting multiprocessing pool with {cpu_count()} workers for geohash {geohash}.")
        with Pool(cpu_count()) as pool:
            building_reports = pool.starmap(self.process_building, args)

        logger.info(f"Completed processing buildings for geohash {geohash}.")
        return [report for report in building_reports if report]

    def generate_building_reports(self, geojson: dict, raster_stats: dict, db_path: Optional[str] = None) -> List[dict]:
        logger.info("Generating building reports from GeoJSON input.")
        try:
            input_gdf = gpd.GeoDataFrame.from_features(geojson["features"])
            input_gdf.set_crs('EPSG:4326', inplace=True)
            input_geom = input_gdf.geometry.iloc[0]
            logger.info("Parsed GeoJSON input successfully.")
        except Exception as e:
            logger.error(f"Error parsing GeoJSON input: {e}")
            return []

        geohashes = self.geohash_service.geohash_grid_covering_polygon(input_geom, resolution=6)
        logger.info(f"Found {len(geohashes)} geohashes covering the input polygon.")

        building_reports = []
        for geohash in geohashes:
            logger.info(f"Processing buildings in geohash: {geohash}")
            reports = self.process_geohash(geohash, input_geom, raster_stats)
            building_reports.extend(reports)
            logger.info(f"Accumulated {len(building_reports)} building reports so far.")

        logger.info(f"Generated reports for {len(building_reports)} buildings in total.")
        return building_reports

class ReportCleaner:
    @staticmethod
    def remove_nan_values(data):
        """ Recursively replace NaN and Inf values with None in nested dictionaries and lists. """
        if isinstance(data, dict):
            return {k: ReportCleaner.remove_nan_values(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [ReportCleaner.remove_nan_values(i) for i in data]
        elif isinstance(data, float) and (math.isnan(data) or math.isinf(data)):
            logger.info("Replacing NaN or Inf value with None.")
            return None  # Replace NaN or infinite values with None
        return data


# ---------------------------
# Application Initialization
# ---------------------------

class GeoApp:
    def __init__(self):
        self.app = FastAPI(
            title="GeoTerrain API",
            description="API for interacting with Terrain Analysis portal",
            version="1.0.0",
            contact={
                "name": "Jaskaran",
            }
        )
        self.configure_middleware()
        self.configure_services()
        self.configure_routes()

    def configure_middleware(self):
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["*"],
            allow_credentials=True,
        )

    def configure_services(self):
        terrain_rasters = {
            'slope': '/var/task/fastapi/data/raster/cog_merged_slope.tif',
            'aspect': '/var/task/fastapi/data/raster/cog_merged_aspect.tif',
            'solar': '/var/task/fastapi/data/raster/cog_global_solar_potential.tif'
        }
        self.raster_service = RasterService(terrain_rasters)
        self.geohash_service = GeohashService()
        self.interpretation_service = InterpretationService()
        self.report_service = ReportService(self.interpretation_service)
        self.building_service = BuildingService(
            raster_service=self.raster_service,
            geohash_service=self.geohash_service,
            report_service=self.report_service,
            db_path='/var/task/fastapi/db/'
        )
        self.report_cleaner = ReportCleaner()

    def configure_routes(self):
        app = self.app
        building_service = self.building_service
        raster_service = self.raster_service

        @app.post(
            "/rasterstats",
            response_model=RasterStatsResponse,
            summary="Clip Raster and Get Statistics For Terrain Raster",
            description="Clips a raster file based on the provided GeoJSON geometry and returns the minimum and maximum values within the clipped area.",
            tags=["Raster Operations"]
        )
        def clip_and_stats(request_data: GeoClipRequest):
            base_path = '/var/task/fastapi/data/raster/'
            geojson = request_data.geojson
            tif_url = os.path.join(base_path, request_data.tif_url)

            if not os.path.exists(tif_url):
                logger.error(f"Raster file {tif_url} does not exist.")
                raise HTTPException(status_code=404, detail="Raster file not found.")

            try:
                stats = raster_service.clip_raster_stats(geojson, tif_url)
                return stats
            except Exception as e:
                logger.error(f"Error in /rasterstats: {e}")
                raise HTTPException(status_code=500, detail="Error processing raster data.")

        @app.get(
            "/health",
            response_model=HealthResponse,
            summary="Health Check",
            description="Returns the health status of the App.",
            tags=["Health Check"]
        )
        def health():
            return {'status': 'Healthy'}

        @app.post(
            "/stats",
            response_model=StatsResponse,
            summary="Generate Building Insights",
            description="Processes building data within a GeoJSON polygon and returns detailed reports.",
            tags=["Building Insights"]
        )
        def bbox_insights(request_data: GeoInsights):
            raster_stats = {
                "slope": [101.018, 657.570],
                "aspect": [0, 360],
                "solar": [0, 975]
            }
            building_reports = building_service.generate_building_reports(request_data.geojson, raster_stats)
            cleaned_reports = ReportCleaner.remove_nan_values(building_reports)
            return {'building_reports': cleaned_reports}

# Instantiate the application
geo_app = GeoApp()
app = geo_app.app
