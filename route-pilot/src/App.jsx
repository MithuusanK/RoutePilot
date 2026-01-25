import { useState } from 'react'
import './App.css'
import UploadStops from './components/UploadStops'
import DriverDashboard from './components/DriverDashboard'
import TripPlanner from './components/TripPlanner'
import FleetDashboard from './components/FleetDashboard'
import { useTheme, NightModeToggle } from './context/ThemeContext'

function App() {
  const [currentView, setCurrentView] = useState('landing') // landing, driver, planner, fleet, upload
  const { nightMode } = useTheme()

  // Render sub-views
  const renderView = () => {
    switch (currentView) {
      case 'driver':
        return (
          <div className={`app-container ${nightMode ? 'night-mode' : ''}`}>
            <header className="header">
              <div className="header-container">
                <a href="#" onClick={() => setCurrentView('landing')} className="logo">🚛 RoutePilot</a>
                <div className="header-actions">
                  <NightModeToggle size="small" />
                  <button className="btn btn-secondary" onClick={() => setCurrentView('landing')}>
                    ← Back
                  </button>
                </div>
              </div>
            </header>
            <DriverDashboard driverId="driver-001" />
          </div>
        )
      
      case 'planner':
        return (
          <div className={`app-container ${nightMode ? 'night-mode' : ''}`}>
            <header className="header">
              <div className="header-container">
                <a href="#" onClick={() => setCurrentView('landing')} className="logo">🚛 RoutePilot</a>
                <div className="header-actions">
                  <NightModeToggle size="small" />
                  <button className="btn btn-secondary" onClick={() => setCurrentView('landing')}>
                    ← Back
                  </button>
                </div>
              </div>
            </header>
            <TripPlanner />
          </div>
        )
      
      case 'fleet':
        return (
          <FleetDashboard onBack={() => setCurrentView('landing')} />
        )
      
      case 'upload':
        return (
          <div className={`app-container ${nightMode ? 'night-mode' : ''}`}>
            <header className="header">
              <div className="header-container">
                <a href="#" onClick={() => setCurrentView('landing')} className="logo">🚛 RoutePilot</a>
                <div className="header-actions">
                  <NightModeToggle size="small" />
                  <button className="btn btn-secondary" onClick={() => setCurrentView('landing')}>
                    ← Back
                  </button>
                </div>
              </div>
            </header>
            <UploadStops />
          </div>
        )
      
      default:
        return null
    }
  }

  // If not on landing page, render the sub-view
  if (currentView !== 'landing') {
    return renderView()
  }

  return (
    <div className={`landing-page ${nightMode ? 'night-mode' : ''}`}>
      {/* Header */}
      <header className="header">
        <div className="header-container">
          <a href="#" className="logo">🚛 RoutePilot</a>
          <nav className="nav">
            <a href="#features" className="nav-link">Features</a>
            <a href="#how-it-works" className="nav-link">How It Works</a>
            <a href="#contact" className="nav-link">Contact</a>
          </nav>
          <div className="header-actions">
            <NightModeToggle size="small" />
            <button className="btn btn-outline" onClick={() => setCurrentView('driver')}>
              Driver Mode
            </button>
            <button className="btn btn-secondary" onClick={() => setCurrentView('fleet')}>
              Fleet Dashboard
            </button>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="hero">
        <div className="hero-container">
          <h1 className="hero-title">
            Truck-Safe Routing for Professional Drivers
          </h1>
          <p className="hero-subtitle">
            HOS-aware route planning, hazard avoidance, and real-time fleet management for 18-wheelers.
          </p>
          <div className="hero-actions">
            <button className="btn btn-primary btn-large" onClick={() => setCurrentView('planner')}>
              🗺️ Plan a Trip
            </button>
            <button className="btn btn-outline btn-large" onClick={() => setCurrentView('upload')}>
              📤 Upload Routes
            </button>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="features">
        <div className="section-container">
          <h2 className="section-title">Built for Big Rigs</h2>
          <div className="features-grid">
            <div className="feature-card">
              <div className="feature-icon">🛣️</div>
              <h3 className="feature-title">Truck-Safe Routes</h3>
              <p className="feature-description">
                Routes that respect bridge heights, weight limits, and hazmat restrictions. No surprises on the road.
              </p>
            </div>
            <div className="feature-card">
              <div className="feature-icon">⏱️</div>
              <h3 className="feature-title">HOS Compliance</h3>
              <p className="feature-description">
                Automatic break planning based on FMCSA hours of service rules. Stay legal and rested.
              </p>
            </div>
            <div className="feature-card">
              <div className="feature-icon">⛽</div>
              <h3 className="feature-title">Fuel Optimization</h3>
              <p className="feature-description">
                Find the best fuel stops along your route based on price and truck-friendly amenities.
              </p>
            </div>
            <div className="feature-card">
              <div className="feature-icon">🚨</div>
              <h3 className="feature-title">Real-Time Alerts</h3>
              <p className="feature-description">
                Get notified about road hazards, weather conditions, and HOS warnings before they become problems.
              </p>
            </div>
            <div className="feature-card">
              <div className="feature-icon">📊</div>
              <h3 className="feature-title">Fleet Analytics</h3>
              <p className="feature-description">
                Track your fleet's performance, fuel costs, and driver hours in one comprehensive dashboard.
              </p>
            </div>
            <div className="feature-card">
              <div className="feature-icon">📱</div>
              <h3 className="feature-title">Mobile-First Design</h3>
              <p className="feature-description">
                Large buttons, night mode, and voice-ready interface designed for use in the cab.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* How It Works Section */}
      <section id="how-it-works" className="how-it-works">
        <div className="section-container">
          <h2 className="section-title">Get Rolling in 4 Steps</h2>
          <div className="steps">
            <div className="step">
              <div className="step-number">1</div>
              <h3 className="step-title">Register Your Truck</h3>
              <p className="step-description">
                Enter your rig's specs: height, weight, axle count, and cargo type.
              </p>
            </div>
            <div className="step">
              <div className="step-number">2</div>
              <h3 className="step-title">Add Your Stops</h3>
              <p className="step-description">
                Enter pickup and delivery locations. We'll optimize the order.
              </p>
            </div>
            <div className="step">
              <div className="step-number">3</div>
              <h3 className="step-title">Review Your Route</h3>
              <p className="step-description">
                See the safe route with break points, fuel stops, and hazard warnings.
              </p>
            </div>
            <div className="step">
              <div className="step-number">4</div>
              <h3 className="step-title">Hit the Road</h3>
              <p className="step-description">
                Get turn-by-turn navigation with live updates and alerts.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="cta-section">
        <div className="section-container">
          <h2>Ready to Drive Smarter?</h2>
          <p>Join thousands of drivers who trust RoutePilot for safer, more efficient routes.</p>
          <div className="cta-buttons">
            <button className="btn btn-primary btn-large" onClick={() => setCurrentView('planner')}>
              Start Planning Now
            </button>
            <button className="btn btn-outline btn-large" onClick={() => setCurrentView('fleet')}>
              Fleet Manager Portal
            </button>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer id="contact" className="footer">
        <div className="footer-container">
          <div className="footer-brand">RoutePilot</div>
          <div className="footer-links">
            <a href="#features" className="footer-link">Features</a>
            <a href="#how-it-works" className="footer-link">How It Works</a>
            <a href="#contact" className="footer-link">Contact</a>
            <a href="#privacy" className="footer-link">Privacy</a>
            <a href="#terms" className="footer-link">Terms</a>
          </div>
          <div className="footer-copyright">
            © 2026 RoutePilot. All rights reserved.
          </div>
        </div>
      </footer>
    </div>
  )
}

export default App
