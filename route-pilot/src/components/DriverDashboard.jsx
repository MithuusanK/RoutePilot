/**
 * DriverDashboard Component
 * 
 * Mobile-first driver interface with:
 * - Current trip overview
 * - Turn-by-turn navigation info
 * - One-tap quick actions
 * - HOS status display
 * - Night mode support
 */

import { useState, useEffect } from 'react';
import * as api from '../services/api';
import './DriverDashboard.css';

export default function DriverDashboard({ driverId = 'driver-001', nightMode = false }) {
  const [currentTrip, setCurrentTrip] = useState(null);
  const [hosStatus, setHosStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(null);
  const [message, setMessage] = useState(null);

  // Fetch driver data on mount
  useEffect(() => {
    loadDriverData();
  }, [driverId]);

  async function loadDriverData() {
    setLoading(true);
    try {
      // Load HOS status
      const hos = await api.getDriverHOS(driverId);
      setHosStatus(hos);

      // Load active trips
      const trips = await api.listTrips({ status: 'active', driverId });
      if (trips.trips && trips.trips.length > 0) {
        setCurrentTrip(trips.trips[0]);
      }
    } catch (error) {
      console.error('Failed to load driver data:', error);
    } finally {
      setLoading(false);
    }
  }

  async function handleQuickAction(action) {
    setActionLoading(action);
    setMessage(null);
    
    try {
      const result = await api.driverQuickAction(action);
      setMessage({ type: 'success', text: result.message });
      
      // Refresh HOS status after actions that affect it
      if (['start_break', 'arrived'].includes(action)) {
        const hos = await api.getDriverHOS(driverId);
        setHosStatus(hos);
      }
    } catch (error) {
      setMessage({ type: 'error', text: error.message });
    } finally {
      setActionLoading(null);
    }
  }

  async function handleHOSAction(action) {
    setActionLoading(action);
    setMessage(null);
    
    try {
      await api.logHOSAction(driverId, action);
      const hos = await api.getDriverHOS(driverId);
      setHosStatus(hos);
      setMessage({ type: 'success', text: `Action "${action.replace('_', ' ')}" recorded` });
    } catch (error) {
      setMessage({ type: 'error', text: error.message });
    } finally {
      setActionLoading(null);
    }
  }

  if (loading) {
    return (
      <div className={`driver-dashboard ${nightMode ? 'night-mode' : ''}`}>
        <div className="loading-spinner">Loading...</div>
      </div>
    );
  }

  const hosData = hosStatus?.hos || hosStatus?.default_status;
  const canDrive = hosStatus?.can_drive ?? true;

  return (
    <div className={`driver-dashboard ${nightMode ? 'night-mode' : ''}`}>
      {/* Header */}
      <header className="driver-header">
        <h1 className="driver-title">🚛 RoutePilot</h1>
        <div className="driver-id">Driver: {driverId}</div>
      </header>

      {/* Message Display */}
      {message && (
        <div className={`driver-message ${message.type}`}>
          {message.type === 'success' ? '✅' : '❌'} {message.text}
        </div>
      )}

      {/* HOS Status Card */}
      <section className="hos-card">
        <h2 className="card-title">⏱️ Hours of Service</h2>
        <div className="hos-grid">
          <div className="hos-item">
            <span className="hos-value">{hosData?.driving_hours_remaining?.toFixed(1) || '11.0'}</span>
            <span className="hos-label">Drive Hours Left</span>
          </div>
          <div className="hos-item">
            <span className="hos-value">{hosData?.on_duty_hours_remaining?.toFixed(1) || '14.0'}</span>
            <span className="hos-label">On-Duty Left</span>
          </div>
          <div className="hos-item">
            <span className="hos-value">{hosData?.cycle_hours_remaining?.toFixed(1) || '70.0'}</span>
            <span className="hos-label">70-Hour Left</span>
          </div>
          <div className="hos-item">
            <span className={`hos-status ${canDrive ? 'ok' : 'warning'}`}>
              {canDrive ? '✓ Ready' : '⚠️ Break Needed'}
            </span>
            <span className="hos-label">Status</span>
          </div>
        </div>
        
        {hosData?.break_required && (
          <div className="hos-warning">
            ⚠️ 30-minute break required before driving
          </div>
        )}
      </section>

      {/* Current Trip Card */}
      {currentTrip ? (
        <section className="trip-card">
          <h2 className="card-title">📍 Current Trip</h2>
          <div className="trip-info">
            <div className="trip-stat">
              <span className="stat-value">{currentTrip.route?.total_distance_miles || '—'}</span>
              <span className="stat-label">Miles</span>
            </div>
            <div className="trip-stat">
              <span className="stat-value">{currentTrip.route?.total_time_hours?.toFixed(1) || '—'}</span>
              <span className="stat-label">Hours</span>
            </div>
            <div className="trip-stat">
              <span className="stat-value">{currentTrip.route?.stop_count || '—'}</span>
              <span className="stat-label">Stops</span>
            </div>
          </div>
          
          {/* Next Stop */}
          <div className="next-stop">
            <div className="next-stop-label">Next Stop:</div>
            <div className="next-stop-location">
              {currentTrip.route?.stops?.[0]?.city || 'Loading...'}
            </div>
          </div>
        </section>
      ) : (
        <section className="trip-card empty">
          <h2 className="card-title">📍 No Active Trip</h2>
          <p className="empty-message">Plan a new trip to get started</p>
        </section>
      )}

      {/* Quick Actions - Large Touch Targets */}
      <section className="quick-actions">
        <h2 className="card-title">⚡ Quick Actions</h2>
        
        <div className="action-grid">
          <button
            className="action-btn action-arrived"
            onClick={() => handleQuickAction('arrived')}
            disabled={actionLoading}
          >
            {actionLoading === 'arrived' ? '...' : '📍 Arrived'}
          </button>
          
          <button
            className="action-btn action-break"
            onClick={() => handleQuickAction('start_break')}
            disabled={actionLoading}
          >
            {actionLoading === 'start_break' ? '...' : '☕ Start Break'}
          </button>
          
          <button
            className="action-btn action-late"
            onClick={() => handleQuickAction('running_late')}
            disabled={actionLoading}
          >
            {actionLoading === 'running_late' ? '...' : '⚠️ Running Late'}
          </button>
          
          <button
            className="action-btn action-fuel"
            onClick={() => handleQuickAction('need_fuel')}
            disabled={actionLoading}
          >
            {actionLoading === 'need_fuel' ? '...' : '⛽ Need Fuel'}
          </button>
        </div>
      </section>

      {/* HOS Control Actions */}
      <section className="hos-actions">
        <h2 className="card-title">📋 Duty Status</h2>
        
        <div className="hos-action-grid">
          <button
            className="hos-btn hos-driving"
            onClick={() => handleHOSAction('start_driving')}
            disabled={actionLoading || !canDrive}
          >
            🚛 Start Driving
          </button>
          
          <button
            className="hos-btn hos-stop"
            onClick={() => handleHOSAction('stop_driving')}
            disabled={actionLoading}
          >
            ⏹️ Stop Driving
          </button>
          
          <button
            className="hos-btn hos-rest"
            onClick={() => handleHOSAction('start_rest')}
            disabled={actionLoading}
          >
            😴 Start 10hr Rest
          </button>
          
          <button
            className="hos-btn hos-end-rest"
            onClick={() => handleHOSAction('end_rest')}
            disabled={actionLoading}
          >
            ☀️ End Rest
          </button>
        </div>
      </section>

      {/* Alerts Section */}
      {currentTrip?.alerts && currentTrip.alerts.length > 0 && (
        <section className="alerts-section">
          <h2 className="card-title">🚨 Alerts</h2>
          <div className="alerts-list">
            {currentTrip.alerts.slice(0, 3).map((alert, idx) => (
              <div key={idx} className={`alert-item ${alert.severity}`}>
                <div className="alert-title">{alert.title}</div>
                <div className="alert-message">{alert.message}</div>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
