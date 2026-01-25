import { useState } from 'react';
import './TripRouteSummary.css';

/**
 * TripRouteSummary component - displays route summary for a trip.
 * Designed for long-haul trucking dispatchers.
 * 
 * Usage:
 *   <TripRouteSummary tripId="uuid-here" stops={stopsArray} disabled={false} />
 * 
 * If stops are provided, they will be sent to the API.
 * If not, the API will fetch stops from the database.
 */
export default function TripRouteSummary({ tripId, stops = null, disabled = false }) {
  const [loading, setLoading] = useState(false);
  const [routeSummary, setRouteSummary] = useState(null);
  const [error, setError] = useState(null);
  const [hasCalculated, setHasCalculated] = useState(false);

  const computeRoute = async () => {
    if (!tripId) {
      setError('Trip ID is required');
      return;
    }

    setLoading(true);
    setError(null);
    setRouteSummary(null);
    setHasCalculated(true);

    try {
      const body = stops ? { stops } : {};
      
      const response = await fetch(`http://localhost:8000/api/trips/${tripId}/route`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
      });

      const data = await response.json();

      if (response.ok) {
        setRouteSummary(data);
      } else {
        // Handle different error codes
        if (response.status === 400) {
          setError(data.detail || 'Invalid request. Please check your stops data.');
        } else if (response.status === 404) {
          setError(data.detail || 'Trip not found.');
        } else if (response.status === 502) {
          setError(data.detail || 'Routing service unavailable. Please try again later.');
        } else {
          setError(data.detail || 'An unexpected error occurred.');
        }
      }
    } catch (err) {
      setError(`Connection failed: ${err.message}. Check your network and try again.`);
    } finally {
      setLoading(false);
    }
  };

  const formatDriveTime = (minutes) => {
    if (minutes < 60) {
      return `${minutes} min`;
    }
    const hours = Math.floor(minutes / 60);
    const mins = Math.round(minutes % 60);
    return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`;
  };

  // Check if button should be disabled
  const isDisabled = disabled || loading || !stops || stops.length < 2;

  return (
    <div className="route-summary-container">
      <div className="route-summary-card">
        <h3 className="route-summary-title">🚛 Route Summary</h3>
        
        {/* Generate Route Button */}
        <button
          onClick={computeRoute}
          disabled={isDisabled}
          className="btn-generate-route"
          aria-busy={loading}
        >
          {loading ? (
            <>
              <span className="loading-spinner" aria-hidden="true"></span>
              Calculating truck route…
            </>
          ) : (
            'Generate Route'
          )}
        </button>

        {/* Disabled state hint */}
        {!loading && isDisabled && !hasCalculated && (
          <p className="route-hint">Upload stops with coordinates to generate a route.</p>
        )}

        {/* Error Display with Retry */}
        {error && (
          <div className="route-alert route-alert-error">
            <div className="route-alert-content">
              <span className="route-alert-icon">⚠️</span>
              <span className="route-alert-message">{error}</span>
            </div>
            <button 
              onClick={computeRoute} 
              className="btn-retry"
              disabled={loading}
            >
              Retry
            </button>
          </div>
        )}

        {/* Route Summary Display */}
        {routeSummary && (
          <div className="route-results">
            <div className="route-stats">
              <div className="route-stat route-stat-distance">
                <span className="route-stat-icon">🛣️</span>
                <div className="route-stat-content">
                  <span className="route-stat-value">
                    {routeSummary.total_distance_km.toLocaleString()}
                  </span>
                  <span className="route-stat-label">Total Distance (km)</span>
                </div>
              </div>
              <div className="route-stat route-stat-time">
                <span className="route-stat-icon">🕐</span>
                <div className="route-stat-content">
                  <span className="route-stat-value">
                    {formatDriveTime(routeSummary.total_drive_time_minutes)}
                  </span>
                  <span className="route-stat-label">Estimated Drive Time (ETA)</span>
                </div>
              </div>
            </div>

            {/* Disclaimer for truckers */}
            <div className="route-disclaimer">
              <span className="route-disclaimer-icon">⚠️</span>
              <div className="route-disclaimer-text">
                <strong>Estimate only</strong> — Does not account for truck-specific restrictions 
                (bridge heights, weight limits, HazMat routes, or HOS regulations).
              </div>
            </div>

            {/* Notes from API */}
            {routeSummary.notes && routeSummary.notes.length > 0 && (
              <div className="route-notes">
                <p className="route-notes-title">Route Notes:</p>
                {routeSummary.notes.map((note, idx) => (
                  <p key={idx} className="route-note">• {note}</p>
                ))}
              </div>
            )}

            <div className="route-engine-badge">
              Route calculated via {routeSummary.routing_engine.toUpperCase()}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
