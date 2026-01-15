# RoutePilot Backend

FastAPI backend for RoutePilot route optimization SaaS with Supabase PostgreSQL.

## Quick Start

### 1. Install Dependencies

Create a virtual environment and install packages:

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Supabase

Create a `.env` file with your Supabase credentials:

```bash
# Copy the example file
cp .env.example .env
```

Edit `.env` and add your Supabase credentials:

```env
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your-anon-public-key-here
SUPABASE_DB_URL=postgresql://postgres:[YOUR-PASSWORD]@db.your-project-id.supabase.co:5432/postgres
```

**Where to find these:**

1. **SUPABASE_URL** & **SUPABASE_KEY**: 
   - Go to https://app.supabase.com/project/_/settings/api
   - Copy "Project URL" and "anon public" key

2. **SUPABASE_DB_URL**:
   - Go to https://app.supabase.com/project/_/settings/database
   - Copy the "Connection string" under "Connection pooling"
   - Replace `[YOUR-PASSWORD]` with your database password

### 3. Run the Server

```bash
python main.py
```

Or use uvicorn directly:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at: http://localhost:8000

## API Endpoints

### Core Endpoints

- `GET /` - API status check
- `GET /api/health` - Health check with database connectivity test
- `POST /api/upload-stops` - Upload and validate CSV with route stops

### Database Connection

The backend connects to your Supabase PostgreSQL database using SQLAlchemy.

**Existing Tables** (DO NOT modify):
- `customers` - Customer accounts
- `trips` - Route trips (one trip = one truck)
- `stops` - Stop locations (pickup/delivery/waypoint)

All tables use UUIDs and have RLS (Row Level Security) enabled.

## CSV Upload Format

Required columns:
- `stop_sequence` (int) - Stop order number
- `stop_type` (PICKUP|DELIVERY|WAYPOINT)
- `service_duration_minutes` (int, 0-480)

Location (provide one of):
- `latitude` + `longitude` (coordinates)
- `address` + `city` + `state` + `zip` (full address)

Optional columns:
- `earliest_time`, `latest_time` (ISO8601: 2026-01-20T08:00:00)
- `notes`, `contact_name`, `contact_phone`, `reference_number`

See [sample-route.csv](sample-route.csv) for a complete example.

## Project Structure

```
backend/
├── main.py              # FastAPI application and endpoints
├── models.py            # Pydantic models for CSV validation
├── db_models.py         # SQLAlchemy ORM models (maps to Supabase tables)
├── database.py          # Database connection and session management
├── config.py            # Configuration management (loads from .env)
├── validation.py        # Pandas CSV validation logic
├── requirements.txt     # Python dependencies
├── .env.example         # Example environment file
├── .env                 # Your actual environment file (gitignored)
└── sample-route.csv     # Sample CSV file
```

## Development

### Testing Database Connection

Check if database is connected:

```bash
curl http://localhost:8000/api/health
```

Should return:
```json
{
  "status": "healthy",
  "service": "RoutePilot API",
  "version": "1.0.0",
  "database": "connected"
}
```

### Logging

The app logs database initialization and errors. Check console output for:
- ✅ Success messages (green checkmarks)
- ❌ Error messages (red X marks)

### CORS Configuration

The backend accepts requests from:
- http://localhost:5173 (Vite default)
- http://localhost:3000 (Alternative React)

Add more origins in `.env`:
```env
CORS_ORIGINS=http://localhost:5173,http://localhost:3000,https://yourdomain.com
```

## Troubleshooting

### "Database initialization failed"

1. Check your `.env` file exists and has correct credentials
2. Verify your Supabase project is active
3. Test connection string in a PostgreSQL client
4. Check if your IP is whitelisted in Supabase (if required)

### "Table does not exist"

The backend expects these tables to already exist in Supabase:
- `customers`
- `trips`  
- `stops`

Do NOT run migrations - tables are created in Supabase dashboard.

### Module import errors

Make sure virtual environment is activated and all packages are installed:
```bash
pip install -r requirements.txt
```
