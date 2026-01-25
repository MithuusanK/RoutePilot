import pandas as pd
from typing import Tuple, List


def validate_csv_dataframe(df: pd.DataFrame) -> Tuple[bool, List[str]]:
    """
    Validate CSV DataFrame structure and basic constraints before Pydantic validation.
    
    This performs fast, bulk validation using Pandas before per-row Pydantic validation.
    
    Args:
        df: Pandas DataFrame loaded from CSV
        
    Returns:
        Tuple of (is_valid: bool, errors: List[str])
    """
    errors = []
    
    # Define expected columns
    required_cols = {'stop_sequence', 'stop_type', 'service_duration_minutes'}
    optional_cols = {
        'address', 'city', 'state', 'zip',
        'latitude', 'longitude',
        'earliest_time', 'latest_time',
        'notes', 'contact_name', 'contact_phone', 'reference_number'
    }
    all_expected_cols = required_cols | optional_cols
    
    # Check for required columns
    missing_required = required_cols - set(df.columns)
    if missing_required:
        errors.append(f"Missing required columns: {', '.join(sorted(missing_required))}")
        return False, errors
    
    # Warn about unexpected columns (not an error, but informative)
    unexpected_cols = set(df.columns) - all_expected_cols
    if unexpected_cols:
        errors.append(f"Warning: Unexpected columns will be ignored: {', '.join(sorted(unexpected_cols))}")
    
    # Check for empty DataFrame
    if df.empty:
        errors.append("CSV file contains no data rows")
        return False, errors
    
    # Check for duplicate stop sequences
    if df['stop_sequence'].duplicated().any():
        duplicate_sequences = df[df['stop_sequence'].duplicated(keep=False)]['stop_sequence'].unique()
        errors.append(f"Duplicate stop_sequence values found: {sorted(duplicate_sequences.tolist())}")
    
    # Validate stop_sequence is positive integer
    if not pd.api.types.is_numeric_dtype(df['stop_sequence']):
        errors.append("stop_sequence must contain numeric values")
    elif (df['stop_sequence'] < 1).any():
        invalid_rows = df[df['stop_sequence'] < 1].index.tolist()
        errors.append(f"stop_sequence must be >= 1 (invalid at rows: {invalid_rows})")
    
    # Validate stop_type values
    valid_stop_types = {'PICKUP', 'DELIVERY', 'WAYPOINT', 'pickup', 'delivery', 'waypoint'}
    if 'stop_type' in df.columns:
        # Handle NaN values and invalid types
        stop_type_upper = df['stop_type'].fillna('').astype(str).str.upper()
        invalid_types = df[~stop_type_upper.isin({'PICKUP', 'DELIVERY', 'WAYPOINT', ''})]
        if not invalid_types.empty:
            errors.append(
                f"Invalid stop_type values at rows {invalid_types.index.tolist()}: "
                f"must be PICKUP, DELIVERY, or WAYPOINT"
            )
    
    # Validate service_duration_minutes
    if not pd.api.types.is_numeric_dtype(df['service_duration_minutes']):
        errors.append("service_duration_minutes must contain numeric values")
    elif ((df['service_duration_minutes'] < 0) | (df['service_duration_minutes'] > 480)).any():
        invalid_rows = df[
            (df['service_duration_minutes'] < 0) | (df['service_duration_minutes'] > 480)
        ].index.tolist()
        errors.append(
            f"service_duration_minutes must be between 0-480 (invalid at rows: {invalid_rows})"
        )
    
    # Validate time windows if present
    if 'earliest_time' in df.columns and 'latest_time' in df.columns:
        # Convert to datetime
        df['earliest_time'] = pd.to_datetime(df['earliest_time'], errors='coerce')
        df['latest_time'] = pd.to_datetime(df['latest_time'], errors='coerce')
        
        # Check for invalid time windows (latest <= earliest)
        time_window_mask = df['earliest_time'].notna() & df['latest_time'].notna()
        invalid_windows = df[time_window_mask & (df['latest_time'] <= df['earliest_time'])]
        
        if not invalid_windows.empty:
            errors.append(
                f"latest_time must be after earliest_time (invalid at rows: {invalid_windows.index.tolist()})"
            )
    
    # Validate latitude/longitude ranges if present
    if 'latitude' in df.columns:
        invalid_lat = df[
            df['latitude'].notna() & ((df['latitude'] < -90) | (df['latitude'] > 90))
        ]
        if not invalid_lat.empty:
            errors.append(
                f"latitude must be between -90 and 90 (invalid at rows: {invalid_lat.index.tolist()})"
            )
    
    if 'longitude' in df.columns:
        invalid_lon = df[
            df['longitude'].notna() & ((df['longitude'] < -180) | (df['longitude'] > 180))
        ]
        if not invalid_lon.empty:
            errors.append(
                f"longitude must be between -180 and 180 (invalid at rows: {invalid_lon.index.tolist()})"
            )
    
    # Validate location data (either coords OR address must be present)
    location_errors = []
    for idx, row in df.iterrows():
        has_coords = pd.notna(row.get('latitude')) and pd.notna(row.get('longitude'))
        has_address = all(
            pd.notna(row.get(col)) 
            for col in ['address', 'city', 'state', 'zip']
            if col in df.columns
        )
        
        if not has_coords and not has_address:
            location_errors.append(idx)
    
    if location_errors:
        errors.append(
            f"Each row must have either coordinates (lat/lon) OR full address "
            f"(address, city, state, zip). Missing location data at rows: {location_errors}"
        )
    
    # Validate state format (2 letters) if present
    if 'state' in df.columns:
        state_filled = df['state'].fillna('').astype(str)
        state_valid = state_filled.str.match(r'^[A-Za-z]{2}$') | (state_filled == '')
        invalid_states = df[~state_valid]
        if not invalid_states.empty:
            errors.append(
                f"state must be 2-letter code (invalid at rows: {invalid_states.index.tolist()})"
            )
    
    # Validate ZIP format (5 digits) if present
    if 'zip' in df.columns:
        zip_filled = df['zip'].fillna('').astype(str).str.replace('.0', '', regex=False)
        zip_valid = zip_filled.str.match(r'^\d{5}$') | (zip_filled == '')
        invalid_zips = df[~zip_valid]
        if not invalid_zips.empty:
            errors.append(
                f"zip must be 5-digit code (invalid at rows: {invalid_zips.index.tolist()})"
            )
    
    # Validate phone format (10 digits) if present
    if 'contact_phone' in df.columns:
        phone_filled = df['contact_phone'].fillna('').astype(str).str.replace('.0', '', regex=False)
        phone_valid = phone_filled.str.match(r'^\d{10}$') | (phone_filled == '')
        invalid_phones = df[~phone_valid]
        if not invalid_phones.empty:
            errors.append(
                f"contact_phone must be 10-digit number (invalid at rows: {invalid_phones.index.tolist()})"
            )
    
    # Return validation result
    is_valid = len(errors) == 0
    return is_valid, errors
