from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import pandas as pd
import io
import logging
from typing import Dict, Any

from models import StopInput
from validation import validate_csv_dataframe
from config import settings
from database import get_db, init_db, close_db

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
        
        # Convert DataFrame rows to Pydantic models for additional validation
        stops = []
        row_errors = []
        
        for idx, row in df.iterrows():
            try:
                stop = StopInput(**row.to_dict())
                stop.validate_location()  # Custom location validation
                stops.append(stop.dict())
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
        
        # Success - return preview
        preview = stops[:5] if len(stops) > 5 else stops
        
        return {
            "success": True,
            "message": f"Successfully validated {len(stops)} stops",
            "stops_count": len(stops),
            "preview": preview,
            "filename": file.filename
        }
        
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
