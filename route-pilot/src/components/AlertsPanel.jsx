/**
 * AlertsPanel.jsx
 * 
 * Real-time alerts display component for drivers and fleet managers.
 * Shows HOS warnings, route hazards, weather alerts, and system notifications.
 */

import { useState, useEffect } from 'react'
import { getAlerts, dismissAlert } from '../services/api'
import './AlertsPanel.css'

const SEVERITY_CONFIG = {
  critical: { icon: '🚨', color: '#dc2626', priority: 1 },
  warning: { icon: '⚠️', color: '#f59e0b', priority: 2 },
  info: { icon: 'ℹ️', color: '#3b82f6', priority: 3 }
}

const TYPE_ICONS = {
  hos_warning: '⏰',
  route_hazard: '🚧',
  weather: '🌧️',
  fuel: '⛽',
  maintenance: '🔧',
  delivery: '📦',
  system: '🔔'
}

export default function AlertsPanel({ 
  driverId = null, 
  tripId = null, 
  maxAlerts = 5,
  compact = false,
  onAlertClick = null
}) {
  const [alerts, setAlerts] = useState([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('all') // all, critical, unread
  const [expandedAlert, setExpandedAlert] = useState(null)

  // Load alerts
  useEffect(() => {
    loadAlerts()
    // Poll for new alerts every 30 seconds
    const interval = setInterval(loadAlerts, 30000)
    return () => clearInterval(interval)
  }, [driverId, tripId])

  const loadAlerts = async () => {
    try {
      const params = {}
      if (driverId) params.driver_id = driverId
      if (tripId) params.trip_id = tripId
      
      const data = await getAlerts(params)
      
      // Sort by severity, then by timestamp
      const sorted = data.sort((a, b) => {
        const priorityA = SEVERITY_CONFIG[a.severity]?.priority || 99
        const priorityB = SEVERITY_CONFIG[b.severity]?.priority || 99
        if (priorityA !== priorityB) return priorityA - priorityB
        return new Date(b.timestamp) - new Date(a.timestamp)
      })
      
      setAlerts(sorted)
    } catch (error) {
      console.error('Failed to load alerts:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleDismiss = async (alertId, e) => {
    e.stopPropagation()
    try {
      await dismissAlert(alertId)
      setAlerts(prev => prev.filter(a => a.id !== alertId))
    } catch (error) {
      console.error('Failed to dismiss alert:', error)
    }
  }

  const handleAlertClick = (alert) => {
    if (onAlertClick) {
      onAlertClick(alert)
    } else {
      setExpandedAlert(expandedAlert === alert.id ? null : alert.id)
    }
  }

  const formatTime = (timestamp) => {
    const date = new Date(timestamp)
    const now = new Date()
    const diff = now - date
    
    if (diff < 60000) return 'Just now'
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`
    return date.toLocaleDateString()
  }

  // Filter alerts
  const filteredAlerts = alerts.filter(alert => {
    if (filter === 'critical') return alert.severity === 'critical'
    if (filter === 'unread') return !alert.read
    return true
  }).slice(0, maxAlerts)

  const criticalCount = alerts.filter(a => a.severity === 'critical').length
  const unreadCount = alerts.filter(a => !a.read).length

  if (loading) {
    return (
      <div className={`alerts-panel ${compact ? 'compact' : ''}`}>
        <div className="alerts-loading">Loading alerts...</div>
      </div>
    )
  }

  return (
    <div className={`alerts-panel ${compact ? 'compact' : ''}`}>
      {/* Header */}
      {!compact && (
        <div className="alerts-header">
          <h3>
            🔔 Alerts
            {unreadCount > 0 && <span className="badge">{unreadCount}</span>}
          </h3>
          <div className="filter-tabs">
            <button 
              className={`filter-tab ${filter === 'all' ? 'active' : ''}`}
              onClick={() => setFilter('all')}
            >
              All
            </button>
            <button 
              className={`filter-tab ${filter === 'critical' ? 'active' : ''}`}
              onClick={() => setFilter('critical')}
            >
              Critical {criticalCount > 0 && `(${criticalCount})`}
            </button>
          </div>
        </div>
      )}

      {/* Alerts List */}
      <div className="alerts-list">
        {filteredAlerts.length === 0 ? (
          <div className="no-alerts">
            <span className="no-alerts-icon">✅</span>
            <p>No alerts at this time</p>
          </div>
        ) : (
          filteredAlerts.map(alert => {
            const severityConfig = SEVERITY_CONFIG[alert.severity] || SEVERITY_CONFIG.info
            const typeIcon = TYPE_ICONS[alert.type] || '🔔'
            const isExpanded = expandedAlert === alert.id
            
            return (
              <div
                key={alert.id}
                className={`alert-item ${alert.severity} ${isExpanded ? 'expanded' : ''}`}
                style={{ borderLeftColor: severityConfig.color }}
                onClick={() => handleAlertClick(alert)}
              >
                <div className="alert-icon">{typeIcon}</div>
                <div className="alert-content">
                  <div className="alert-title">
                    <span className="severity-indicator">{severityConfig.icon}</span>
                    {alert.title || alert.message}
                  </div>
                  {(isExpanded || compact) && alert.details && (
                    <div className="alert-details">{alert.details}</div>
                  )}
                  <div className="alert-meta">
                    <span className="alert-time">{formatTime(alert.timestamp)}</span>
                    {alert.trip_id && <span className="alert-trip">Trip: {alert.trip_id.slice(0, 8)}</span>}
                  </div>
                </div>
                {!compact && (
                  <button 
                    className="dismiss-btn"
                    onClick={(e) => handleDismiss(alert.id, e)}
                    title="Dismiss"
                  >
                    ×
                  </button>
                )}
              </div>
            )
          })
        )}
      </div>

      {/* View All Link */}
      {alerts.length > maxAlerts && !compact && (
        <div className="view-all">
          <button onClick={() => setFilter('all')}>
            View all {alerts.length} alerts →
          </button>
        </div>
      )}
    </div>
  )
}

// Quick alert toast for immediate notifications
export function AlertToast({ alert, onDismiss }) {
  const [visible, setVisible] = useState(true)
  const severityConfig = SEVERITY_CONFIG[alert.severity] || SEVERITY_CONFIG.info
  const typeIcon = TYPE_ICONS[alert.type] || '🔔'

  useEffect(() => {
    // Auto-dismiss after 5 seconds for non-critical alerts
    if (alert.severity !== 'critical') {
      const timer = setTimeout(() => {
        setVisible(false)
        onDismiss?.()
      }, 5000)
      return () => clearTimeout(timer)
    }
  }, [alert, onDismiss])

  if (!visible) return null

  return (
    <div 
      className={`alert-toast ${alert.severity}`}
      style={{ borderColor: severityConfig.color }}
    >
      <span className="toast-icon">{typeIcon}</span>
      <div className="toast-content">
        <strong>{alert.title}</strong>
        <p>{alert.message}</p>
      </div>
      <button className="toast-dismiss" onClick={onDismiss}>×</button>
    </div>
  )
}
