/**
 * ThemeContext.jsx
 * 
 * Provides night mode toggle and theme management for the entire app.
 * Trucker-friendly night mode with high contrast colors for safe cab use.
 */

import { createContext, useContext, useState, useEffect } from 'react'

const ThemeContext = createContext()

export const useTheme = () => {
  const context = useContext(ThemeContext)
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider')
  }
  return context
}

export function ThemeProvider({ children }) {
  // Initialize from localStorage or system preference
  const [nightMode, setNightMode] = useState(() => {
    const saved = localStorage.getItem('routepilot-night-mode')
    if (saved !== null) {
      return saved === 'true'
    }
    // Check system preference
    return window.matchMedia?.('(prefers-color-scheme: dark)').matches || false
  })

  // Persist preference and apply to document
  useEffect(() => {
    localStorage.setItem('routepilot-night-mode', nightMode)
    
    if (nightMode) {
      document.documentElement.classList.add('night-mode')
      document.body.classList.add('night-mode')
    } else {
      document.documentElement.classList.remove('night-mode')
      document.body.classList.remove('night-mode')
    }
  }, [nightMode])

  // Listen for system preference changes
  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
    
    const handleChange = (e) => {
      // Only auto-switch if user hasn't explicitly set a preference
      const saved = localStorage.getItem('routepilot-night-mode')
      if (saved === null) {
        setNightMode(e.matches)
      }
    }
    
    mediaQuery.addEventListener('change', handleChange)
    return () => mediaQuery.removeEventListener('change', handleChange)
  }, [])

  const toggleNightMode = () => {
    setNightMode(prev => !prev)
  }

  const value = {
    nightMode,
    toggleNightMode,
    setNightMode
  }

  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  )
}

/**
 * Night Mode Toggle Button Component
 * 
 * Can be placed anywhere in the app to toggle night mode.
 */
export function NightModeToggle({ className = '', size = 'medium' }) {
  const { nightMode, toggleNightMode } = useTheme()
  
  const sizeClasses = {
    small: 'toggle-small',
    medium: 'toggle-medium',
    large: 'toggle-large'
  }

  return (
    <button
      className={`night-mode-toggle ${sizeClasses[size]} ${className}`}
      onClick={toggleNightMode}
      title={nightMode ? 'Switch to Day Mode' : 'Switch to Night Mode'}
      aria-label={nightMode ? 'Switch to Day Mode' : 'Switch to Night Mode'}
    >
      <span className="toggle-icon">{nightMode ? '☀️' : '🌙'}</span>
      <span className="toggle-label">{nightMode ? 'Day' : 'Night'}</span>
    </button>
  )
}

export default ThemeContext
