/**
 * RoutePilot API Service
 * 
 * Centralized API client for all backend communications.
 * Handles truck management, HOS tracking, trip planning, and fleet dashboard.
 */

const API_BASE_URL = 'http://localhost:8000';

/**
 * Generic fetch wrapper with error handling
 */
async function apiRequest(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  
  const defaultOptions = {
    headers: {
      'Content-Type': 'application/json',
    },
  };

  try {
    const response = await fetch(url, { ...defaultOptions, ...options });
    const data = await response.json();
    
    if (!response.ok) {
      throw new Error(data.detail || data.message || 'API request failed');
    }
    
    return data;
  } catch (error) {
    console.error(`API Error [${endpoint}]:`, error);
    throw error;
  }
}

// =============================================================================
// HEALTH & STATUS
// =============================================================================

export async function checkHealth() {
  return apiRequest('/api/health');
}

// =============================================================================
// TRUCK MANAGEMENT
// =============================================================================

export async function registerTruck(truckData) {
  return apiRequest('/api/trucks', {
    method: 'POST',
    body: JSON.stringify(truckData),
  });
}

export async function listTrucks() {
  return apiRequest('/api/trucks');
}

export async function getTruck(truckId) {
  return apiRequest(`/api/trucks/${truckId}`);
}

export async function updateTruck(truckId, truckData) {
  return apiRequest(`/api/trucks/${truckId}`, {
    method: 'PUT',
    body: JSON.stringify(truckData),
  });
}

export async function updateTruckFuel(truckId, currentFuelGallons) {
  return apiRequest(`/api/trucks/${truckId}/fuel`, {
    method: 'PATCH',
    body: JSON.stringify({ current_fuel_gallons: currentFuelGallons }),
  });
}

// =============================================================================
// HOS (HOURS OF SERVICE)
// =============================================================================

export async function getDriverHOS(driverId) {
  return apiRequest(`/api/drivers/${driverId}/hos`);
}

export async function updateDriverHOS(driverId, hosData) {
  return apiRequest(`/api/drivers/${driverId}/hos`, {
    method: 'POST',
    body: JSON.stringify(hosData),
  });
}

export async function logHOSAction(driverId, action) {
  return apiRequest(`/api/drivers/${driverId}/hos/action`, {
    method: 'POST',
    body: JSON.stringify({ action }),
  });
}

// =============================================================================
// TRIP PLANNING
// =============================================================================

export async function uploadStops(file) {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await fetch(`${API_BASE_URL}/api/upload-stops`, {
    method: 'POST',
    body: formData,
  });
  
  const data = await response.json();
  
  if (!response.ok && !data.success) {
    throw new Error(data.detail || data.message || 'Upload failed');
  }
  
  return data;
}

export async function planTrip(tripData) {
  return apiRequest('/api/trips/plan', {
    method: 'POST',
    body: JSON.stringify(tripData),
  });
}

export async function listTrips(filters = {}) {
  const params = new URLSearchParams();
  if (filters.status) params.append('status', filters.status);
  if (filters.driverId) params.append('driver_id', filters.driverId);
  
  const queryString = params.toString();
  return apiRequest(`/api/trips${queryString ? '?' + queryString : ''}`);
}

export async function getTrip(tripId) {
  return apiRequest(`/api/trips/${tripId}`);
}

export async function startTrip(tripId) {
  return apiRequest(`/api/trips/${tripId}/start`, {
    method: 'POST',
  });
}

export async function markArrived(tripId, stopSequence) {
  return apiRequest(`/api/trips/${tripId}/stop/${stopSequence}/arrived`, {
    method: 'POST',
  });
}

export async function completeTrip(tripId) {
  return apiRequest(`/api/trips/${tripId}/complete`, {
    method: 'POST',
  });
}

// =============================================================================
// DRIVER QUICK ACTIONS
// =============================================================================

export async function driverQuickAction(action) {
  return apiRequest('/api/driver/quick-action', {
    method: 'POST',
    body: JSON.stringify({ action }),
  });
}

// =============================================================================
// ALERTS
// =============================================================================

export async function getAlerts(filters = {}) {
  const params = new URLSearchParams();
  if (filters.driverId) params.append('driver_id', filters.driverId);
  if (filters.severity) params.append('severity', filters.severity);
  if (filters.unacknowledgedOnly) params.append('unacknowledged_only', 'true');
  
  const queryString = params.toString();
  return apiRequest(`/api/alerts${queryString ? '?' + queryString : ''}`);
}

export async function acknowledgeAlert(alertId) {
  return apiRequest(`/api/alerts/${alertId}/acknowledge`, {
    method: 'POST',
  });
}

export async function dismissAlert(alertId) {
  return apiRequest(`/api/alerts/${alertId}/dismiss`, {
    method: 'POST',
  });
}

// =============================================================================
// FLEET MANAGER DASHBOARD
// =============================================================================

export async function getFleetDashboard() {
  return apiRequest('/api/fleet/dashboard');
}

export async function getTripsAtRisk() {
  return apiRequest('/api/fleet/trips/at-risk');
}

export async function getFleetAnalytics() {
  return apiRequest('/api/fleet/analytics');
}

// =============================================================================
// DEFAULT TRUCK SPECS FOR NEW TRUCKS
// =============================================================================

export const DEFAULT_TRUCK_SPECS = {
  truck_type: 'dry_van',
  height_feet: 13.5,
  width_feet: 8.5,
  length_feet: 53.0,
  gross_weight_lbs: 80000,
  axle_count: 5,
  fuel_tank_gallons: 300,
  mpg: 6.5,
  hazmat_class: 'none',
  requires_oversize_permit: false,
};

export const TRUCK_TYPES = [
  { value: 'semi_trailer', label: 'Semi Trailer (53\')' },
  { value: 'dry_van', label: 'Dry Van' },
  { value: 'refrigerated', label: 'Refrigerated (Reefer)' },
  { value: 'flatbed', label: 'Flatbed' },
  { value: 'tanker', label: 'Tanker' },
  { value: 'lowboy', label: 'Lowboy' },
  { value: 'car_carrier', label: 'Car Carrier' },
  { value: 'container', label: 'Container' },
];

export const HAZMAT_CLASSES = [
  { value: 'none', label: 'None' },
  { value: 'class_1', label: 'Class 1 - Explosives' },
  { value: 'class_2', label: 'Class 2 - Gases' },
  { value: 'class_3', label: 'Class 3 - Flammable Liquids' },
  { value: 'class_4', label: 'Class 4 - Flammable Solids' },
  { value: 'class_5', label: 'Class 5 - Oxidizers' },
  { value: 'class_6', label: 'Class 6 - Poisons' },
  { value: 'class_7', label: 'Class 7 - Radioactive' },
  { value: 'class_8', label: 'Class 8 - Corrosive' },
  { value: 'class_9', label: 'Class 9 - Miscellaneous' },
];
