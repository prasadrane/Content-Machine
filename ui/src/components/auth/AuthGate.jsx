import React, { useEffect, useRef, useState } from 'react'
import { onUnauthorized } from '../../api/session'
import { GuestReadiness } from './GuestReadiness'
import { GuestTransfer } from './GuestTransfer'
import WelcomeLanding from './WelcomeLanding'
import { clearGuestProof, retainGuestProof } from './guestProof'

export function AuthGate({ service, error: configurationError, children }) {
  const [state, setState] = useState({ loading: true, session: null, error: '', revision: 0, signingOut: false })
  const [pending, setPending] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const signOutButton = useRef(null)
  const dialog = useRef(null)
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

  // An unrecoverable 401 from the API (after one refresh retry) returns to sign-in.
  useEffect(() => {
    if (!service || service.mode !== 'hosted') return undefined
    return onUnauthorized(() => {
      clearGuestProof()
      setConfirming(false)
      setState(previous => previous.session ? ({ ...previous, session: null, error: 'Your session expired. Please sign in again.', revision: previous.revision + 1 }) : previous)
    })
  }, [service])

  useEffect(() => {
    if (!confirming) return undefined
    const root = dialog.current
    root?.querySelector('button')?.focus()
    const onKey = event => {
      if (event.key === 'Escape') { event.stopPropagation(); setConfirming(false); signOutButton.current?.focus() }
      else if (event.key === 'Tab' && root) {
        const buttons = [...root.querySelectorAll('button:not(:disabled)')]
        if (!buttons.length) return
        const first = buttons[0], last = buttons[buttons.length - 1]
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus() }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus() }
      }
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [confirming])

  useEffect(() => {
    const expiry = state.session?.expires_at
    if (!expiry) return undefined
    const remaining = expiry * 1000 - Date.now()
    const expire = () => { clearGuestProof(); setState(previous => ({ ...previous, session: null, error: 'Your session expired. Please sign in again.', revision: previous.revision + 1 })) }
    if (remaining <= 0) { expire(); return undefined }
    const timer = window.setTimeout(expire, Math.min(remaining, 2147483647))
    return () => window.clearTimeout(timer)
  }, [state.session])

  // A deep link to one user's item must not outlive their session: the next
  // user would land on a "not found" screen for an item they cannot own.
  const signedOut = !!service && service.mode === 'hosted' && !state.loading && !state.session?.user?.id
  useEffect(() => {
    if (signedOut && window.location.hash.startsWith('#/workflow/items/')) {
      window.history.replaceState(null, '', window.location.pathname + window.location.search + '#/workflow')
    }
  }, [signedOut])

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
  // Child components warn about unsaved work by cancelling `beforeunload`;
  // probe that shared signal rather than tracking dirty state a second time.
  const hasUnsavedWork = () => {
    const probe = new Event('beforeunload', { cancelable: true })
    window.dispatchEvent(probe)
    return probe.defaultPrevented
  }
  const requestSignOut = () => {
    if (pending) return
    if (state.session?.user?.is_anonymous || hasUnsavedWork()) setConfirming(true)
    else signOut()
  }
  const copyGuestWork = () => run(async () => {
    setConfirming(false)
    const current = await service.getSession()
    retainGuestProof(current)
    try { await service.signInWithGoogle(window.location.origin + window.location.pathname) }
    catch (error) { clearGuestProof(); throw error }
  })
  const signOut = async () => {
    if (pending) return
    setConfirming(false)
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
  if (!state.session?.user?.id) return <WelcomeLanding error={state.error} pending={pending}
    onGoogle={() => run(() => service.signInWithGoogle(window.location.origin + window.location.pathname))}
    onGuest={() => run(() => service.signInAsGuest())} />
  return <>
    <div className="cm-panel">
      {state.session.user.is_anonymous && <>
        <p>Guest workspace. You can copy current guest work into a Google account as new unapproved drafts.</p>
        <button type="button" className="cm-button cm-button-secondary" disabled={pending} onClick={copyGuestWork}>Copy guest work with Google</button>
      </>}
      {state.error && <p role="alert">{state.error}</p>}
      <button type="button" ref={signOutButton} className="cm-button cm-button-secondary" disabled={pending} onClick={requestSignOut}>Sign out</button>
      {confirming && <div ref={dialog} role="alertdialog" aria-modal="true" aria-labelledby="cm-signout-title" aria-describedby="cm-signout-desc" className="cm-status cm-status-warning space-y-2">
        <h2 id="cm-signout-title" className="cm-panel-title">Sign out?</h2>
        {state.session.user.is_anonymous
          ? <p id="cm-signout-desc">Guest work becomes unreachable after you sign out. Copy it to a Google account first to keep it.</p>
          : <p id="cm-signout-desc">You have unsaved changes. Signing out will discard them.</p>}
        <div className="cm-page-actions">
          {state.session.user.is_anonymous && <button type="button" className="cm-button cm-button-primary" disabled={pending} onClick={copyGuestWork}>Copy guest work with Google</button>}
          <button type="button" className="cm-button cm-button-secondary" onClick={() => { setConfirming(false); signOutButton.current?.focus() }}>Cancel</button>
          <button type="button" className="cm-button cm-button-secondary" disabled={pending} onClick={signOut}>Sign out anyway</button>
        </div>
      </div>}
    </div>
    <React.Fragment key={`${state.session.user.id}:${state.revision}`}>
      {state.session.user.is_anonymous ? <GuestReadiness>{children}</GuestReadiness> : <>
        <GuestTransfer session={state.session} />{children}
      </>}
    </React.Fragment>
  </>
}
