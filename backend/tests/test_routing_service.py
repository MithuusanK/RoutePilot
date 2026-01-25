"""
Unit tests for the routing service module.

These tests do not make real OSRM calls - all external requests are mocked.
"""

import pytest
import httpx
import respx
from httpx import Response

from services.routing import (
    compute_trucking_route_summary,
    RoutingValidationError,
    RoutingUpstreamError,
    _validate_stops,
    _build_osrm_coords_string,
    _meters_to_km,
    _seconds_to_minutes,
)

# Base URL used in config (http, not https)
OSRM_BASE = "http://router.project-osrm.org"


class TestValidateStops:
    """Tests for _validate_stops function."""
    
    def test_empty_stops_raises_error(self):
        with pytest.raises(RoutingValidationError, match="At least 2 stops"):
            _validate_stops([])
    
    def test_single_stop_raises_error(self):
        with pytest.raises(RoutingValidationError, match="At least 2 stops"):
            _validate_stops([{"lat": 32.8, "lng": -96.8}])
    
    def test_missing_lat_raises_error(self):
        stops = [
            {"lat": 32.8, "lng": -96.8},
            {"lng": -97.0}  # missing lat
        ]
        with pytest.raises(RoutingValidationError, match="Stop 2 missing required coordinates"):
            _validate_stops(stops)
    
    def test_missing_lng_raises_error(self):
        stops = [
            {"lat": 32.8},  # missing lng
            {"lat": 33.0, "lng": -97.0}
        ]
        with pytest.raises(RoutingValidationError, match="Stop 1 missing required coordinates"):
            _validate_stops(stops)
    
    def test_none_lat_raises_error(self):
        stops = [
            {"lat": None, "lng": -96.8},
            {"lat": 33.0, "lng": -97.0}
        ]
        with pytest.raises(RoutingValidationError, match="Stop 1 missing required coordinates"):
            _validate_stops(stops)
    
    def test_nan_lat_raises_error(self):
        stops = [
            {"lat": float("nan"), "lng": -96.8},
            {"lat": 33.0, "lng": -97.0}
        ]
        with pytest.raises(RoutingValidationError, match="invalid coordinates \\(NaN\\)"):
            _validate_stops(stops)
    
    def test_nan_lng_raises_error(self):
        stops = [
            {"lat": 32.8, "lng": float("nan")},
            {"lat": 33.0, "lng": -97.0}
        ]
        with pytest.raises(RoutingValidationError, match="invalid coordinates \\(NaN\\)"):
            _validate_stops(stops)
    
    def test_non_numeric_lat_raises_error(self):
        stops = [
            {"lat": "invalid", "lng": -96.8},
            {"lat": 33.0, "lng": -97.0}
        ]
        with pytest.raises(RoutingValidationError, match="non-numeric coordinates"):
            _validate_stops(stops)
    
    def test_lat_out_of_range_raises_error(self):
        stops = [
            {"lat": 95.0, "lng": -96.8},  # lat > 90
            {"lat": 33.0, "lng": -97.0}
        ]
        with pytest.raises(RoutingValidationError, match="latitude .* out of range"):
            _validate_stops(stops)
    
    def test_lng_out_of_range_raises_error(self):
        stops = [
            {"lat": 32.8, "lng": -200.0},  # lng < -180
            {"lat": 33.0, "lng": -97.0}
        ]
        with pytest.raises(RoutingValidationError, match="longitude .* out of range"):
            _validate_stops(stops)
    
    def test_valid_stops_pass(self):
        stops = [
            {"lat": 32.8, "lng": -96.8},
            {"lat": 33.0, "lng": -97.0}
        ]
        # Should not raise
        _validate_stops(stops)
    
    def test_latitude_longitude_aliases_work(self):
        """Test that 'latitude'/'longitude' keys work as aliases."""
        stops = [
            {"latitude": 32.8, "longitude": -96.8},
            {"latitude": 33.0, "longitude": -97.0}
        ]
        # Should not raise
        _validate_stops(stops)


class TestBuildOsrmCoordsString:
    """Tests for _build_osrm_coords_string function."""
    
    def test_basic_coords_string(self):
        stops = [
            {"lat": 32.8357, "lng": -96.9217},
            {"lat": 35.4676, "lng": -97.5164}
        ]
        result = _build_osrm_coords_string(stops)
        assert result == "-96.9217,32.8357;-97.5164,35.4676"
    
    def test_three_stops(self):
        stops = [
            {"lat": 32.0, "lng": -96.0},
            {"lat": 33.0, "lng": -97.0},
            {"lat": 34.0, "lng": -98.0}
        ]
        result = _build_osrm_coords_string(stops)
        assert result == "-96.0,32.0;-97.0,33.0;-98.0,34.0"
    
    def test_latitude_longitude_aliases(self):
        stops = [
            {"latitude": 32.8, "longitude": -96.9},
            {"latitude": 35.4, "longitude": -97.5}
        ]
        result = _build_osrm_coords_string(stops)
        assert result == "-96.9,32.8;-97.5,35.4"


class TestUnitConversions:
    """Tests for unit conversion functions."""
    
    def test_meters_to_km_basic(self):
        assert _meters_to_km(1000) == 1.0
        assert _meters_to_km(5000) == 5.0
    
    def test_meters_to_km_rounding(self):
        assert _meters_to_km(1234) == 1.23
        assert _meters_to_km(1235) == 1.24  # rounds .235 to .24
        assert _meters_to_km(100567) == 100.57
    
    def test_meters_to_km_zero(self):
        assert _meters_to_km(0) == 0.0
    
    def test_seconds_to_minutes_basic(self):
        assert _seconds_to_minutes(60) == 1.0
        assert _seconds_to_minutes(120) == 2.0
    
    def test_seconds_to_minutes_rounding(self):
        assert _seconds_to_minutes(90) == 1.5
        assert _seconds_to_minutes(95) == 1.6  # rounds
        assert _seconds_to_minutes(3661) == 61.0
    
    def test_seconds_to_minutes_zero(self):
        assert _seconds_to_minutes(0) == 0.0


class TestComputeTruckingRouteSummary:
    """Integration tests for compute_trucking_route_summary with mocked OSRM."""
    
    @pytest.fixture
    def valid_stops(self):
        return [
            {"lat": 32.8357, "lng": -96.9217},
            {"lat": 35.4676, "lng": -97.5164}
        ]
    
    @pytest.fixture
    def osrm_success_response(self):
        return {
            "code": "Ok",
            "routes": [
                {
                    "distance": 350000,  # 350 km in meters
                    "duration": 14400    # 4 hours in seconds (240 minutes)
                }
            ]
        }
    
    @respx.mock
    @pytest.mark.asyncio
    async def test_successful_route_calculation(self, valid_stops, osrm_success_response):
        respx.route(
            method="GET",
            host="router.project-osrm.org",
            path__startswith="/route/v1/driving/"
        ).mock(return_value=Response(200, json=osrm_success_response))
        
        result = await compute_trucking_route_summary(valid_stops)
        
        assert result["total_distance_km"] == 350.0
        assert result["total_drive_time_minutes"] == 240.0
        assert result["routing_engine"] == "osrm"
        assert isinstance(result["notes"], list)
        assert len(result["notes"]) > 0
        assert any("truck restrictions" in note.lower() for note in result["notes"])
    
    @respx.mock
    @pytest.mark.asyncio
    async def test_validation_error_propagates(self):
        # No need to mock OSRM - validation happens first
        with pytest.raises(RoutingValidationError):
            await compute_trucking_route_summary([{"lat": 32.0, "lng": -96.0}])
    
    @respx.mock
    @pytest.mark.asyncio
    async def test_osrm_timeout_raises_upstream_error(self, valid_stops):
        respx.route(
            method="GET",
            host="router.project-osrm.org",
            path__startswith="/route/v1/driving/"
        ).mock(side_effect=httpx.TimeoutException("Connection timed out"))
        
        with pytest.raises(RoutingUpstreamError, match="timed out"):
            await compute_trucking_route_summary(valid_stops)
    
    @respx.mock
    @pytest.mark.asyncio
    async def test_osrm_connection_error_raises_upstream_error(self, valid_stops):
        respx.route(
            method="GET",
            host="router.project-osrm.org",
            path__startswith="/route/v1/driving/"
        ).mock(side_effect=httpx.ConnectError("Connection refused"))
        
        with pytest.raises(RoutingUpstreamError, match="unavailable"):
            await compute_trucking_route_summary(valid_stops)
    
    @respx.mock
    @pytest.mark.asyncio
    async def test_osrm_non_200_raises_upstream_error(self, valid_stops):
        respx.route(
            method="GET",
            host="router.project-osrm.org",
            path__startswith="/route/v1/driving/"
        ).mock(return_value=Response(503, json={"message": "Service unavailable"}))
        
        with pytest.raises(RoutingUpstreamError, match="HTTP 503"):
            await compute_trucking_route_summary(valid_stops)
    
    @respx.mock
    @pytest.mark.asyncio
    async def test_osrm_code_not_ok_raises_upstream_error(self, valid_stops):
        respx.route(
            method="GET",
            host="router.project-osrm.org",
            path__startswith="/route/v1/driving/"
        ).mock(return_value=Response(200, json={
            "code": "NoRoute",
            "message": "No route found"
        }))
        
        with pytest.raises(RoutingUpstreamError, match="No route found"):
            await compute_trucking_route_summary(valid_stops)
    
    @respx.mock
    @pytest.mark.asyncio
    async def test_osrm_empty_routes_raises_upstream_error(self, valid_stops):
        respx.route(
            method="GET",
            host="router.project-osrm.org",
            path__startswith="/route/v1/driving/"
        ).mock(return_value=Response(200, json={
            "code": "Ok",
            "routes": []
        }))
        
        with pytest.raises(RoutingUpstreamError, match="No route found"):
            await compute_trucking_route_summary(valid_stops)
    
    @respx.mock
    @pytest.mark.asyncio
    async def test_osrm_invalid_json_raises_upstream_error(self, valid_stops):
        respx.route(
            method="GET",
            host="router.project-osrm.org",
            path__startswith="/route/v1/driving/"
        ).mock(return_value=Response(200, content=b"not json"))
        
        with pytest.raises(RoutingUpstreamError, match="invalid response"):
            await compute_trucking_route_summary(valid_stops)
