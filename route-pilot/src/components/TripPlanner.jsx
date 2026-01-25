/**
 * TripPlanner Component
 * 
 * Full trip planning interface with:
 * - Truck specification input
 * - Multi-stop management
 * - Route optimization preview
 * - HOS impact analysis
 * - Cost estimation
 */

import { useState, useEffect } from 'react';
import * as api from '../services/api';
import './TripPlanner.css';

export default function TripPlanner({ onTripPlanned }) {
  // Form state
  const [truckId, setTruckId] = useState('');
  const [driverId, setDriverId] = useState('');
  const [truckSpecs, setTruckSpecs] = useState(api.DEFAULT_TRUCK_SPECS);
  const [stops, setStops] = useState([]);
  const [startLocation, setStartLocation] = useState({ lat: '', lon: '' });
  const [fuelPrice, setFuelPrice] = useState(4.50);
  const [optimizeOrder, setOptimizeOrder] = useState(true);
  
  // UI state
  const [step, setStep] = useState(1); // 1: Truck, 2: Stops, 3: Review
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [plannedRoute, setPlannedRoute] = useState(null);
  const [registeredTrucks, setRegisteredTrucks] = useState([]);

  // Load registered trucks on mount
  useEffect(() => {
    loadTrucks();
  }, []);

  async function loadTrucks() {
    try {
      const result = await api.listTrucks();
      setRegisteredTrucks(result.trucks || []);
    } catch (err) {
      console.error('Failed to load trucks:', err);
    }
  }

  function handleTruckSpecChange(field, value) {
    setTruckSpecs(prev => ({
      ...prev,
      [field]: value
    }));
  }

  function addStop() {
    setStops(prev => [
      ...prev,
      {
        stop_sequence: prev.length + 1,
        stop_type: 'DELIVERY',
        address: '',
        city: '',
        state: '',
        zip: '',
        latitude: '',
        longitude: '',
        service_duration_minutes: 30,
        earliest_time: '',
        latest_time: '',
        notes: '',
        contact_name: '',
        contact_phone: '',
      }
    ]);
  }

  function updateStop(index, field, value) {
    setStops(prev => prev.map((stop, i) => 
      i === index ? { ...stop, [field]: value } : stop
    ));
  }

  function removeStop(index) {
    setStops(prev => prev.filter((_, i) => i !== index).map((stop, i) => ({
      ...stop,
      stop_sequence: i + 1
    })));
  }

  async function handleRegisterTruck() {
    if (!truckId) {
      setError('Please enter a Truck ID');
      return;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      const result = await api.registerTruck({
        truck_id: truckId,
        ...truckSpecs
      });
      
      await loadTrucks();
      setStep(2);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handlePlanTrip() {
    // Validate required fields
    if (!startLocation.lat || !startLocation.lon) {
      setError('Please enter start location coordinates');
      return;
    }
    
    if (stops.length === 0) {
      setError('Please add at least one stop');
      return;
    }
    
    // Validate stops have coordinates
    for (const stop of stops) {
      const hasCoords = stop.latitude && stop.longitude;
      const hasAddress = stop.address && stop.city && stop.state && stop.zip;
      
      if (!hasCoords && !hasAddress) {
        setError(`Stop ${stop.stop_sequence} needs either coordinates or full address`);
        return;
      }
    }
    
    setLoading(true);
    setError(null);
    
    try {
      // Prepare stops data
      const formattedStops = stops.map(stop => ({
        stop_sequence: stop.stop_sequence,
        stop_type: stop.stop_type,
        address: stop.address || null,
        city: stop.city || null,
        state: stop.state || null,
        zip: stop.zip || null,
        latitude: stop.latitude ? parseFloat(stop.latitude) : null,
        longitude: stop.longitude ? parseFloat(stop.longitude) : null,
        service_duration_minutes: parseInt(stop.service_duration_minutes) || 30,
        earliest_time: stop.earliest_time || null,
        latest_time: stop.latest_time || null,
        notes: stop.notes || null,
        contact_name: stop.contact_name || null,
        contact_phone: stop.contact_phone || null,
      }));
      
      const result = await api.planTrip({
        stops: formattedStops,
        truck_id: truckId || 'default-truck',
        driver_id: driverId || 'default-driver',
        start_latitude: parseFloat(startLocation.lat),
        start_longitude: parseFloat(startLocation.lon),
        optimize_order: optimizeOrder,
        fuel_price_per_gallon: parseFloat(fuelPrice),
      });
      
      setPlannedRoute(result);
      setStep(3);
      
      if (onTripPlanned) {
        onTripPlanned(result);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleStartTrip() {
    if (!plannedRoute?.trip_id) return;
    
    setLoading(true);
    try {
      await api.startTrip(plannedRoute.trip_id);
      alert('Trip started! Drive safely. 🚛');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="trip-planner">
      <h2 className="planner-title">🗺️ Plan New Trip</h2>
      
      {/* Progress Steps */}
      <div className="progress-steps">
        <div className={`progress-step ${step >= 1 ? 'active' : ''} ${step > 1 ? 'completed' : ''}`}>
          <span className="step-number">1</span>
          <span className="step-label">Truck Specs</span>
        </div>
        <div className={`progress-step ${step >= 2 ? 'active' : ''} ${step > 2 ? 'completed' : ''}`}>
          <span className="step-number">2</span>
          <span className="step-label">Add Stops</span>
        </div>
        <div className={`progress-step ${step >= 3 ? 'active' : ''}`}>
          <span className="step-number">3</span>
          <span className="step-label">Review</span>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="planner-error">
          ❌ {error}
          <button onClick={() => setError(null)} className="error-close">×</button>
        </div>
      )}

      {/* Step 1: Truck Specifications */}
      {step === 1 && (
        <div className="step-content">
          <h3 className="step-title">🚛 Truck Specifications</h3>
          
          {registeredTrucks.length > 0 && (
            <div className="form-group">
              <label>Use Existing Truck</label>
              <select 
                value={truckId}
                onChange={(e) => {
                  setTruckId(e.target.value);
                  const truck = registeredTrucks.find(t => t.truck_id === e.target.value);
                  if (truck) setTruckSpecs(truck);
                }}
              >
                <option value="">-- Select or Enter New --</option>
                {registeredTrucks.map(t => (
                  <option key={t.truck_id} value={t.truck_id}>{t.truck_id}</option>
                ))}
              </select>
            </div>
          )}
          
          <div className="form-group">
            <label>Truck ID *</label>
            <input
              type="text"
              value={truckId}
              onChange={(e) => setTruckId(e.target.value)}
              placeholder="e.g., TRUCK-001"
            />
          </div>
          
          <div className="form-group">
            <label>Driver ID</label>
            <input
              type="text"
              value={driverId}
              onChange={(e) => setDriverId(e.target.value)}
              placeholder="e.g., driver-001"
            />
          </div>
          
          <div className="form-row">
            <div className="form-group">
              <label>Truck Type</label>
              <select
                value={truckSpecs.truck_type}
                onChange={(e) => handleTruckSpecChange('truck_type', e.target.value)}
              >
                {api.TRUCK_TYPES.map(t => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
            </div>
            
            <div className="form-group">
              <label>Hazmat Class</label>
              <select
                value={truckSpecs.hazmat_class}
                onChange={(e) => handleTruckSpecChange('hazmat_class', e.target.value)}
              >
                {api.HAZMAT_CLASSES.map(h => (
                  <option key={h.value} value={h.value}>{h.label}</option>
                ))}
              </select>
            </div>
          </div>
          
          <div className="form-row">
            <div className="form-group">
              <label>Height (ft)</label>
              <input
                type="number"
                step="0.1"
                value={truckSpecs.height_feet}
                onChange={(e) => handleTruckSpecChange('height_feet', parseFloat(e.target.value))}
              />
            </div>
            
            <div className="form-group">
              <label>Width (ft)</label>
              <input
                type="number"
                step="0.1"
                value={truckSpecs.width_feet}
                onChange={(e) => handleTruckSpecChange('width_feet', parseFloat(e.target.value))}
              />
            </div>
            
            <div className="form-group">
              <label>Length (ft)</label>
              <input
                type="number"
                step="0.1"
                value={truckSpecs.length_feet}
                onChange={(e) => handleTruckSpecChange('length_feet', parseFloat(e.target.value))}
              />
            </div>
          </div>
          
          <div className="form-row">
            <div className="form-group">
              <label>Gross Weight (lbs)</label>
              <input
                type="number"
                value={truckSpecs.gross_weight_lbs}
                onChange={(e) => handleTruckSpecChange('gross_weight_lbs', parseInt(e.target.value))}
              />
            </div>
            
            <div className="form-group">
              <label>Axles</label>
              <input
                type="number"
                value={truckSpecs.axle_count}
                onChange={(e) => handleTruckSpecChange('axle_count', parseInt(e.target.value))}
              />
            </div>
          </div>
          
          <div className="form-row">
            <div className="form-group">
              <label>Fuel Tank (gal)</label>
              <input
                type="number"
                value={truckSpecs.fuel_tank_gallons}
                onChange={(e) => handleTruckSpecChange('fuel_tank_gallons', parseFloat(e.target.value))}
              />
            </div>
            
            <div className="form-group">
              <label>MPG</label>
              <input
                type="number"
                step="0.1"
                value={truckSpecs.mpg}
                onChange={(e) => handleTruckSpecChange('mpg', parseFloat(e.target.value))}
              />
            </div>
          </div>
          
          <button 
            className="btn-primary btn-large"
            onClick={handleRegisterTruck}
            disabled={loading}
          >
            {loading ? 'Saving...' : 'Continue to Stops →'}
          </button>
        </div>
      )}

      {/* Step 2: Add Stops */}
      {step === 2 && (
        <div className="step-content">
          <h3 className="step-title">📍 Trip Stops</h3>
          
          {/* Start Location */}
          <div className="start-location">
            <h4>Starting Location</h4>
            <div className="form-row">
              <div className="form-group">
                <label>Latitude *</label>
                <input
                  type="number"
                  step="0.0001"
                  value={startLocation.lat}
                  onChange={(e) => setStartLocation(prev => ({ ...prev, lat: e.target.value }))}
                  placeholder="e.g., 32.7767"
                />
              </div>
              <div className="form-group">
                <label>Longitude *</label>
                <input
                  type="number"
                  step="0.0001"
                  value={startLocation.lon}
                  onChange={(e) => setStartLocation(prev => ({ ...prev, lon: e.target.value }))}
                  placeholder="e.g., -96.7970"
                />
              </div>
            </div>
          </div>
          
          {/* Fuel Price */}
          <div className="form-group">
            <label>Diesel Price ($/gal)</label>
            <input
              type="number"
              step="0.01"
              value={fuelPrice}
              onChange={(e) => setFuelPrice(parseFloat(e.target.value))}
            />
          </div>
          
          {/* Optimize Toggle */}
          <div className="form-group checkbox-group">
            <label>
              <input
                type="checkbox"
                checked={optimizeOrder}
                onChange={(e) => setOptimizeOrder(e.target.checked)}
              />
              Optimize stop order for efficiency
            </label>
          </div>
          
          {/* Stops List */}
          <div className="stops-list">
            {stops.map((stop, index) => (
              <div key={index} className="stop-card">
                <div className="stop-header">
                  <span className="stop-number">Stop #{stop.stop_sequence}</span>
                  <button 
                    className="btn-remove"
                    onClick={() => removeStop(index)}
                  >
                    ✕
                  </button>
                </div>
                
                <div className="form-row">
                  <div className="form-group">
                    <label>Type</label>
                    <select
                      value={stop.stop_type}
                      onChange={(e) => updateStop(index, 'stop_type', e.target.value)}
                    >
                      <option value="PICKUP">Pickup</option>
                      <option value="DELIVERY">Delivery</option>
                      <option value="WAYPOINT">Waypoint</option>
                    </select>
                  </div>
                  
                  <div className="form-group">
                    <label>Service Time (min)</label>
                    <input
                      type="number"
                      value={stop.service_duration_minutes}
                      onChange={(e) => updateStop(index, 'service_duration_minutes', e.target.value)}
                    />
                  </div>
                </div>
                
                <div className="form-row">
                  <div className="form-group">
                    <label>Latitude</label>
                    <input
                      type="number"
                      step="0.0001"
                      value={stop.latitude}
                      onChange={(e) => updateStop(index, 'latitude', e.target.value)}
                      placeholder="Optional if address provided"
                    />
                  </div>
                  <div className="form-group">
                    <label>Longitude</label>
                    <input
                      type="number"
                      step="0.0001"
                      value={stop.longitude}
                      onChange={(e) => updateStop(index, 'longitude', e.target.value)}
                    />
                  </div>
                </div>
                
                <div className="form-group">
                  <label>Address</label>
                  <input
                    type="text"
                    value={stop.address}
                    onChange={(e) => updateStop(index, 'address', e.target.value)}
                    placeholder="Street address"
                  />
                </div>
                
                <div className="form-row">
                  <div className="form-group">
                    <label>City</label>
                    <input
                      type="text"
                      value={stop.city}
                      onChange={(e) => updateStop(index, 'city', e.target.value)}
                    />
                  </div>
                  <div className="form-group" style={{ width: '80px' }}>
                    <label>State</label>
                    <input
                      type="text"
                      maxLength="2"
                      value={stop.state}
                      onChange={(e) => updateStop(index, 'state', e.target.value.toUpperCase())}
                    />
                  </div>
                  <div className="form-group" style={{ width: '100px' }}>
                    <label>ZIP</label>
                    <input
                      type="text"
                      maxLength="5"
                      value={stop.zip}
                      onChange={(e) => updateStop(index, 'zip', e.target.value)}
                    />
                  </div>
                </div>
                
                <div className="form-group">
                  <label>Notes</label>
                  <input
                    type="text"
                    value={stop.notes}
                    onChange={(e) => updateStop(index, 'notes', e.target.value)}
                    placeholder="Gate codes, dock info, etc."
                  />
                </div>
              </div>
            ))}
          </div>
          
          <button className="btn-secondary btn-add-stop" onClick={addStop}>
            + Add Stop
          </button>
          
          <div className="step-actions">
            <button className="btn-back" onClick={() => setStep(1)}>
              ← Back
            </button>
            <button 
              className="btn-primary btn-large"
              onClick={handlePlanTrip}
              disabled={loading || stops.length === 0}
            >
              {loading ? 'Planning Route...' : 'Plan Route →'}
            </button>
          </div>
        </div>
      )}

      {/* Step 3: Review Route */}
      {step === 3 && plannedRoute && (
        <div className="step-content">
          <h3 className="step-title">✅ Route Planned</h3>
          
          {/* Route Summary */}
          <div className="route-summary">
            <div className="summary-stat">
              <span className="stat-value">{plannedRoute.route?.total_distance_miles}</span>
              <span className="stat-label">Miles</span>
            </div>
            <div className="summary-stat">
              <span className="stat-value">{plannedRoute.route?.total_time_hours}</span>
              <span className="stat-label">Hours</span>
            </div>
            <div className="summary-stat">
              <span className="stat-value">{plannedRoute.route?.stop_count}</span>
              <span className="stat-label">Stops</span>
            </div>
            <div className="summary-stat">
              <span className="stat-value">${plannedRoute.costs?.fuel_cost}</span>
              <span className="stat-label">Fuel Cost</span>
            </div>
          </div>
          
          {/* Route Explanation */}
          {plannedRoute.explanation && (
            <div className="route-explanation">
              <h4>🛡️ Route Safety</h4>
              <p>{plannedRoute.explanation.summary}</p>
              
              {plannedRoute.explanation.avoided_low_bridges?.length > 0 && (
                <div className="avoided-hazard">
                  ⚠️ Avoided {plannedRoute.explanation.avoided_low_bridges.length} low bridges
                </div>
              )}
              
              {plannedRoute.explanation.avoided_weight_restrictions?.length > 0 && (
                <div className="avoided-hazard">
                  ⚠️ Avoided {plannedRoute.explanation.avoided_weight_restrictions.length} weight restrictions
                </div>
              )}
            </div>
          )}
          
          {/* HOS Impact */}
          <div className="hos-impact">
            <h4>⏱️ HOS Impact</h4>
            <div className="hos-details">
              <p>
                <strong>Required Breaks:</strong> {plannedRoute.hos?.required_breaks || 0}
              </p>
              <p>
                <strong>Can Complete Without 10hr Rest:</strong> {' '}
                {plannedRoute.hos?.can_complete_without_rest ? '✅ Yes' : '❌ No'}
              </p>
              <p>
                <strong>Drive Hours Remaining After:</strong> {' '}
                {plannedRoute.hos?.hours_remaining_at_end?.toFixed(1)} hrs
              </p>
            </div>
          </div>
          
          {/* Planned Breaks */}
          {plannedRoute.breaks?.length > 0 && (
            <div className="planned-breaks">
              <h4>☕ Planned Breaks</h4>
              {plannedRoute.breaks.map((brk, idx) => (
                <div key={idx} className="break-item">
                  <span className="break-type">{brk.break_type}</span>
                  <span className="break-location">{brk.location_name}</span>
                  <span className="break-duration">{brk.duration_minutes} min</span>
                </div>
              ))}
            </div>
          )}
          
          {/* Alerts */}
          {plannedRoute.alerts?.length > 0 && (
            <div className="route-alerts">
              <h4>🚨 Alerts</h4>
              {plannedRoute.alerts.map((alert, idx) => (
                <div key={idx} className={`alert-item ${alert.severity}`}>
                  <strong>{alert.title}</strong>
                  <p>{alert.message}</p>
                  {alert.suggested_action && (
                    <p className="suggestion">💡 {alert.suggested_action}</p>
                  )}
                </div>
              ))}
            </div>
          )}
          
          <div className="step-actions">
            <button className="btn-back" onClick={() => setStep(2)}>
              ← Modify Stops
            </button>
            <button 
              className="btn-primary btn-large btn-start"
              onClick={handleStartTrip}
              disabled={loading}
            >
              🚀 Start Trip
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
