import React, { useEffect, useState } from 'react'
import { GuestReadiness } from './GuestReadiness'
import { GuestTransfer } from './GuestTransfer'
import { clearGuestProof, retainGuestProof } from './guestProof'

export function AuthGate({ service, error: configurationError, children }) {
  const [state, setState] = useState({ loading: true, session: null, error: '', revision: 0, signingOut: false })
  const [pending, setPending] = useState(false)
  useEffect(() => {
    if (!service || service.mode !== 'hosted') return undefined
    let active = true
    let events = 0
    const unsubscribe = service.onAuthStateChange((event, session) => {
      events += 1
      if (active) setState(previous => previous.signingOut ? previous : ({ ...previous, loading: false, session, error: '', revision: previous.revision + (previous.session?.user?.id === session?.user?.id ? 0 : 1) }))
    })
    service.getSession().then(session => {
      if (active && events === 0) setState(previous => ({ ...previous, loading: false, session }))
    }).catch(error => {
      if (active && events === 0) setState(previous => ({ ...previous, loading: false, error: error.message }))
    })
    return () => { active = false; unsubscribe() }
  }, [service])

  useEffect(() => {
    const expiry = state.session?.expires_at
    if (!expiry) return undefined
    const remaining = expiry * 1000 - Date.now()
    const expire = () => { clearGuestProof(); setState(previous => ({ ...previous, session: null, error: 'Your session expired. Please sign in again.', revision: previous.revision + 1 })) }
    if (remaining <= 0) { expire(); return undefined }
    const timer = window.setTimeout(expire, Math.min(remaining, 2147483647))
    return () => window.clearTimeout(timer)
  }, [state.session])

  if (configurationError || !service) return <p role="alert">{configurationError || 'Workspace configuration is unavailable.'}</p>
  if (service.mode === 'local') return children
  if (state.loading) return <p role="status">Loading your workspace…</p>

  const run = async action => {
    if (pending) return
    setPending(true)
    setState(previous => ({ ...previous, error: '' }))
    try { await action() } catch (error) { setState(previous => ({ ...previous, error: error.message || 'Unable to sign in.' })) }
    finally { setPending(false) }
  }
  const signOut = async () => {
    if (pending) return
    // Remove private state before waiting for the network or SDK event.
    setPending(true)
    clearGuestProof()
    setState(previous => ({ ...previous, session: null, signingOut: true, error: '', revision: previous.revision + 1 }))
    try {
      await service.signOut()
      setState(previous => ({ ...previous, signingOut: false }))
    } catch {
      setState(previous => ({ ...previous, error: 'Sign out failed. You may still be signed in; retry before leaving or refreshing this page.' }))
    } finally { setPending(false) }
  }
  if (state.signingOut) return <main className="cm-page"><section className="cm-panel">
    <h1 className="cm-page-title">Signing out</h1>
    {state.error && <p role="alert">{state.error}</p>}
    <button type="button" className="cm-button cm-button-secondary" disabled={pending} onClick={signOut}>Retry sign out</button>
  </section></main>
  if (!state.session?.user?.id) return <main className="cm-page">
    <section className="cm-panel">
      <h1 className="cm-page-title">Welcome to Content Machine</h1>
      <p className="cm-muted">Sign in for your private workspace, or try a guest workspace.</p>
      {state.error && <p role="alert">{state.error}</p>}
      <div className="cm-page-actions">
        <button type="button" className="cm-button cm-button-primary" disabled={pending} onClick={() => run(() => service.signInWithGoogle(window.location.origin + window.location.pathname))}>Continue with Google</button>
        <button type="button" className="cm-button cm-button-secondary" disabled={pending} onClick={() => run(() => service.signInAsGuest())}>Continue as guest</button>
      </div>
    </section>
  </main>
  return <>
    <div className="cm-panel">
      {state.session.user.is_anonymous && <>
        <p>Guest workspace. You can copy current guest work into a Google account as new unapproved drafts.</p>
        <button type="button" className="cm-button cm-button-secondary" disabled={pending} onClick={() => run(async () => {
          const current = await service.getSession()
          retainGuestProof(current)
          try { await service.signInWithGoogle(window.location.origin + window.location.pathname) }
          catch (error) { clearGuestProof(); throw error }
        })}>Copy guest work with Google</button>
      </>}
      {state.error && <p role="alert">{state.error}</p>}
      <button type="button" className="cm-button cm-button-secondary" disabled={pending} onClick={signOut}>Sign out</button>
    </div>
    <React.Fragment key={`${state.session.user.id}:${state.revision}`}>
      {state.session.user.is_anonymous ? <GuestReadiness>{children}</GuestReadiness> : <>
        <GuestTransfer session={state.session} />{children}
      </>}
    </React.Fragment>
  </>
}
