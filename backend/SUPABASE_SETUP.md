# Supabase Setup Guide for RoutePilot

This guide walks you through connecting your RoutePilot backend to your existing Supabase PostgreSQL database.

## Prerequisites

- Supabase project already created with tables: `customers`, `trips`, `stops`
- Python 3.8+ installed
- Backend dependencies installed (`pip install -r requirements.txt`)

## Step 1: Get Your Supabase Credentials

### A. Get API Credentials

1. Go to your Supabase dashboard: https://app.supabase.com
2. Select your project
3. Click **Settings** → **API**
4. Copy these values:
   - **Project URL** (e.g., `https://abc123xyz.supabase.co`)
   - **anon public** key (under "Project API keys")

### B. Get Database Connection String

1. In Supabase dashboard, go to **Settings** → **Database**
2. Scroll down to **Connection string** section
3. Select **Connection pooling** tab
4. Copy the connection string (it looks like):
   ```
   postgresql://postgres.abc123xyz:[YOUR-PASSWORD]@aws-0-us-west-1.pooler.supabase.com:5432/postgres
   ```
5. Replace `[YOUR-PASSWORD]` with your actual database password
   - If you forgot your password, you can reset it on the same page

## Step 2: Create .env File

1. Navigate to the backend directory:
   ```bash
   cd C:\Users\Amsan\Documents\RoutePilot\backend
   ```

2. Copy the example file:
   ```bash
   copy .env.example .env
   ```

3. Open `.env` in your text editor and fill in your credentials:

   ```env
   # Replace with YOUR actual Supabase values:
   SUPABASE_URL=https://your-project-id.supabase.co
   SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
   SUPABASE_DB_URL=postgresql://postgres:[YOUR-PASSWORD]@db.your-project-id.supabase.co:5432/postgres
   ```

   **Example with real values:**
   ```env
   SUPABASE_URL=https://xyzabc123.supabase.co
   SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inh5emFiYzEyMyIsInJvbGUiOiJhbm9uIiwiaWF0IjoxNjQwMDAwMDAwLCJleHAiOjE5NTU1NzYwMDB9.example-key
   SUPABASE_DB_URL=postgresql://postgres:MySecretPassword123!@db.xyzabc123.supabase.co:5432/postgres
   ```

4. Save the file

## Step 3: Install Dependencies

If you haven't already:

```bash
cd C:\Users\Amsan\Documents\RoutePilot\backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## Step 4: Test the Connection

### A. Start the Backend

```bash
python main.py
```

Look for these startup messages:

```
✅ Database connection successful
✅ Table 'customers' exists
✅ Table 'trips' exists
✅ Table 'stops' exists
✅ Database initialization complete
✅ Database connected and ready
🚀 Starting RoutePilot API...
```

### B. Test Health Endpoint

Open a new terminal and run:

```bash
curl http://localhost:8000/api/health
```

You should see:

```json
{
  "status": "healthy",
  "service": "RoutePilot API",
  "version": "1.0.0",
  "database": "connected"
}
```

## Troubleshooting

### ❌ "Database initialization failed"

**Check 1: Verify credentials**
- Make sure there are no extra spaces in your `.env` file
- Ensure you replaced `[YOUR-PASSWORD]` with your actual password
- Confirm the URL starts with `https://` (not `http://`)

**Check 2: Test connection string directly**

You can test your connection string with `psql` (if installed):

```bash
psql "postgresql://postgres:YOUR-PASSWORD@db.your-project-id.supabase.co:5432/postgres"
```

**Check 3: Verify tables exist**

In Supabase dashboard:
1. Go to **Table Editor**
2. Verify these tables exist:
   - `customers`
   - `trips`
   - `stops`

### ❌ "Table does not exist"

The backend expects tables to already exist in Supabase. If they don't:

1. Go to Supabase **SQL Editor**
2. Run the table creation scripts (provided separately)
3. Verify tables appear in **Table Editor**

### ❌ "Module not found" errors

Make sure virtual environment is activated and dependencies are installed:

```bash
venv\Scripts\activate
pip install -r requirements.txt
```

### ❌ Connection timeout

**Check 1: Network/Firewall**
- Supabase allows connections from any IP by default
- Check your firewall isn't blocking port 5432

**Check 2: Project paused**
- Free-tier Supabase projects pause after inactivity
- Go to your project dashboard and wake it up if needed

## Next Steps

Once you see ✅ **Database connected and ready**, you're all set!

You can now:
1. Test CSV upload at http://localhost:8000/api/upload-stops
2. Access your data through SQLAlchemy models
3. Build Step 2 (route generation) features

## Security Notes

- ✅ `.env` is in `.gitignore` - never commit it
- ✅ RLS (Row Level Security) is enabled on your Supabase tables
- ✅ Use `SUPABASE_KEY` (anon public key) for frontend, not the service role key
- ✅ Database connection uses connection pooling for production safety
