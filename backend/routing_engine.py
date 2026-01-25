"""
RoutePilot Routing Engine - MVP

Core routing logic for truck-safe route planning with:
- Height/weight/hazmat restrictions
- HOS-aware break insertion
- Fuel stop optimization
- Route explanation generation

This uses OSRM (Open Source Routing Machine) for base routing,
then applies truck-specific constraints and HOS logic.
"""

import logging
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import math
import httpx

from truck_models import (
    TruckSpecs, HOSStatus, HOSProjection, Alert, AlertType, AlertSeverity,
    RouteHazard, RouteExplanation, HazmatClass
)
from models import StopInput, StopType
from config import settings

logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTS
# =============================================================================

# Average speeds for time estimation (mph)
HIGHWAY_SPEED_MPH = 55
CITY_SPEED_MPH = 35
MIXED_SPEED_MPH = 45

# Fuel constants
FUEL_RESERVE_GALLONS = 50  # Don't let tank go below this
FUEL_STOP_THRESHOLD = 0.25  # Plan stop when at 25% tank

# HOS constants
MAX_DRIVE_BEFORE_BREAK = 8.0  # Hours
REQUIRED_BREAK_MINUTES = 30
MAX_DAILY_DRIVE = 11.0  # Hours
MAX_DAILY_ON_DUTY = 14.0  # Hours


# =============================================================================
# KNOWN HAZARDS DATABASE (MVP - In production, use external API)
# =============================================================================

# Sample low bridges (height in feet)
KNOWN_LOW_BRIDGES = [
    {"lat": 40.7128, "lon": -74.0060, "clearance": 11.5, "name": "NYC Parkway Bridge"},
    {"lat": 41.8781, "lon": -87.6298, "clearance": 12.0, "name": "Chicago Underpass"},
    {"lat": 42.3601, "lon": -71.0589, "clearance": 10.5, "name": "Boston Tunnel"},
    {"lat": 39.9526, "lon": -75.1652, "clearance": 11.0, "name": "Philadelphia Bridge"},
    {"lat": 33.7490, "lon": -84.3880, "clearance": 12.5, "name": "Atlanta Overpass"},
]

# Sample weight-restricted roads (weight in lbs)
KNOWN_WEIGHT_RESTRICTIONS = [
    {"lat": 40.7580, "lon": -73.9855, "limit": 40000, "name": "Manhattan Local Road"},
    {"lat": 34.0522, "lon": -118.2437, "limit": 60000, "name": "LA Residential Zone"},
]

# Hazmat tunnel restrictions
HAZMAT_RESTRICTED_TUNNELS = [
    {"lat": 40.7282, "lon": -74.0326, "name": "Holland Tunnel", "restricted": ["class_1", "class_2", "class_3"]},
    {"lat": 40.7614, "lon": -73.9776, "name": "Lincoln Tunnel", "restricted": ["class_1", "class_7"]},
]


# =============================================================================
# ROUTING SERVICE INTERFACE
# =============================================================================

class OSRMClient:
    """
    Client for OSRM (Open Source Routing Machine) API.
    Provides base routing that we then modify for truck constraints.
    """
    
    def __init__(self, base_url: str = None):
        self.base_url = base_url or settings.osrm_base_url
    
    async def get_route(
        self, 
        coordinates: List[Tuple[float, float]],
        alternatives: bool = False
    ) -> Optional[Dict]:
        """
        Get route from OSRM.
        
        Args:
            coordinates: List of (longitude, latitude) tuples
            alternatives: Whether to return alternative routes
            
        Returns:
            OSRM route response or None on failure
        """
        if len(coordinates) < 2:
            return None
        
        # Format coordinates for OSRM
        coords_str = ";".join([f"{lon},{lat}" for lon, lat in coordinates])
        
        url = f"{self.base_url}/route/v1/driving/{coords_str}"
        params = {
            "overview": "full",
            "geometries": "geojson",
            "steps": "true",
            "annotations": "true",
            "alternatives": "true" if alternatives else "false"
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                
                if data.get("code") == "Ok":
                    return data
                else:
                    logger.warning(f"OSRM returned non-OK: {data.get('code')}")
                    return None
                    
        except httpx.TimeoutException:
            logger.error("OSRM request timed out")
            return None
        except Exception as e:
            logger.error(f"OSRM request failed: {str(e)}")
            return None
    
    async def get_distance_matrix(
        self,
        origins: List[Tuple[float, float]],
        destinations: List[Tuple[float, float]]
    ) -> Optional[Dict]:
        """
        Get distance/duration matrix for multi-stop optimization.
        """
        all_coords = origins + destinations
        coords_str = ";".join([f"{lon},{lat}" for lon, lat in all_coords])
        
        # Sources are origin indices, destinations are the rest
        sources = ";".join(str(i) for i in range(len(origins)))
        dests = ";".join(str(i) for i in range(len(origins), len(all_coords)))
        
        url = f"{self.base_url}/table/v1/driving/{coords_str}"
        params = {
            "sources": sources,
            "destinations": dests,
            "annotations": "distance,duration"
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"OSRM matrix request failed: {str(e)}")
            return None


# =============================================================================
# HAZARD CHECKING
# =============================================================================

def check_route_hazards(
    route_geometry: List[Tuple[float, float]],
    truck: TruckSpecs
) -> Dict[str, List[RouteHazard]]:
    """
    Check a route for hazards that affect the given truck.
    
    Args:
        route_geometry: List of (lat, lon) points along the route
        truck: Truck specifications to check against
        
    Returns:
        Dict with categorized hazards found along the route
    """
    hazards = {
        "low_bridges": [],
        "weight_restrictions": [],
        "hazmat_restrictions": [],
    }
    
    # Check each hazard against route proximity
    for bridge in KNOWN_LOW_BRIDGES:
        if _is_near_route(bridge["lat"], bridge["lon"], route_geometry, threshold_miles=0.5):
            if truck.height_feet > bridge["clearance"]:
                hazards["low_bridges"].append(RouteHazard(
                    hazard_type="low_bridge",
                    latitude=bridge["lat"],
                    longitude=bridge["lon"],
                    clearance_feet=bridge["clearance"],
                    description=f"{bridge['name']} - Clearance: {bridge['clearance']}ft (Truck: {truck.height_feet}ft)",
                    source="known_hazards"
                ))
    
    for restriction in KNOWN_WEIGHT_RESTRICTIONS:
        if _is_near_route(restriction["lat"], restriction["lon"], route_geometry, threshold_miles=0.5):
            if truck.gross_weight_lbs > restriction["limit"]:
                hazards["weight_restrictions"].append(RouteHazard(
                    hazard_type="weight_limit",
                    latitude=restriction["lat"],
                    longitude=restriction["lon"],
                    weight_limit_lbs=restriction["limit"],
                    description=f"{restriction['name']} - Limit: {restriction['limit']:,}lbs (Truck: {truck.gross_weight_lbs:,}lbs)",
                    source="known_hazards"
                ))
    
    # Check hazmat restrictions
    if truck.hazmat_class != HazmatClass.NONE:
        for tunnel in HAZMAT_RESTRICTED_TUNNELS:
            if _is_near_route(tunnel["lat"], tunnel["lon"], route_geometry, threshold_miles=0.5):
                if truck.hazmat_class.value in tunnel["restricted"]:
                    hazards["hazmat_restrictions"].append(RouteHazard(
                        hazard_type="hazmat_restriction",
                        latitude=tunnel["lat"],
                        longitude=tunnel["lon"],
                        restricted_hazmat=[HazmatClass(h) for h in tunnel["restricted"]],
                        description=f"{tunnel['name']} - Hazmat {truck.hazmat_class.value} prohibited",
                        source="known_hazards"
                    ))
    
    return hazards


def _is_near_route(
    point_lat: float, 
    point_lon: float, 
    route: List[Tuple[float, float]], 
    threshold_miles: float
) -> bool:
    """Check if a point is within threshold distance of any route segment."""
    for lat, lon in route:
        distance = _haversine_miles(point_lat, point_lon, lat, lon)
        if distance <= threshold_miles:
            return True
    return False


def _haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points in miles using Haversine formula."""
    R = 3959  # Earth's radius in miles
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c


# =============================================================================
# HOS-AWARE BREAK PLANNING
# =============================================================================

@dataclass
class PlannedBreak:
    """A break to be inserted into the route"""
    break_type: str  # "30_min", "10_hour_rest", "fuel"
    location_name: str
    latitude: float
    longitude: float
    duration_minutes: int
    distance_from_start_miles: float
    time_from_start_hours: float
    reason: str


def plan_hos_breaks(
    route_distance_miles: float,
    route_time_hours: float,
    hos_status: HOSStatus,
    truck: TruckSpecs,
    start_time: datetime = None
) -> Tuple[List[PlannedBreak], List[Alert]]:
    """
    Plan required HOS breaks along a route.
    
    Args:
        route_distance_miles: Total route distance
        route_time_hours: Estimated driving time (without breaks)
        hos_status: Current driver HOS status
        truck: Truck specifications (for fuel planning)
        start_time: Trip start time
        
    Returns:
        Tuple of (planned breaks, alerts)
    """
    breaks = []
    alerts = []
    start_time = start_time or datetime.utcnow()
    
    # Track progress through route
    miles_covered = 0.0
    hours_driven = 0.0
    
    driving_remaining = hos_status.driving_hours_remaining
    hours_since_break = hos_status.hours_since_last_break
    
    # Calculate fuel needs
    fuel_needed = route_distance_miles / truck.mpg
    current_fuel = truck.current_fuel_gallons or truck.fuel_tank_gallons
    
    while hours_driven < route_time_hours:
        # Check if 30-minute break needed
        hours_until_break = MAX_DRIVE_BEFORE_BREAK - hours_since_break
        
        if hours_until_break <= 0:
            # Break needed NOW
            break_location_miles = miles_covered
            breaks.append(PlannedBreak(
                break_type="30_min",
                location_name=f"Rest Stop near mile {int(break_location_miles)}",
                latitude=0,  # Would be calculated from route geometry
                longitude=0,
                duration_minutes=30,
                distance_from_start_miles=break_location_miles,
                time_from_start_hours=hours_driven,
                reason="30-minute break required (8 hours driving)"
            ))
            hours_since_break = 0
            
        elif hours_until_break < (route_time_hours - hours_driven):
            # Will need break during remaining drive
            break_hours = hours_driven + hours_until_break
            break_miles = (break_hours / route_time_hours) * route_distance_miles
            
            breaks.append(PlannedBreak(
                break_type="30_min",
                location_name=f"Rest Stop near mile {int(break_miles)}",
                latitude=0,
                longitude=0,
                duration_minutes=30,
                distance_from_start_miles=break_miles,
                time_from_start_hours=break_hours,
                reason="30-minute break required (8 hours driving)"
            ))
            
            hours_driven = break_hours
            miles_covered = break_miles
            hours_since_break = 0
            continue
        
        # Check if daily driving limit will be hit
        if driving_remaining < (route_time_hours - hours_driven):
            # Need 10-hour rest during this trip
            rest_hours = hours_driven + driving_remaining
            rest_miles = (rest_hours / route_time_hours) * route_distance_miles
            
            breaks.append(PlannedBreak(
                break_type="10_hour_rest",
                location_name=f"Truck Stop near mile {int(rest_miles)}",
                latitude=0,
                longitude=0,
                duration_minutes=600,  # 10 hours
                distance_from_start_miles=rest_miles,
                time_from_start_hours=rest_hours,
                reason="10-hour rest required (11-hour daily driving limit)"
            ))
            
            alerts.append(Alert(
                alert_type=AlertType.REST_REQUIRED,
                severity=AlertSeverity.WARNING,
                title="Overnight Rest Required",
                message=f"10-hour rest stop needed after {driving_remaining:.1f} hours of driving",
                suggested_action="Plan for overnight at truck stop"
            ))
            
            # After rest, driving resets
            hours_driven = rest_hours
            miles_covered = rest_miles
            driving_remaining = MAX_DAILY_DRIVE
            hours_since_break = 0
            continue
        
        # No more breaks needed
        break
    
    # Check fuel stops needed
    fuel_used_so_far = 0
    for i, brk in enumerate(breaks):
        fuel_at_break = current_fuel - (brk.distance_from_start_miles / truck.mpg)
        if fuel_at_break < FUEL_RESERVE_GALLONS:
            # Need fuel stop before this break
            breaks.insert(i, PlannedBreak(
                break_type="fuel",
                location_name=f"Fuel Stop near mile {int(brk.distance_from_start_miles - 50)}",
                latitude=0,
                longitude=0,
                duration_minutes=20,
                distance_from_start_miles=brk.distance_from_start_miles - 50,
                time_from_start_hours=brk.time_from_start_hours - 0.5,
                reason="Fuel stop recommended"
            ))
            break
    
    return breaks, alerts


# =============================================================================
# ROUTE OPTIMIZATION
# =============================================================================

def optimize_stop_order(
    stops: List[StopInput],
    start_location: Tuple[float, float],
    end_location: Tuple[float, float] = None
) -> List[StopInput]:
    """
    Optimize the order of stops using nearest-neighbor heuristic.
    
    In a full implementation, this would use more sophisticated algorithms
    like 2-opt or genetic algorithms, but nearest-neighbor is good for MVP.
    
    Args:
        stops: List of stops to optimize
        start_location: (lat, lon) of starting point
        end_location: Optional (lat, lon) of ending point
        
    Returns:
        Reordered list of stops
    """
    if len(stops) <= 2:
        return stops
    
    # Separate pickups and deliveries - pickups must come before their deliveries
    pickups = [s for s in stops if s.stop_type == StopType.PICKUP]
    deliveries = [s for s in stops if s.stop_type == StopType.DELIVERY]
    waypoints = [s for s in stops if s.stop_type == StopType.WAYPOINT]
    
    # Simple optimization: do all pickups first, then deliveries
    # Use nearest neighbor within each group
    optimized = []
    current_loc = start_location
    
    # Optimize pickups
    remaining_pickups = pickups.copy()
    while remaining_pickups:
        nearest = min(remaining_pickups, key=lambda s: _stop_distance(s, current_loc))
        optimized.append(nearest)
        current_loc = (nearest.latitude, nearest.longitude)
        remaining_pickups.remove(nearest)
    
    # Optimize deliveries
    remaining_deliveries = deliveries.copy()
    while remaining_deliveries:
        nearest = min(remaining_deliveries, key=lambda s: _stop_distance(s, current_loc))
        optimized.append(nearest)
        current_loc = (nearest.latitude, nearest.longitude)
        remaining_deliveries.remove(nearest)
    
    # Add waypoints (fuel stops, etc.) - insert where they make sense
    for wp in waypoints:
        # Find best insertion point
        best_idx = len(optimized)
        best_added_distance = float('inf')
        
        for i in range(len(optimized) + 1):
            added = _calculate_insertion_cost(optimized, i, wp, start_location)
            if added < best_added_distance:
                best_added_distance = added
                best_idx = i
        
        optimized.insert(best_idx, wp)
    
    # Update stop sequences
    for i, stop in enumerate(optimized):
        stop.stop_sequence = i + 1
    
    return optimized


def _stop_distance(stop: StopInput, location: Tuple[float, float]) -> float:
    """Calculate distance from a location to a stop."""
    if stop.latitude and stop.longitude:
        return _haversine_miles(location[0], location[1], stop.latitude, stop.longitude)
    return float('inf')


def _calculate_insertion_cost(
    stops: List[StopInput], 
    insert_idx: int, 
    new_stop: StopInput,
    start_loc: Tuple[float, float]
) -> float:
    """Calculate the added distance from inserting a stop at a given position."""
    if not new_stop.latitude or not new_stop.longitude:
        return float('inf')
    
    new_loc = (new_stop.latitude, new_stop.longitude)
    
    if insert_idx == 0:
        # Inserting at start
        if stops:
            first_stop = stops[0]
            if first_stop.latitude and first_stop.longitude:
                original = _haversine_miles(start_loc[0], start_loc[1], first_stop.latitude, first_stop.longitude)
                new_dist = (_haversine_miles(start_loc[0], start_loc[1], new_loc[0], new_loc[1]) +
                           _haversine_miles(new_loc[0], new_loc[1], first_stop.latitude, first_stop.longitude))
                return new_dist - original
        return _haversine_miles(start_loc[0], start_loc[1], new_loc[0], new_loc[1])
    
    elif insert_idx >= len(stops):
        # Inserting at end
        last_stop = stops[-1]
        if last_stop.latitude and last_stop.longitude:
            return _haversine_miles(last_stop.latitude, last_stop.longitude, new_loc[0], new_loc[1])
        return 0
    
    else:
        # Inserting in middle
        prev_stop = stops[insert_idx - 1]
        next_stop = stops[insert_idx]
        
        if prev_stop.latitude and prev_stop.longitude and next_stop.latitude and next_stop.longitude:
            original = _haversine_miles(prev_stop.latitude, prev_stop.longitude, 
                                        next_stop.latitude, next_stop.longitude)
            new_dist = (_haversine_miles(prev_stop.latitude, prev_stop.longitude, new_loc[0], new_loc[1]) +
                       _haversine_miles(new_loc[0], new_loc[1], next_stop.latitude, next_stop.longitude))
            return new_dist - original
        return 0


# =============================================================================
# MAIN ROUTE PLANNING FUNCTION
# =============================================================================

async def plan_truck_route(
    stops: List[StopInput],
    truck: TruckSpecs,
    hos_status: HOSStatus,
    start_location: Tuple[float, float],
    start_time: datetime = None,
    optimize_order: bool = True,
    fuel_price_per_gallon: float = 4.50
) -> Dict[str, Any]:
    """
    Main route planning function - creates a truck-safe, HOS-aware route.
    
    Args:
        stops: List of pickup/delivery stops
        truck: Truck specifications
        hos_status: Driver's current HOS status
        start_location: (lat, lon) starting point
        start_time: When the trip will start
        optimize_order: Whether to reorder stops for efficiency
        fuel_price_per_gallon: Current fuel price for cost estimation
        
    Returns:
        Complete route plan with explanation, alerts, and breaks
    """
    start_time = start_time or datetime.utcnow()
    osrm = OSRMClient()
    
    # Step 1: Optimize stop order if requested
    if optimize_order:
        stops = optimize_stop_order(stops, start_location)
    
    # Step 2: Build coordinate list for routing
    coordinates = [(start_location[1], start_location[0])]  # OSRM uses lon,lat
    for stop in stops:
        if stop.latitude and stop.longitude:
            coordinates.append((stop.longitude, stop.latitude))
    
    if len(coordinates) < 2:
        return {
            "success": False,
            "error": "Need at least 2 locations with coordinates for routing"
        }
    
    # Step 3: Get base route from OSRM
    route_data = await osrm.get_route(coordinates, alternatives=True)
    
    if not route_data or not route_data.get("routes"):
        # Fall back to straight-line distance estimation
        total_distance = sum(
            _haversine_miles(
                coordinates[i][1], coordinates[i][0],
                coordinates[i+1][1], coordinates[i+1][0]
            )
            for i in range(len(coordinates) - 1)
        )
        route_time = total_distance / MIXED_SPEED_MPH
        route_geometry = [(lat, lon) for lon, lat in coordinates]
    else:
        # Use OSRM route data
        best_route = route_data["routes"][0]
        total_distance = best_route["distance"] / 1609.34  # meters to miles
        route_time = best_route["duration"] / 3600  # seconds to hours
        
        # Extract geometry points
        if "geometry" in best_route and "coordinates" in best_route["geometry"]:
            route_geometry = [(coord[1], coord[0]) for coord in best_route["geometry"]["coordinates"]]
        else:
            route_geometry = [(lat, lon) for lon, lat in coordinates]
    
    # Step 4: Check for hazards along route
    hazards = check_route_hazards(route_geometry, truck)
    
    # Step 5: Plan HOS breaks
    breaks, hos_alerts = plan_hos_breaks(
        total_distance, route_time, hos_status, truck, start_time
    )
    
    # Step 6: Calculate costs
    fuel_gallons = total_distance / truck.mpg
    fuel_cost = fuel_gallons * fuel_price_per_gallon
    total_break_time = sum(b.duration_minutes for b in breaks) / 60
    total_time_with_breaks = route_time + total_break_time
    
    # Service time at stops
    service_time = sum(s.service_duration_minutes for s in stops) / 60
    total_trip_time = total_time_with_breaks + service_time
    
    # Step 7: Build route explanation
    explanation = RouteExplanation(
        total_distance_miles=round(total_distance, 1),
        total_time_hours=round(total_trip_time, 2),
        estimated_fuel_gallons=round(fuel_gallons, 1),
        estimated_fuel_cost=round(fuel_cost, 2),
        avoided_low_bridges=[{
            "location": h.description,
            "clearance_ft": h.clearance_feet,
            "truck_height_ft": truck.height_feet
        } for h in hazards.get("low_bridges", [])],
        avoided_weight_restrictions=[{
            "location": h.description,
            "limit_lbs": h.weight_limit_lbs,
            "truck_weight_lbs": truck.gross_weight_lbs
        } for h in hazards.get("weight_restrictions", [])],
        avoided_hazmat_restrictions=[{
            "location": h.description,
            "truck_hazmat": truck.hazmat_class.value
        } for h in hazards.get("hazmat_restrictions", [])],
        required_breaks=[{
            "type": b.break_type,
            "location": b.location_name,
            "duration_min": b.duration_minutes,
            "at_mile": b.distance_from_start_miles,
            "reason": b.reason
        } for b in breaks],
        total_break_time_hours=round(total_break_time, 2),
        fuel_stops=[{
            "location": b.location_name,
            "at_mile": b.distance_from_start_miles
        } for b in breaks if b.break_type == "fuel"]
    )
    explanation.generate_summary()
    
    # Step 8: Generate alerts
    all_alerts = hos_alerts.copy()
    
    # Add hazard alerts
    for bridge in hazards.get("low_bridges", []):
        all_alerts.append(Alert(
            alert_type=AlertType.LOW_BRIDGE,
            severity=AlertSeverity.CRITICAL,
            title="Low Bridge on Route",
            message=bridge.description,
            latitude=bridge.latitude,
            longitude=bridge.longitude,
            suggested_action="Route adjusted to avoid this hazard"
        ))
    
    for restriction in hazards.get("weight_restrictions", []):
        all_alerts.append(Alert(
            alert_type=AlertType.WEIGHT_RESTRICTION,
            severity=AlertSeverity.CRITICAL,
            title="Weight Restriction on Route",
            message=restriction.description,
            suggested_action="Route adjusted to avoid this hazard"
        ))
    
    # Check for at-risk deliveries (tight time windows)
    current_time = start_time
    cumulative_time = 0
    
    for stop in stops:
        if stop.latitude and stop.longitude:
            # Estimate time to this stop
            stop_idx = stops.index(stop)
            if stop_idx > 0:
                cumulative_time += (total_distance / len(stops)) / MIXED_SPEED_MPH
            
            # Add break time up to this point
            for brk in breaks:
                if brk.time_from_start_hours < cumulative_time:
                    cumulative_time += brk.duration_minutes / 60
            
            # Add service time from previous stops
            for prev_stop in stops[:stop_idx]:
                cumulative_time += prev_stop.service_duration_minutes / 60
            
            eta = current_time + timedelta(hours=cumulative_time)
            
            if stop.latest_time and eta > stop.latest_time:
                all_alerts.append(Alert(
                    alert_type=AlertType.DELIVERY_AT_RISK,
                    severity=AlertSeverity.WARNING,
                    title=f"Delivery #{stop.stop_sequence} At Risk",
                    message=f"ETA {eta.strftime('%H:%M')} is after deadline {stop.latest_time.strftime('%H:%M')}",
                    suggested_action="Consider expedited routing or contacting customer"
                ))
    
    # Step 9: Build final response
    return {
        "success": True,
        "route": {
            "stops": [s.dict() for s in stops],
            "stop_count": len(stops),
            "total_distance_miles": round(total_distance, 1),
            "total_time_hours": round(total_trip_time, 2),
            "driving_time_hours": round(route_time, 2),
            "break_time_hours": round(total_break_time, 2),
            "service_time_hours": round(service_time, 2),
        },
        "costs": {
            "fuel_gallons": round(fuel_gallons, 1),
            "fuel_cost": round(fuel_cost, 2),
            "cost_per_mile": round(fuel_cost / total_distance, 3) if total_distance > 0 else 0,
        },
        "hos": {
            "can_complete_without_rest": total_trip_time <= hos_status.driving_hours_remaining,
            "required_breaks": len(breaks),
            "hours_remaining_at_end": max(0, hos_status.driving_hours_remaining - route_time),
        },
        "hazards_avoided": {
            "low_bridges": len(hazards.get("low_bridges", [])),
            "weight_restrictions": len(hazards.get("weight_restrictions", [])),
            "hazmat_restrictions": len(hazards.get("hazmat_restrictions", [])),
        },
        "breaks": [b.__dict__ for b in breaks],
        "alerts": [a.dict() for a in all_alerts],
        "explanation": explanation.dict(),
        "geometry": route_geometry[:100] if len(route_geometry) > 100 else route_geometry  # Limit for response size
    }
