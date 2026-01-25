"""
Routing service module for computing trucking route summaries.

This module provides a stable interface for route calculations that can be
swapped for a truck-aware routing engine later without changing callers.

Current implementation: OSRM public API (driving profile)
Future: Commercial truck-routing API with vehicle constraints
"""

import logging
import math
from typing import Any

import httpx

from config import settings

logger = logging.getLogger(__name__)

# Constants
OSRM_TIMEOUT_SECONDS = 8.0
METERS_PER_KM = 1000.0
SECONDS_PER_MINUTE = 60.0


class RoutingError(Exception):
    """Base exception for routing service errors."""
    pass


class RoutingValidationError(RoutingError):
    """Raised when input validation fails."""
    pass


class RoutingUpstreamError(RoutingError):
    """Raised when upstream routing service fails."""
    pass


def _validate_stops(stops: list[dict]) -> None:
    """
    Validate stops input for routing calculation.
    
    Args:
        stops: List of stop dictionaries with lat/lng coordinates
        
    Raises:
        RoutingValidationError: If validation fails
    """
    if not stops or len(stops) < 2:
        raise RoutingValidationError("At least 2 stops are required for route calculation")
    
    for idx, stop in enumerate(stops):
        lat = stop.get("lat") or stop.get("latitude")
        lng = stop.get("lng") or stop.get("longitude")
        
        # Check for missing coordinates
        if lat is None or lng is None:
            raise RoutingValidationError(
                f"Stop {idx + 1} missing required coordinates (lat/lng)"
            )
        
        # Check for valid numeric values (not NaN)
        try:
            lat_f = float(lat)
            lng_f = float(lng)
            if math.isnan(lat_f) or math.isnan(lng_f):
                raise RoutingValidationError(
                    f"Stop {idx + 1} has invalid coordinates (NaN)"
                )
            # Validate coordinate ranges
            if not (-90 <= lat_f <= 90):
                raise RoutingValidationError(
                    f"Stop {idx + 1} latitude {lat_f} out of range (-90 to 90)"
                )
            if not (-180 <= lng_f <= 180):
                raise RoutingValidationError(
                    f"Stop {idx + 1} longitude {lng_f} out of range (-180 to 180)"
                )
        except (TypeError, ValueError) as e:
            raise RoutingValidationError(
                f"Stop {idx + 1} has non-numeric coordinates"
            ) from e


def _build_osrm_coords_string(stops: list[dict]) -> str:
    """
    Build OSRM coordinates string from stops.
    
    OSRM format: "lng,lat;lng,lat;..."
    
    Args:
        stops: List of stop dictionaries with lat/lng coordinates
        
    Returns:
        Coordinates string in OSRM format
    """
    coords_parts = []
    for stop in stops:
        lat = stop.get("lat") or stop.get("latitude")
        lng = stop.get("lng") or stop.get("longitude")
        coords_parts.append(f"{float(lng)},{float(lat)}")
    return ";".join(coords_parts)


def _meters_to_km(meters: float) -> float:
    """Convert meters to kilometers, rounded to 2 decimal places."""
    return round(meters / METERS_PER_KM, 2)


def _seconds_to_minutes(seconds: float) -> float:
    """Convert seconds to minutes, rounded to 1 decimal place."""
    return round(seconds / SECONDS_PER_MINUTE, 1)


async def compute_trucking_route_summary(stops: list[dict]) -> dict[str, Any]:
    """
    Compute a trucking route summary for the given ordered stops.
    
    This is the stable interface for route calculations. Current implementation
    uses OSRM public API with driving profile. The interface is designed to allow
    future swap to a truck-aware routing engine without changing callers.
    
    Args:
        stops: Ordered list of stops, each containing:
            - lat (or latitude): float - WGS84 latitude
            - lng (or longitude): float - WGS84 longitude
            - ... other fields are ignored
    
    Returns:
        dict with:
            - total_distance_km: float
            - total_drive_time_minutes: float
            - routing_engine: str
            - notes: list[str] - Important disclaimers and caveats
    
    Raises:
        RoutingValidationError: If input validation fails (400-level)
        RoutingUpstreamError: If routing service fails (502-level)
    """
    # Validate input
    _validate_stops(stops)
    
    # Build OSRM request
    coords_str = _build_osrm_coords_string(stops)
    osrm_base_url = settings.osrm_base_url.rstrip("/")
    url = f"{osrm_base_url}/route/v1/driving/{coords_str}"
    
    params = {
        "overview": "false",
        "steps": "false",
        "annotations": "false"
    }
    
    # Make request with strict timeout
    try:
        async with httpx.AsyncClient(timeout=OSRM_TIMEOUT_SECONDS) as client:
            response = await client.get(url, params=params)
    except httpx.TimeoutException:
        logger.error("OSRM request timed out after %s seconds", OSRM_TIMEOUT_SECONDS)
        raise RoutingUpstreamError("Routing service timed out. Please try again.")
    except httpx.RequestError as e:
        logger.error("OSRM request failed: %s", type(e).__name__)
        raise RoutingUpstreamError("Routing service unavailable. Please try again later.")
    
    # Check HTTP status
    if response.status_code != 200:
        logger.error("OSRM returned HTTP %s", response.status_code)
        raise RoutingUpstreamError(
            f"Routing service error (HTTP {response.status_code}). Please try again later."
        )
    
    # Parse response
    try:
        data = response.json()
    except Exception:
        logger.error("OSRM returned invalid JSON")
        raise RoutingUpstreamError("Routing service returned invalid response.")
    
    # Validate OSRM response
    osrm_code = data.get("code")
    if osrm_code != "Ok":
        osrm_message = data.get("message", "Unknown error")
        logger.error("OSRM returned code=%s, message=%s", osrm_code, osrm_message)
        raise RoutingUpstreamError(
            f"Could not calculate route: {osrm_message}"
        )
    
    routes = data.get("routes", [])
    if not routes:
        logger.error("OSRM returned no routes")
        raise RoutingUpstreamError("No route found between the specified stops.")
    
    # Extract route summary
    route = routes[0]
    distance_meters = route.get("distance", 0)
    duration_seconds = route.get("duration", 0)
    
    return {
        "total_distance_km": _meters_to_km(distance_meters),
        "total_drive_time_minutes": _seconds_to_minutes(duration_seconds),
        "routing_engine": "osrm",
        "notes": [
            "Route is an estimate and may not account for truck restrictions (height/weight/hazmat).",
            "Actual drive times may vary based on traffic, weather, and road conditions."
        ]
    }
