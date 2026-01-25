from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
import pandas as pd
import numpy as np
import io
import json
import logging
from typing import Dict, Any, Optional

from models import StopInput
from validation import validate_csv_dataframe
from config import settings
from database import get_db, init_db, close_db
from db_models import Trip, Stop
from services.routing import (
    compute_trucking_route_summary,
    RoutingValidationError,
    RoutingUpstreamError,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug
)

# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize database connection on startup"""
    logger.info("🚀 Starting RoutePilot API...")
    try:
        init_db()
        logger.info("✅ Database connected and ready")
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {str(e)}")
        logger.error("⚠️  Please check your .env file and Supabase credentials")
        # Don't raise - allow app to start but warn about DB issues


@app.on_event("shutdown")
async def shutdown_event():
    """Close database connection on shutdown"""
    logger.info("👋 Shutting down RoutePilot API...")
    close_db()


@app.get("/")
async def root():
    return {"message": "RoutePilot API v1", "status": "active"}


@app.post("/api/upload-stops")
async def upload_stops(file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    Upload and validate a CSV file containing trip stops.
    
    Returns:
        - success: bool
        - message: str
        - stops_count: int (if successful)
        - errors: list (if validation fails)
        - preview: list of first 5 stops (if successful)
    """
    
    # Validate file type
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=400,
            detail="File must be a CSV"
        )
    
    try:
        # Read CSV into pandas DataFrame
        contents = await file.read()
        df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
        
        # Validate CSV structure and data
        is_valid, errors = validate_csv_dataframe(df)
        
        if not is_valid:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": "CSV validation failed",
                    "errors": errors
                }
            )
        
        # Preprocess DataFrame: convert float NaN to None, numeric strings to strings
        string_columns = ['address', 'city', 'state', 'zip', 'notes', 
                          'contact_name', 'contact_phone', 'reference_number']
        for col in string_columns:
            if col in df.columns:
                def clean_string_value(x):
                    if pd.isna(x):
                        return None
                    if isinstance(x, float):
                        # Convert 75247.0 -> "75247"
                        if x == int(x):
                            return str(int(x))
                        return str(x)
                    return str(x) if x is not None else None
                df[col] = df[col].apply(clean_string_value)
        
        # Convert numeric columns from float to int where appropriate
        int_columns = ['stop_sequence', 'service_duration_minutes']
        for col in int_columns:
            if col in df.columns:
                df[col] = df[col].apply(lambda x: int(x) if pd.notna(x) else None)
        
        # Convert DataFrame rows to Pydantic models for additional validation
        stops = []
        row_errors = []
        
        for idx, row in df.iterrows():
            try:
                # Convert numpy types to native Python types
                row_dict = {}
                for key, val in row.to_dict().items():
                    if pd.isna(val):
                        row_dict[key] = None
                    elif hasattr(val, 'item'):  # numpy scalar
                        row_dict[key] = val.item()
                    else:
                        row_dict[key] = val
                
                stop = StopInput(**row_dict)
                stop.validate_location()  # Custom location validation
                
                # Convert to dict and ensure native Python types
                stop_dict = stop.model_dump()
                for key, val in stop_dict.items():
                    if hasattr(val, 'item'):  # numpy scalar
                        stop_dict[key] = val.item()
                stops.append(stop_dict)
            except Exception as e:
                row_errors.append(f"Row {idx + 2}: {str(e)}")  # +2 for header and 0-indexing
        
        if row_errors:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": "Row validation failed",
                    "errors": row_errors[:10]  # Limit to first 10 errors
                }
            )
        
        # Success - return preview (use JSON to ensure all numpy types are converted)
        preview = stops[:5] if len(stops) > 5 else stops
        
        # Force conversion to native Python types via JSON round-trip
        clean_preview = json.loads(json.dumps(preview, default=str))
        
        return JSONResponse(content={
            "success": True,
            "message": f"Successfully validated {len(stops)} stops",
            "stops_count": len(stops),
            "preview": clean_preview,
            "filename": file.filename
        })
        
    except pd.errors.EmptyDataError:
        raise HTTPException(status_code=400, detail="CSV file is empty")
    except pd.errors.ParserError as e:
        raise HTTPException(status_code=400, detail=f"CSV parsing error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")


@app.get("/api/health")
async def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint - verifies API and database connectivity
    """
    try:
        # Test database connection
        db.execute("SELECT 1")
        db_status = "connected"
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        db_status = "disconnected"
    
    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "service": settings.app_name,
        "version": settings.app_version,
        "database": db_status
    }


# ============================================================================
# Route Summary Endpoint (Trucking Route Calculation)
# ============================================================================

class StopCoordinate(BaseModel):
    """Coordinate for a stop - supports both lat/lng and latitude/longitude keys."""
    lat: Optional[float] = Field(None, ge=-90, le=90)
    lng: Optional[float] = Field(None, ge=-180, le=180)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)


class RouteRequest(BaseModel):
    """Request body for route calculation."""
    stops: Optional[list[StopCoordinate]] = Field(
        None,
        description="Ordered list of stops with coordinates. If omitted, stops are fetched from DB."
    )


class RouteSummaryResponse(BaseModel):
    """Response for route summary endpoint."""
    trip_id: str
    total_distance_km: float
    total_drive_time_minutes: float
    routing_engine: str
    notes: list[str]


@app.post("/api/trips/{trip_id}/route", response_model=RouteSummaryResponse)
async def compute_trip_route(
    trip_id: str,
    request: RouteRequest = None,
    db: Session = Depends(get_db)
) -> RouteSummaryResponse:
    """
    Compute a route summary for a trip's ordered stops.
    
    This endpoint calculates total distance and drive time for trucking dispatch/planning.
    
    **Important**: Results are estimates based on general driving routes and may not account
    for truck-specific restrictions (height/weight limits, hazmat routes, etc.).
    
    Args:
        trip_id: The trip identifier
        request: Optional request body containing stops. If omitted, stops are fetched from DB.
    
    Returns:
        Route summary with distance, time, and disclaimers
    
    Raises:
        400: Invalid coordinates or fewer than 2 stops
        404: Trip not found (when fetching from DB)
        502: Upstream routing service error
    """
    stops_data = []
    
    # Determine stops source
    if request and request.stops:
        # Use stops from request body
        for stop in request.stops:
            lat = stop.lat if stop.lat is not None else stop.latitude
            lng = stop.lng if stop.lng is not None else stop.longitude
            stops_data.append({"lat": lat, "lng": lng})
    else:
        # Fetch stops from database
        trip = db.query(Trip).filter(Trip.id == trip_id).first()
        if not trip:
            raise HTTPException(status_code=404, detail=f"Trip {trip_id} not found")
        
        # Get stops ordered by sequence
        db_stops = (
            db.query(Stop)
            .filter(Stop.trip_id == trip_id)
            .order_by(Stop.stop_sequence)
            .all()
        )
        
        if not db_stops:
            raise HTTPException(
                status_code=400,
                detail="No stops found for this trip"
            )
        
        for stop in db_stops:
            if stop.latitude is None or stop.longitude is None:
                raise HTTPException(
                    status_code=400,
                    detail=f"Stop {stop.stop_sequence} missing coordinates. Geocoding may be required."
                )
            stops_data.append({"lat": stop.latitude, "lng": stop.longitude})
    
    # Validate we have stops
    if not stops_data:
        raise HTTPException(
            status_code=400,
            detail="No stops provided. Include stops in request body or ensure trip has stops in database."
        )
    
    # Compute route
    try:
        result = await compute_trucking_route_summary(stops_data)
    except RoutingValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RoutingUpstreamError as e:
        raise HTTPException(status_code=502, detail=str(e))
    
    return RouteSummaryResponse(
        trip_id=trip_id,
        total_distance_km=result["total_distance_km"],
        total_drive_time_minutes=result["total_drive_time_minutes"],
        routing_engine=result["routing_engine"],
        notes=result["notes"]
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
