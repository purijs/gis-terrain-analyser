# test_ci_unittests.py

import unittest
from unittest.mock import patch, MagicMock
import numpy as np
from fastapi.testclient import TestClient
from main import GeoApp
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestCIUnitGeoTerrainAPI(unittest.TestCase):
    def setUp(self):
        self.app = GeoApp().app
        self.client = TestClient(self.app)

    def test_health_check(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "Healthy"})

    @patch('main.os.path.exists')
    def test_clip_and_stats_file_not_found(self, mock_exists):
        logger.info("Testing /rasterstats endpoint with nonexistent raster file.")

        # Mock os.path.exists to return False
        mock_exists.return_value = False

        # Make the POST request
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

        # Assert response
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "Raster file not found."})

    @patch('main.BuildingService.generate_building_reports')
    def test_bbox_insights_success(self, mock_generate_reports):
        logger.info("Testing /stats endpoint with successful building report generation.")

        # Mock BuildingService.generate_building_reports to return a sample report
        mock_generate_reports.return_value = [
            {
                "building_id": "test_id",
                "zonal_variation": {"north": {"slope": 10.5}},
                "zonal_variation_text": {"north": {"slope": "The slope is moderate. Value is 10.5."}},
                "neighborhood_understanding": {"north": {"slope": 11.0}},
                "neighborhood_understanding_text": {"north": {"slope": "The terrain to the north has a moderate slope."}}
            }
        ]

        # Make the POST request
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

        # Assert response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["building_reports"]), 1)
        self.assertEqual(response.json()["building_reports"][0]["building_id"], "test_id")

    @patch('main.BuildingService.generate_building_reports')
    def test_bbox_insights_no_buildings(self, mock_generate_reports):
        logger.info("Testing /stats endpoint with no buildings found.")

        # Mock BuildingService.generate_building_reports to return an empty list
        mock_generate_reports.return_value = []

        # Make the POST request
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

        # Assert response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"building_reports": []})

    def test_clip_and_stats_with_malformed_geojson(self):
        logger.info("Testing /rasterstats endpoint with malformed GeoJSON.")

        # Make the POST request with invalid GeoJSON
        response = self.client.post(
            "/rasterstats",
            json={
                "geojson": "This is not a valid GeoJSON",
                "tif_url": "cog_merged_slope.tif"
            }
        )

        # Assert response
        self.assertEqual(response.status_code, 422)  # Unprocessable Entity

    def test_bbox_insights_invalid_input(self):
        logger.info("Testing /stats endpoint with invalid input data.")

        # Make the POST request with invalid input
        response = self.client.post(
            "/stats",
            json={
                "invalid_field": {
                    "type": "FeatureCollection",
                    "features": []
                }
            }
        )

        # Assert response
        self.assertEqual(response.status_code, 422)  # Unprocessable Entity

    @patch('main.BuildingService.generate_building_reports')
    def test_bbox_insights_large_dataset(self, mock_generate_reports):
        logger.info("Testing /stats endpoint with a large dataset of building reports.")

        # Mock BuildingService.generate_building_reports to return a large number of reports
        mock_generate_reports.return_value = [
            {
                "building_id": f"test_id_{i}",
                "zonal_variation": {"north": {"slope": 10.5}},
                "zonal_variation_text": {"north": {"slope": f"The slope is moderate. Value is 10.5."}},
                "neighborhood_understanding": {"north": {"slope": 11.0}},
                "neighborhood_understanding_text": {"north": {"slope": f"The terrain to the north has a moderate slope."}}
            } for i in range(100)  # Simulating 100 building reports
        ]

        # Make the POST request
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

        # Assert response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["building_reports"]), 100)
        self.assertEqual(response.json()["building_reports"][0]["building_id"], "test_id_0")
        self.assertEqual(response.json()["building_reports"][-1]["building_id"], "test_id_99")

if __name__ == '__main__':
    unittest.main()
