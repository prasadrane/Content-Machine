import React, { useEffect, useState } from 'react'
import { bootstrapGuest } from '../../api/guests'

export function GuestReadiness({ children }) {
  const [state, setState] = useState({ ready: false, error: false })
  const [attempt, setAttempt] = useState(0)
  useEffect(() => {
    let active = true
    setState({ ready: false, error: false })
    bootstrapGuest().then(() => { if (active) setState({ ready: true, error: false }) })
      .catch(() => { if (active) setState({ ready: false, error: true }) })
    return () => { active = false }
  }, [attempt])
  if (state.ready) return children
  return <section className="cm-panel">
    {state.error ? <>
      <p role="alert">Guest workspace setup failed. Your saved work has not been changed.</p>
      <button type="button" className="cm-button cm-button-secondary" onClick={() => setAttempt(value => value + 1)}>Retry guest setup</button>
    </> : <p role="status">Preparing your guest workspace…</p>}
  </section>
}
