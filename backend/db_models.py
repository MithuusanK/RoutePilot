from sqlalchemy import Column, String, Integer, Float, ForeignKey, CheckConstraint, Index, Text
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP, ENUM
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
import uuid

Base = declarative_base()


class Customer(Base):
    """
    Customer model - maps to existing Supabase 'customers' table.
    DO NOT MODIFY SCHEMA - this matches the existing table structure.
    """
    __tablename__ = "customers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    trips = relationship("Trip", back_populates="customer", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Customer(id={self.id}, name={self.name})>"


class Trip(Base):
    """
    Trip model - maps to existing Supabase 'trips' table.
    DO NOT MODIFY SCHEMA - this matches the existing table structure.
    One trip = one truck route with multiple stops.
    """
    __tablename__ = "trips"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    status = Column(String(20), default="PENDING", nullable=False)
    
    # Relationships
    customer = relationship("Customer", back_populates="trips")
    stops = relationship("Stop", back_populates="trip", cascade="all, delete-orphan", order_by="Stop.stop_sequence")
    
    def __repr__(self):
        return f"<Trip(id={self.id}, customer_id={self.customer_id}, status={self.status})>"


class Stop(Base):
    """
    Stop model - maps to existing Supabase 'stops' table.
    DO NOT MODIFY SCHEMA - this matches the existing table structure.
    Represents a pickup, delivery, or waypoint in a trucking route.
    """
    __tablename__ = "stops"
    
    # Create ENUM type for stop_type (must match database)
    stop_type_enum = ENUM('PICKUP', 'DELIVERY', 'WAYPOINT', name='stop_type_enum', create_type=False)
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trip_id = Column(UUID(as_uuid=True), ForeignKey("trips.id", ondelete="CASCADE"), nullable=False)
    stop_sequence = Column(Integer, nullable=False)
    stop_type = Column(stop_type_enum, nullable=False)
    
    # Location fields
    address = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(2), nullable=True)
    zip = Column(String(5), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    geocoded_at = Column(TIMESTAMP(timezone=True), nullable=True)
    
    # Time constraints
    earliest_time = Column(TIMESTAMP(timezone=True), nullable=True)
    latest_time = Column(TIMESTAMP(timezone=True), nullable=True)
    service_duration_minutes = Column(Integer, nullable=False)
    
    # Metadata
    notes = Column(Text, nullable=True)
    contact_name = Column(String(100), nullable=True)
    contact_phone = Column(String(10), nullable=True)
    reference_number = Column(String(50), nullable=True)
    source = Column(String(20), nullable=True, default="csv_upload")
    
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    trip = relationship("Trip", back_populates="stops")
    
    # Table constraints (must match existing database)
    __table_args__ = (
        CheckConstraint(
            '(latest_time IS NULL OR earliest_time IS NULL OR latest_time > earliest_time)',
            name='chk_time_window'
        ),
        CheckConstraint(
            'service_duration_minutes >= 0 AND service_duration_minutes <= 480',
            name='chk_service_duration'
        ),
        CheckConstraint(
            '(latitude IS NOT NULL AND longitude IS NOT NULL) OR '
            '(address IS NOT NULL AND city IS NOT NULL AND state IS NOT NULL AND zip IS NOT NULL)',
            name='chk_location_data'
        ),
        Index('idx_stops_trip_sequence', 'trip_id', 'stop_sequence'),
        Index('idx_stops_coordinates', 'latitude', 'longitude'),
        Index('idx_stops_trip_id', 'trip_id'),
    )
    
    def __repr__(self):
        return f"<Stop(id={self.id}, trip_id={self.trip_id}, sequence={self.stop_sequence}, type={self.stop_type})>"
    
    @property
    def has_coordinates(self) -> bool:
        """Check if stop has valid coordinates"""
        return self.latitude is not None and self.longitude is not None
    
    @property
    def has_address(self) -> bool:
        """Check if stop has valid address"""
        return all([self.address, self.city, self.state, self.zip])
    
    @property
    def location_display(self) -> str:
        """Return human-readable location string"""
        if self.city and self.state:
            return f"{self.city}, {self.state}"
        elif self.has_coordinates:
            return f"{self.latitude:.4f}, {self.longitude:.4f}"
        else:
            return "Unknown location"
