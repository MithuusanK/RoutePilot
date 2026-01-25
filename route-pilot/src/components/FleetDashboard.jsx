/**
 * FleetDashboard Component
 * 
 * Fleet manager web dashboard with:
 * - Overview of all active trips
 * - Driver status and utilization
 * - ETAs and delay risks
 * - Cost per mile analytics
 * - At-risk trip alerts
 */

import { useState, useEffect } from 'react';
import * as api from '../services/api';
import './FleetDashboard.css';

export default function FleetDashboard() {
  const [dashboard, setDashboard] = useState(null);
  const [trips, setTrips] = useState([]);
  const [atRiskTrips, setAtRiskTrips] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');

  useEffect(() => {
    loadDashboardData();
    // Refresh every 30 seconds
    const interval = setInterval(loadDashboardData, 30000);
    return () => clearInterval(interval);
  }, []);

  async function loadDashboardData() {
    try {
      const [dashData, tripsData, riskData, analyticsData] = await Promise.all([
        api.getFleetDashboard(),
        api.listTrips(),
        api.getTripsAtRisk(),
        api.getFleetAnalytics()
      ]);
      
      setDashboard(dashData);
      setTrips(tripsData.trips || []);
      setAtRiskTrips(riskData.at_risk_trips || []);
      setAnalytics(analyticsData);
      setError(null);
    } catch (err) {
      console.error('Failed to load dashboard:', err);
      setError('Failed to connect to server. Is the backend running?');
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="fleet-dashboard">
        <div className="loading">Loading fleet data...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="fleet-dashboard">
        <div className="error-message">
          ❌ {error}
          <button onClick={loadDashboardData}>Retry</button>
        </div>
      </div>
    );
  }

  return (
    <div className="fleet-dashboard">
      {/* Header */}
      <header className="dashboard-header">
        <h1>📊 Fleet Manager Dashboard</h1>
        <button className="refresh-btn" onClick={loadDashboardData}>
          🔄 Refresh
        </button>
      </header>

      {/* Tab Navigation */}
      <nav className="dashboard-tabs">
        <button 
          className={`tab ${activeTab === 'overview' ? 'active' : ''}`}
          onClick={() => setActiveTab('overview')}
        >
          Overview
        </button>
        <button 
          className={`tab ${activeTab === 'trips' ? 'active' : ''}`}
          onClick={() => setActiveTab('trips')}
        >
          Trips
        </button>
        <button 
          className={`tab ${activeTab === 'drivers' ? 'active' : ''}`}
          onClick={() => setActiveTab('drivers')}
        >
          Drivers
        </button>
        <button 
          className={`tab ${activeTab === 'analytics' ? 'active' : ''}`}
          onClick={() => setActiveTab('analytics')}
        >
          Analytics
        </button>
      </nav>

      {/* Overview Tab */}
      {activeTab === 'overview' && dashboard && (
        <div className="tab-content">
          {/* Summary Cards */}
          <div className="summary-grid">
            <div className="summary-card">
              <div className="card-icon">🚛</div>
              <div className="card-content">
                <span className="card-value">{dashboard.summary.active_trips}</span>
                <span className="card-label">Active Trips</span>
              </div>
            </div>
            
            <div className="summary-card">
              <div className="card-icon">✅</div>
              <div className="card-content">
                <span className="card-value">{dashboard.summary.completed_trips}</span>
                <span className="card-label">Completed Today</span>
              </div>
            </div>
            
            <div className="summary-card">
              <div className="card-icon">📍</div>
              <div className="card-content">
                <span className="card-value">{dashboard.summary.planned_trips}</span>
                <span className="card-label">Planned</span>
              </div>
            </div>
            
            <div className="summary-card highlight">
              <div className="card-icon">⚠️</div>
              <div className="card-content">
                <span className="card-value">{dashboard.alerts.critical}</span>
                <span className="card-label">Critical Alerts</span>
              </div>
            </div>
          </div>

          {/* Cost Summary */}
          <div className="cost-summary">
            <h3>💰 Cost Summary</h3>
            <div className="cost-grid">
              <div className="cost-item">
                <span className="cost-label">Total Fuel Cost</span>
                <span className="cost-value">${dashboard.costs.total_fuel_cost.toFixed(2)}</span>
              </div>
              <div className="cost-item">
                <span className="cost-label">Total Miles</span>
                <span className="cost-value">{dashboard.costs.total_miles.toFixed(1)}</span>
              </div>
              <div className="cost-item">
                <span className="cost-label">Cost per Mile</span>
                <span className="cost-value">${dashboard.costs.cost_per_mile.toFixed(3)}</span>
              </div>
            </div>
          </div>

          {/* At-Risk Trips */}
          {atRiskTrips.length > 0 && (
            <div className="at-risk-section">
              <h3>🚨 Trips At Risk</h3>
              <div className="risk-list">
                {atRiskTrips.map((trip, idx) => (
                  <div key={idx} className="risk-item">
                    <div className="risk-info">
                      <span className="risk-driver">Driver: {trip.driver_id}</span>
                      <span className="risk-truck">Truck: {trip.truck_id}</span>
                    </div>
                    <div className="risk-alerts">
                      {trip.alerts.map((alert, i) => (
                        <span key={i} className={`risk-badge ${alert.severity}`}>
                          {alert.title}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Driver Status */}
          {dashboard.driver_status && dashboard.driver_status.length > 0 && (
            <div className="driver-status-section">
              <h3>👤 Driver Status</h3>
              <div className="driver-list">
                {dashboard.driver_status.map((driver, idx) => (
                  <div key={idx} className="driver-item">
                    <div className="driver-info">
                      <span className="driver-id">{driver.driver_id}</span>
                      <span className={`driver-status ${driver.can_drive ? 'available' : 'unavailable'}`}>
                        {driver.status.replace(/_/g, ' ')}
                      </span>
                    </div>
                    <div className="driver-hours">
                      <span className="hours-remaining">{driver.driving_hours_remaining} hrs left</span>
                      <span className={`drive-status ${driver.can_drive ? 'ok' : 'warning'}`}>
                        {driver.can_drive ? '✅ Ready' : '⚠️ Rest Needed'}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Trips Tab */}
      {activeTab === 'trips' && (
        <div className="tab-content">
          <h3>📋 All Trips</h3>
          
          {trips.length === 0 ? (
            <div className="empty-state">
              <p>No trips found. Plan a new trip to get started.</p>
            </div>
          ) : (
            <div className="trips-table">
              <div className="table-header">
                <span>Status</span>
                <span>Driver</span>
                <span>Truck</span>
                <span>Distance</span>
                <span>Est. Time</span>
                <span>Fuel Cost</span>
              </div>
              {trips.map((trip, idx) => (
                <div key={idx} className="table-row">
                  <span className={`status-badge ${trip.status}`}>
                    {trip.status}
                  </span>
                  <span>{trip.driver_id}</span>
                  <span>{trip.truck_id}</span>
                  <span>{trip.route?.total_distance_miles || '—'} mi</span>
                  <span>{trip.route?.total_time_hours?.toFixed(1) || '—'} hrs</span>
                  <span>${trip.costs?.fuel_cost?.toFixed(2) || '—'}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Drivers Tab */}
      {activeTab === 'drivers' && (
        <div className="tab-content">
          <h3>👥 Driver Management</h3>
          
          <div className="driver-overview">
            <div className="overview-stat">
              <span className="stat-value">{dashboard?.summary?.tracked_drivers || 0}</span>
              <span className="stat-label">Tracked Drivers</span>
            </div>
            <div className="overview-stat">
              <span className="stat-value">
                {dashboard?.driver_status?.filter(d => d.can_drive).length || 0}
              </span>
              <span className="stat-label">Available</span>
            </div>
            <div className="overview-stat">
              <span className="stat-value">
                {dashboard?.driver_status?.filter(d => !d.can_drive).length || 0}
              </span>
              <span className="stat-label">On Break/Rest</span>
            </div>
          </div>

          <div className="driver-cards">
            {dashboard?.driver_status?.map((driver, idx) => (
              <div key={idx} className={`driver-card ${driver.can_drive ? '' : 'resting'}`}>
                <div className="driver-avatar">👤</div>
                <div className="driver-details">
                  <h4>{driver.driver_id}</h4>
                  <p className="driver-status-text">
                    Status: {driver.status.replace(/_/g, ' ')}
                  </p>
                  <div className="hos-bar">
                    <div 
                      className="hos-fill" 
                      style={{ width: `${(driver.driving_hours_remaining / 11) * 100}%` }}
                    />
                  </div>
                  <p className="hos-text">
                    {driver.driving_hours_remaining} / 11 drive hours remaining
                  </p>
                </div>
              </div>
            ))}
            
            {(!dashboard?.driver_status || dashboard.driver_status.length === 0) && (
              <div className="empty-state">
                <p>No drivers tracked yet. Driver data appears when trips are planned.</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Analytics Tab */}
      {activeTab === 'analytics' && (
        <div className="tab-content">
          <h3>📈 Fleet Analytics</h3>
          
          {analytics?.message ? (
            <div className="empty-state">
              <p>{analytics.message}</p>
            </div>
          ) : analytics ? (
            <div className="analytics-content">
              <div className="analytics-summary">
                <div className="analytics-card">
                  <h4>Trip Summary</h4>
                  <div className="analytics-stat">
                    <span className="stat-value">{analytics.completed_trips}</span>
                    <span className="stat-label">Completed Trips</span>
                  </div>
                </div>
                
                <div className="analytics-card">
                  <h4>Distance</h4>
                  <div className="analytics-stat">
                    <span className="stat-value">{analytics.totals?.total_miles}</span>
                    <span className="stat-label">Total Miles</span>
                  </div>
                  <div className="analytics-stat">
                    <span className="stat-value">{analytics.averages?.avg_miles_per_trip}</span>
                    <span className="stat-label">Avg per Trip</span>
                  </div>
                </div>
                
                <div className="analytics-card">
                  <h4>Costs</h4>
                  <div className="analytics-stat">
                    <span className="stat-value">${analytics.totals?.total_fuel_cost}</span>
                    <span className="stat-label">Total Fuel</span>
                  </div>
                  <div className="analytics-stat">
                    <span className="stat-value">${analytics.averages?.cost_per_mile}</span>
                    <span className="stat-label">Cost/Mile</span>
                  </div>
                </div>
                
                <div className="analytics-card">
                  <h4>Time</h4>
                  <div className="analytics-stat">
                    <span className="stat-value">{analytics.totals?.total_driving_hours}</span>
                    <span className="stat-label">Total Hours</span>
                  </div>
                  <div className="analytics-stat">
                    <span className="stat-value">{analytics.averages?.avg_hours_per_trip}</span>
                    <span className="stat-label">Avg per Trip</span>
                  </div>
                </div>
                
                <div className="analytics-card highlight">
                  <h4>Efficiency</h4>
                  <div className="analytics-stat">
                    <span className="stat-value">{analytics.efficiency?.avg_mpg}</span>
                    <span className="stat-label">Avg MPG</span>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="empty-state">
              <p>No analytics data available.</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
