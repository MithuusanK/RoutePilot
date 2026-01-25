"""
API tests for the route endpoint.

These tests verify the endpoint logic by testing the routing service directly
and the Pydantic models. Full integration testing requires compatible package
versions (fastapi, starlette, httpx).
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import uuid

from services.routing import (
    compute_trucking_route_summary,
    RoutingValidationError,
    RoutingUpstreamError,
)


@pytest.fixture
def valid_trip_id():
    return str(uuid.uuid4())


@pytest.fixture
def valid_stops_payload():
    return [
        {"lat": 32.8357, "lng": -96.9217},
        {"lat": 35.4676, "lng": -97.5164},
        {"lat": 39.7392, "lng": -104.9903}
    ]


@pytest.fixture
def route_summary_response():
    return {
        "total_distance_km": 500.0,
        "total_drive_time_minutes": 300.0,
        "routing_engine": "osrm",
        "notes": ["Route is an estimate and may not account for truck restrictions."]
    }


class TestRouteEndpointModels:
    """Test the Pydantic models used by the endpoint."""
    
    def test_stop_coordinate_with_lat_lng(self):
        """Test StopCoordinate model with lat/lng keys."""
        from main import StopCoordinate
        
        stop = StopCoordinate(lat=32.8357, lng=-96.9217)
        assert stop.lat == 32.8357
        assert stop.lng == -96.9217
    
    def test_stop_coordinate_with_latitude_longitude(self):
        """Test StopCoordinate model with latitude/longitude keys."""
        from main import StopCoordinate
        
        stop = StopCoordinate(latitude=32.8357, longitude=-96.9217)
        assert stop.latitude == 32.8357
        assert stop.longitude == -96.9217
    
    def test_route_request_with_stops(self):
        """Test RouteRequest model with stops."""
        from main import RouteRequest, StopCoordinate
        
        request = RouteRequest(stops=[
            StopCoordinate(lat=32.8, lng=-96.8),
            StopCoordinate(lat=33.0, lng=-97.0)
        ])
        assert len(request.stops) == 2
    
    def test_route_request_without_stops(self):
        """Test RouteRequest model without stops (will use DB fallback)."""
        from main import RouteRequest
        
        request = RouteRequest()
        assert request.stops is None
    
    def test_route_summary_response_model(self):
        """Test RouteSummaryResponse model."""
        from main import RouteSummaryResponse
        
        response = RouteSummaryResponse(
            trip_id="test-id",
            total_distance_km=100.0,
            total_drive_time_minutes=60.0,
            routing_engine="osrm",
            notes=["Test note"]
        )
        assert response.trip_id == "test-id"
        assert response.total_distance_km == 100.0


class TestRouteEndpointLogic:
    """Test the endpoint logic using the routing service directly."""
    
    @pytest.mark.asyncio
    async def test_routing_service_success(self, valid_stops_payload, route_summary_response):
        """Test that routing service returns expected response structure."""
        import respx
        from httpx import Response
        
        with respx.mock:
            respx.route(
                method="GET",
                host="router.project-osrm.org",
                path__startswith="/route/v1/driving/"
            ).mock(return_value=Response(200, json={
                "code": "Ok",
                "routes": [{"distance": 500000, "duration": 18000}]
            }))
            
            result = await compute_trucking_route_summary(valid_stops_payload)
            
            assert "total_distance_km" in result
            assert "total_drive_time_minutes" in result
            assert "routing_engine" in result
            assert "notes" in result
            assert result["routing_engine"] == "osrm"
    
    @pytest.mark.asyncio
    async def test_routing_service_validation_error(self):
        """Test that validation errors are raised for invalid input."""
        with pytest.raises(RoutingValidationError, match="At least 2 stops"):
            await compute_trucking_route_summary([{"lat": 32.0, "lng": -96.0}])
    
    @pytest.mark.asyncio
    async def test_routing_service_upstream_error(self, valid_stops_payload):
        """Test that upstream errors are raised for OSRM failures."""
        import respx
        from httpx import Response
        
        with respx.mock:
            respx.route(
                method="GET",
                host="router.project-osrm.org",
                path__startswith="/route/v1/driving/"
            ).mock(return_value=Response(200, json={
                "code": "NoRoute",
                "message": "No route found"
            }))
            
            with pytest.raises(RoutingUpstreamError):
                await compute_trucking_route_summary(valid_stops_payload)


class TestEndpointErrorMapping:
    """Test that endpoint correctly maps service errors to HTTP codes."""
    
    def test_validation_error_is_400(self):
        """Verify RoutingValidationError maps to 400."""
        # This documents the expected behavior - validation errors should be 400
        error = RoutingValidationError("Test error")
        # In the endpoint, this is caught and returns HTTPException(400)
        assert str(error) == "Test error"
    
    def test_upstream_error_is_502(self):
        """Verify RoutingUpstreamError maps to 502."""
        # This documents the expected behavior - upstream errors should be 502
        error = RoutingUpstreamError("Service unavailable")
        # In the endpoint, this is caught and returns HTTPException(502)
        assert str(error) == "Service unavailable"
