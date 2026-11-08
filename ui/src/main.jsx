import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'
import { createConfiguredAuth } from './api/auth'
import { setAccessTokenProvider } from './api/session'
import { AuthGate } from './components/auth/AuthGate'

let authService
let authError = ''
try {
  authService = createConfiguredAuth()
  setAccessTokenProvider(authService.getAccessToken)
} catch {
  authError = 'Workspace configuration is unavailable. Please contact the workspace administrator.'
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <AuthGate service={authService} error={authError}><App /></AuthGate>
  </React.StrictMode>,
)
