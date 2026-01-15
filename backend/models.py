from pydantic import BaseModel, Field, validator
from enum import Enum
from datetime import datetime
from typing import Optional


class StopType(str, Enum):
    """Enum for stop types in a trucking route"""
    PICKUP = "PICKUP"
    DELIVERY = "DELIVERY"
    WAYPOINT = "WAYPOINT"


class StopInput(BaseModel):
    """
    Pydantic model for validating CSV stop input.
    This is the canonical input format for RoutePilot v1.
    """
    
    stop_sequence: int = Field(
        ge=1,
        description="Stop sequence number (must be positive integer)"
    )
    
    stop_type: StopType = Field(
        description="Type of stop: PICKUP, DELIVERY, or WAYPOINT"
    )
    
    # Address fields (optional if coordinates provided)
    address: Optional[str] = Field(
        None,
        max_length=255,
        description="Street address"
    )
    
    city: Optional[str] = Field(
        None,
        max_length=100,
        description="City name"
    )
    
    state: Optional[str] = Field(
        None,
        min_length=2,
        max_length=2,
        description="2-letter state code (e.g., TX, CA)"
    )
    
    zip: Optional[str] = Field(
        None,
        pattern="^[0-9]{5}$",
        description="5-digit ZIP code"
    )
    
    # Coordinates (optional if address provided)
    latitude: Optional[float] = Field(
        None,
        ge=-90,
        le=90,
        description="Latitude in WGS84 format"
    )
    
    longitude: Optional[float] = Field(
        None,
        ge=-180,
        le=180,
        description="Longitude in WGS84 format"
    )
    
    # Time window constraints
    earliest_time: Optional[datetime] = Field(
        None,
        description="Earliest arrival time (ISO8601 format)"
    )
    
    latest_time: Optional[datetime] = Field(
        None,
        description="Latest arrival time (ISO8601 format)"
    )
    
    # Service time
    service_duration_minutes: int = Field(
        ge=0,
        le=480,
        description="Time required at stop in minutes (0-480)"
    )
    
    # Metadata
    notes: Optional[str] = Field(
        None,
        max_length=500,
        description="Special instructions (gate codes, dock info, etc.)"
    )
    
    contact_name: Optional[str] = Field(
        None,
        max_length=100,
        description="On-site contact name"
    )
    
    contact_phone: Optional[str] = Field(
        None,
        pattern="^[0-9]{10}$",
        description="10-digit phone number (no dashes or spaces)"
    )
    
    reference_number: Optional[str] = Field(
        None,
        max_length=50,
        description="PO number, BOL, or internal tracking number"
    )
    
    @validator('latest_time')
    def latest_after_earliest(cls, v, values):
        """Ensure latest_time comes after earliest_time"""
        if v and values.get('earliest_time') and v <= values['earliest_time']:
            raise ValueError('latest_time must be after earliest_time')
        return v
    
    @validator('state')
    def state_uppercase(cls, v):
        """Convert state code to uppercase"""
        return v.upper() if v else None
    
    @validator('stop_type', pre=True)
    def stop_type_uppercase(cls, v):
        """Convert stop_type to uppercase for flexibility"""
        return v.upper() if isinstance(v, str) else v
    
    class Config:
        use_enum_values = True
    
    def validate_location(self):
        """
        Custom validation: must have either (lat/lon) OR (address+city+state+zip)
        
        Raises:
            ValueError: If neither coordinate pair nor full address is provided
        """
        has_coords = self.latitude is not None and self.longitude is not None
        has_address = all([self.address, self.city, self.state, self.zip])
        
        if not has_coords and not has_address:
            raise ValueError(
                "Must provide either coordinates (latitude/longitude) "
                "OR full address (address, city, state, zip)"
            )
        
        return True
