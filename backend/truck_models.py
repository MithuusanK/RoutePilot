"""
Truck Specifications & HOS Models for RoutePilot MVP

This module defines truck-specific constraints and Hours of Service (HOS) 
tracking for safe 18-wheeler routing.
"""

from pydantic import BaseModel, Field, validator
from enum import Enum
from datetime import datetime, timedelta
from typing import Optional, List
from uuid import UUID, uuid4


# =============================================================================
# ENUMS - Truck & Cargo Types
# =============================================================================

class TruckType(str, Enum):
    """Common 18-wheeler truck configurations"""
    SEMI_TRAILER = "semi_trailer"           # Standard 53' trailer
    TANKER = "tanker"                       # Liquid cargo
    FLATBED = "flatbed"                     # Open cargo
    REFRIGERATED = "refrigerated"           # Reefer truck
    DRY_VAN = "dry_van"                     # Enclosed cargo
    LOWBOY = "lowboy"                       # Heavy equipment
    CAR_CARRIER = "car_carrier"             # Vehicle transport
    CONTAINER = "container"                 # Intermodal container


class HazmatClass(str, Enum):
    """DOT Hazmat Classifications"""
    NONE = "none"
    CLASS_1_EXPLOSIVES = "class_1"
    CLASS_2_GASES = "class_2"
    CLASS_3_FLAMMABLE = "class_3"
    CLASS_4_FLAMMABLE_SOLIDS = "class_4"
    CLASS_5_OXIDIZERS = "class_5"
    CLASS_6_POISONS = "class_6"
    CLASS_7_RADIOACTIVE = "class_7"
    CLASS_8_CORROSIVE = "class_8"
    CLASS_9_MISC = "class_9"


class DriverStatus(str, Enum):
    """Current driver duty status per HOS regulations"""
    OFF_DUTY = "off_duty"
    SLEEPER_BERTH = "sleeper_berth"
    DRIVING = "driving"
    ON_DUTY_NOT_DRIVING = "on_duty_not_driving"


class AlertSeverity(str, Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertType(str, Enum):
    """Types of alerts for drivers and fleet managers"""
    HOS_WARNING = "hos_warning"
    HOS_VIOLATION_RISK = "hos_violation_risk"
    LOW_BRIDGE = "low_bridge"
    WEIGHT_RESTRICTION = "weight_restriction"
    HAZMAT_RESTRICTION = "hazmat_restriction"
    WEATHER = "weather"
    TRAFFIC = "traffic"
    ROAD_CLOSURE = "road_closure"
    FUEL_LOW = "fuel_low"
    REST_REQUIRED = "rest_required"
    DELIVERY_AT_RISK = "delivery_at_risk"


# =============================================================================
# TRUCK SPECIFICATIONS
# =============================================================================

class TruckSpecs(BaseModel):
    """
    Truck physical specifications for route planning.
    These constraints determine which roads/bridges/tunnels are safe.
    """
    
    id: UUID = Field(default_factory=uuid4)
    
    # Basic truck info
    truck_id: str = Field(..., description="Fleet truck identifier (e.g., TRUCK-001)")
    truck_type: TruckType = Field(default=TruckType.DRY_VAN)
    
    # Physical dimensions (used for bridge/tunnel clearance)
    height_feet: float = Field(
        default=13.5,
        ge=8.0,
        le=14.5,
        description="Total height in feet (standard max is 13.5')"
    )
    width_feet: float = Field(
        default=8.5,
        ge=6.0,
        le=10.0,
        description="Total width in feet (standard max is 8.5')"
    )
    length_feet: float = Field(
        default=53.0,
        ge=28.0,
        le=80.0,
        description="Total length in feet (tractor + trailer)"
    )
    
    # Weight specifications (affects bridge ratings & road restrictions)
    gross_weight_lbs: int = Field(
        default=80000,
        ge=10000,
        le=105500,
        description="Gross vehicle weight in pounds"
    )
    axle_count: int = Field(
        default=5,
        ge=2,
        le=9,
        description="Number of axles"
    )
    axle_weight_lbs: Optional[int] = Field(
        default=None,
        description="Single axle weight limit (lbs)"
    )
    
    # Fuel & range
    fuel_tank_gallons: float = Field(
        default=300.0,
        ge=50.0,
        le=500.0,
        description="Total fuel capacity in gallons"
    )
    mpg: float = Field(
        default=6.5,
        ge=3.0,
        le=12.0,
        description="Average miles per gallon"
    )
    current_fuel_gallons: Optional[float] = Field(
        default=None,
        description="Current fuel level (for fuel stop planning)"
    )
    
    # Special restrictions
    hazmat_class: HazmatClass = Field(
        default=HazmatClass.NONE,
        description="Hazmat classification (affects tunnel/road access)"
    )
    requires_oversize_permit: bool = Field(
        default=False,
        description="Requires oversize/overweight permit"
    )
    
    @property
    def estimated_range_miles(self) -> float:
        """Calculate estimated range based on fuel and MPG"""
        fuel = self.current_fuel_gallons or self.fuel_tank_gallons
        return fuel * self.mpg
    
    @validator('current_fuel_gallons')
    def fuel_within_tank(cls, v, values):
        if v is not None and 'fuel_tank_gallons' in values:
            if v > values['fuel_tank_gallons']:
                raise ValueError('Current fuel cannot exceed tank capacity')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "truck_id": "TRUCK-001",
                "truck_type": "dry_van",
                "height_feet": 13.5,
                "width_feet": 8.5,
                "length_feet": 53.0,
                "gross_weight_lbs": 76000,
                "axle_count": 5,
                "fuel_tank_gallons": 300,
                "mpg": 6.5,
                "hazmat_class": "none"
            }
        }


# =============================================================================
# HOS (HOURS OF SERVICE) TRACKING
# =============================================================================

class HOSStatus(BaseModel):
    """
    Current Hours of Service status for a driver.
    Based on FMCSA regulations for property-carrying drivers.
    
    Key Rules:
    - 11-hour driving limit after 10 consecutive hours off duty
    - 14-hour on-duty window after 10 consecutive hours off duty
    - 30-minute break required after 8 hours driving
    - 60/70 hour limit over 7/8 days
    - 34-hour restart option
    """
    
    driver_id: str = Field(..., description="Driver identifier")
    
    # Current status
    current_status: DriverStatus = Field(default=DriverStatus.OFF_DUTY)
    status_start_time: datetime = Field(default_factory=datetime.utcnow)
    
    # Today's limits (reset after 10-hour break)
    driving_hours_remaining: float = Field(
        default=11.0,
        ge=0.0,
        le=11.0,
        description="Hours of driving remaining in current shift"
    )
    on_duty_hours_remaining: float = Field(
        default=14.0,
        ge=0.0,
        le=14.0,
        description="Hours remaining in 14-hour on-duty window"
    )
    
    # 30-minute break tracking
    hours_since_last_break: float = Field(
        default=0.0,
        ge=0.0,
        description="Hours driven since last 30-min break"
    )
    break_required: bool = Field(
        default=False,
        description="True if 30-min break is required before continuing"
    )
    
    # Weekly limits (7 or 8 day cycle)
    cycle_hours_used: float = Field(
        default=0.0,
        ge=0.0,
        description="Total on-duty hours used in current 7/8-day cycle"
    )
    cycle_hours_remaining: float = Field(
        default=70.0,
        ge=0.0,
        le=70.0,
        description="Hours remaining in 60/70-hour cycle"
    )
    cycle_type: int = Field(
        default=8,
        ge=7,
        le=8,
        description="7-day (60hr) or 8-day (70hr) cycle"
    )
    
    # Timestamps
    last_rest_start: Optional[datetime] = Field(
        default=None,
        description="When last 10-hour rest period started"
    )
    last_rest_end: Optional[datetime] = Field(
        default=None,
        description="When last 10-hour rest period ended"
    )
    
    @property
    def can_drive(self) -> bool:
        """Check if driver can legally drive right now"""
        return (
            self.driving_hours_remaining > 0 and
            self.on_duty_hours_remaining > 0 and
            self.cycle_hours_remaining > 0 and
            not self.break_required
        )
    
    @property
    def max_drive_time_hours(self) -> float:
        """Maximum hours driver can drive before a stop is required"""
        return min(
            self.driving_hours_remaining,
            self.on_duty_hours_remaining,
            self.cycle_hours_remaining,
            8.0 - self.hours_since_last_break if not self.break_required else 0
        )
    
    def calculate_required_break(self, driving_hours_planned: float) -> Optional[dict]:
        """
        Determine if and when a break is needed for planned driving time.
        
        Returns dict with break timing and type, or None if no break needed.
        """
        if self.break_required:
            return {
                "break_type": "30_min_mandatory",
                "needed_before_miles": 0,
                "reason": "30-minute break required before driving"
            }
        
        hours_until_break = 8.0 - self.hours_since_last_break
        
        if driving_hours_planned > hours_until_break:
            return {
                "break_type": "30_min_mandatory",
                "needed_after_hours": hours_until_break,
                "reason": f"30-minute break required after {hours_until_break:.1f} hours of driving"
            }
        
        if driving_hours_planned > self.driving_hours_remaining:
            return {
                "break_type": "10_hour_rest",
                "needed_after_hours": self.driving_hours_remaining,
                "reason": "10-hour rest required - daily driving limit reached"
            }
        
        return None


class HOSProjection(BaseModel):
    """Projected HOS status at a future point in time"""
    
    checkpoint_time: datetime
    checkpoint_location: str
    
    # Projected remaining hours at this point
    projected_driving_remaining: float
    projected_on_duty_remaining: float
    
    # Warnings
    will_require_break: bool = False
    break_recommended_at: Optional[str] = None
    
    # Risk flags
    violation_risk: bool = False
    violation_type: Optional[str] = None


# =============================================================================
# ALERTS
# =============================================================================

class Alert(BaseModel):
    """
    Alert/notification for drivers and fleet managers.
    Used for HOS warnings, hazards, weather, traffic, etc.
    """
    
    id: UUID = Field(default_factory=uuid4)
    alert_type: AlertType
    severity: AlertSeverity
    
    title: str = Field(..., max_length=100)
    message: str = Field(..., max_length=500)
    
    # Location context (optional)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    location_name: Optional[str] = None
    
    # Related entities
    trip_id: Optional[UUID] = None
    driver_id: Optional[str] = None
    stop_id: Optional[UUID] = None
    
    # Timing
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    acknowledged: bool = False
    acknowledged_at: Optional[datetime] = None
    
    # Action suggestions
    suggested_action: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "alert_type": "hos_warning",
                "severity": "warning",
                "title": "Break Required Soon",
                "message": "You will need a 30-minute break in 45 minutes based on current pace.",
                "suggested_action": "Look for rest area near mile marker 156"
            }
        }


# =============================================================================
# ROUTE HAZARDS & RESTRICTIONS
# =============================================================================

class RouteHazard(BaseModel):
    """
    Hazard or restriction along a route that trucks must avoid.
    """
    
    hazard_type: str = Field(..., description="Type: low_bridge, weight_limit, etc.")
    latitude: float
    longitude: float
    
    # Restriction details
    clearance_feet: Optional[float] = None  # For bridges/tunnels
    weight_limit_lbs: Optional[int] = None  # For weight restrictions
    restricted_hazmat: List[HazmatClass] = []  # For hazmat restrictions
    
    # Metadata
    description: str
    source: str = "user_reported"  # osm, dot, user_reported
    verified: bool = False
    
    # Timestamps
    reported_at: datetime = Field(default_factory=datetime.utcnow)
    last_verified: Optional[datetime] = None


class RouteExplanation(BaseModel):
    """
    Explains WHY a particular route was chosen.
    Shows avoided hazards and trade-offs made.
    """
    
    # Route summary
    total_distance_miles: float
    total_time_hours: float
    estimated_fuel_gallons: float
    estimated_fuel_cost: float
    
    # Hazards avoided
    avoided_low_bridges: List[dict] = []
    avoided_weight_restrictions: List[dict] = []
    avoided_hazmat_restrictions: List[dict] = []
    avoided_tight_turns: List[dict] = []
    
    # Trade-offs
    distance_added_for_safety: float = 0.0  # Extra miles vs shortest route
    time_added_for_safety: float = 0.0      # Extra time vs fastest route
    
    # HOS impact
    required_breaks: List[dict] = []
    total_break_time_hours: float = 0.0
    
    # Fuel stops recommended
    fuel_stops: List[dict] = []
    
    # Explanation text for display
    summary: str = ""
    
    def generate_summary(self) -> str:
        """Generate human-readable route explanation"""
        parts = []
        
        if self.avoided_low_bridges:
            parts.append(f"Avoided {len(self.avoided_low_bridges)} low bridges")
        if self.avoided_weight_restrictions:
            parts.append(f"Avoided {len(self.avoided_weight_restrictions)} weight-restricted roads")
        if self.avoided_hazmat_restrictions:
            parts.append(f"Avoided {len(self.avoided_hazmat_restrictions)} hazmat-restricted areas")
        
        if self.distance_added_for_safety > 0:
            parts.append(f"Added {self.distance_added_for_safety:.1f} miles for truck-safe routing")
        
        if self.required_breaks:
            parts.append(f"Includes {len(self.required_breaks)} required HOS breaks")
        
        self.summary = ". ".join(parts) + "." if parts else "Standard route - no hazards avoided."
        return self.summary
