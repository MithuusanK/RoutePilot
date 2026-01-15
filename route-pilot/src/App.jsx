import { useState } from 'react'
import './App.css'
import UploadStops from './components/UploadStops'

function App() {
  const [showUpload, setShowUpload] = useState(false)

  if (showUpload) {
    return (
      <div className="app-container">
        <header className="header">
          <div className="header-container">
            <a href="#" onClick={() => setShowUpload(false)} className="logo">RoutePilot</a>
            <button className="btn btn-secondary" onClick={() => setShowUpload(false)}>
              ← Back to Home
            </button>
          </div>
        </header>
        <UploadStops />
      </div>
    )
  }

  return (
    <div className="landing-page">
      {/* Header */}
      <header className="header">
        <div className="header-container">
          <a href="#" className="logo">RoutePilot</a>
          <nav className="nav">
            <a href="#features" className="nav-link">Features</a>
            <a href="#how-it-works" className="nav-link">How It Works</a>
            <a href="#contact" className="nav-link">Contact</a>
          </nav>
          <button className="btn btn-secondary" onClick={() => setShowUpload(true)}>
            Upload Routes
          </button>
        </div>
      </header>

      {/* Hero Section */}
      <section className="hero">
        <div className="hero-container">
          <h1 className="hero-title">
            Route Optimization for Modern Fleet Managers
          </h1>
          <p className="hero-subtitle">
            Reduce operational costs by up to 30% through intelligent route planning and real-time optimization.
          </p>
          <button className="btn btn-primary" onClick={() => setShowUpload(true)}>
            Upload Your Routes Now
          </button>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="features">
        <div className="section-container">
          <h2 className="section-title">Features</h2>
          <div className="features-grid">
            <div className="feature-card">
              <h3 className="feature-title">Route Analysis</h3>
              <p className="feature-description">
                Comprehensive analysis of current routes to identify inefficiencies and optimization opportunities.
              </p>
            </div>
            <div className="feature-card">
              <h3 className="feature-title">Smart Optimization</h3>
              <p className="feature-description">
                AI-powered algorithms calculate the most efficient routes based on distance, traffic, and delivery windows.
              </p>
            </div>
            <div className="feature-card">
              <h3 className="feature-title">Cost Savings</h3>
              <p className="feature-description">
                Track fuel consumption, vehicle wear, and labor hours to measure and maximize your savings.
              </p>
            </div>
            <div className="feature-card">
              <h3 className="feature-title">Dynamic Scheduling</h3>
              <p className="feature-description">
                Adapt to last-minute changes with real-time route adjustments and automated driver notifications.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* How It Works Section */}
      <section id="how-it-works" className="how-it-works">
        <div className="section-container">
          <h2 className="section-title">How It Works</h2>
          <div className="steps">
            <div className="step">
              <div className="step-number">1</div>
              <h3 className="step-title">Upload Routes</h3>
              <p className="step-description">
                Import your existing route data via CSV, API, or manual entry.
              </p>
            </div>
            <div className="step">
              <div className="step-number">2</div>
              <h3 className="step-title">Analyze</h3>
              <p className="step-description">
                Our system evaluates your routes for inefficiencies and potential improvements.
              </p>
            </div>
            <div className="step">
              <div className="step-number">3</div>
              <h3 className="step-title">Optimize</h3>
              <p className="step-description">
                Receive optimized route suggestions based on multiple factors and constraints.
              </p>
            </div>
            <div className="step">
              <div className="step-number">4</div>
              <h3 className="step-title">Review Savings</h3>
              <p className="step-description">
                View detailed reports on projected cost reductions and efficiency gains.
              </p>
            </div>
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
