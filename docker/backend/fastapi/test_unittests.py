import unittest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import json
import os
import numpy as np
from main import GeoApp
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestGeoTerrainAPI(unittest.TestCase):
    def setUp(self):
        self.app = GeoApp().app
        self.client = TestClient(self.app)

    def test_health_check(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "Healthy"})

    @patch('main.rasterio.open')
    def test_clip_and_stats_success(self, mock_rasterio_open):
        logger.info("Testing /rasterstats endpoint with valid input.")
        mock_src = MagicMock()
        mock_src.nodata = None
        mock_src.__enter__.return_value = mock_src
        mock_rasterio_open.return_value = mock_src

        # Mock the mask function to return a numpy array
        with patch('main.mask', return_value=(np.array([[1, 2], [3, 4]]), None)):
            response = self.client.post(
                "/rasterstats",
                json={
                    "geojson": {
                        "type": "FeatureCollection",
                        "features": [{
                            "type": "Feature",
                            "geometry": {
                                "type": "Polygon",
                                "coordinates": [[[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]]
                            }
                        }]
                    },
                    "tif_url": "cog_merged_slope.tif"
                }
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"min": 1.0, "max": 4.0})

    @patch('main.os.path.exists')
    def test_clip_and_stats_file_not_found(self, mock_exists):
        logger.info("Testing /rasterstats endpoint with nonexistent raster file.")
        mock_exists.return_value = False

        response = self.client.post(
            "/rasterstats",
            json={
                "geojson": {
                    "type": "FeatureCollection",
                    "features": [{
                        "type": "Feature",
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [[[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]]
                        }
                    }]
                },
                "tif_url": "nonexistent_file.tif"
            }
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "Raster file not found."})

    @patch('main.BuildingService.generate_building_reports')
    def test_bbox_insights_success(self, mock_generate_reports):
        logger.info("Testing /stats endpoint with successful building report generation.")
        mock_generate_reports.return_value = [
            {
                "building_id": "test_id",
                "zonal_variation": {"north": {"slope": 10.5}},
                "zonal_variation_text": {"north": {"slope": "The slope is moderate. Value is 10.5."}},
                "neighborhood_understanding": {"north": {"slope": 11.0}},
                "neighborhood_understanding_text": {"north": {"slope": "The terrain to the north has a moderate slope."}}
            }
        ]

        response = self.client.post(
            "/stats",
            json={
                "geojson": {
                    "type": "FeatureCollection",
                    "features": [{
                        "type": "Feature",
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [[[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]]
                        }
                    }]
                }
            }
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["building_reports"]), 1)
        self.assertEqual(response.json()["building_reports"][0]["building_id"], "test_id")

    @patch('main.BuildingService.generate_building_reports')
    def test_bbox_insights_no_buildings(self, mock_generate_reports):
        logger.info("Testing /stats endpoint with no buildings found.")
        mock_generate_reports.return_value = []

        response = self.client.post(
            "/stats",
            json={
                "geojson": {
                    "type": "FeatureCollection",
                    "features": [{
                        "type": "Feature",
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [[[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]]
                        }
                    }]
                }
            }
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"building_reports": []})

    @patch('main.mask')
    @patch('main.rasterio.open')
    def test_clip_and_stats_with_nodata_values(self, mock_rasterio_open, mock_mask):
        logger.info("Testing /rasterstats endpoint with nodata values in raster data.")
        mock_src = MagicMock()
        mock_src.nodata = -9999
        mock_src.__enter__.return_value = mock_src
        mock_rasterio_open.return_value = mock_src

        # Mock the mask function to return data with nodata values
        mock_mask.return_value = (np.array([[-9999, 2], [3, 4]]), None)

        response = self.client.post(
            "/rasterstats",
            json={
                "geojson": {
                    "type": "FeatureCollection",
                    "features": [{
                        "type": "Feature",
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [[[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]]
                        }
                    }]
                },
                "tif_url": "cog_merged_slope.tif"
            }
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"min": 2.0, "max": 4.0})

    

    def test_clip_and_stats_with_malformed_geojson(self):
        logger.info("Testing /rasterstats endpoint with malformed GeoJSON.")
        response = self.client.post(
            "/rasterstats",
            json={
                "geojson": "This is not a valid GeoJSON",
                "tif_url": "cog_merged_slope.tif"
            }
        )

        self.assertEqual(response.status_code, 422)  # Unprocessable Entity

    def test_bbox_insights_invalid_input(self):
        logger.info("Testing /stats endpoint with invalid input data.")
        response = self.client.post(
            "/stats",
            json={
                "invalid_field": {
                    "type": "FeatureCollection",
                    "features": []
                }
            }
        )

        self.assertEqual(response.status_code, 422)  # Unprocessable Entity

    @patch('main.BuildingService.generate_building_reports')
    def test_bbox_insights_large_dataset(self, mock_generate_reports):
        logger.info("Testing /stats endpoint with a large dataset of building reports.")
        mock_generate_reports.return_value = [
            {
                "building_id": f"test_id_{i}",
                "zonal_variation": {"north": {"slope": 10.5}},
                "zonal_variation_text": {"north": {"slope": f"The slope is moderate. Value is 10.5."}},
                "neighborhood_understanding": {"north": {"slope": 11.0}},
                "neighborhood_understanding_text": {"north": {"slope": f"The terrain to the north has a moderate slope."}}
            } for i in range(100)  # Simulating 100 building reports
        ]

        response = self.client.post(
            "/stats",
            json={
                "geojson": {
                    "type": "FeatureCollection",
                    "features": [{
                        "type": "Feature",
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [[[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]]
                        }
                    }]
                }
            }
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["building_reports"]), 100)
        self.assertEqual(response.json()["building_reports"][0]["building_id"], "test_id_0")
        self.assertEqual(response.json()["building_reports"][-1]["building_id"], "test_id_99")

if __name__ == '__main__':
    unittest.main()