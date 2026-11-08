import { useEffect, useRef, useState } from 'react'
import { Clock, Plus } from 'lucide-react'
import * as api from '../../api/preferences'

function newRequestId() {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID()
  if (!globalThis.crypto?.getRandomValues) throw new Error('This browser cannot create a request ID.')
  return Array.from(globalThis.crypto.getRandomValues(new Uint8Array(16)),
    byte => byte.toString(16).padStart(2, '0')).join('')
}

const originLabel = {
  manual: 'Added by you', item: 'Suggested from saved content', legacy: 'Imported local lesson',
}
const statusLabel = { active: 'Active', pending: 'Pending suggestion', stopped: 'Stopped', rejected: 'Dismissed' }

export default function PreferencesPage() {
  const [preferences, setPreferences] = useState(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [editor, setEditor] = useState(null)
  const [text, setText] = useState('')
  const [history, setHistory] = useState({})
  const pending = useRef(new Map())
  const mounted = useRef(true)
  const loadSequence = useRef(0)
  const historySequence = useRef(new Map())
  const busyRef = useRef(false)

  async function load() {
    const sequence = ++loadSequence.current
    for (const [id, value] of historySequence.current) historySequence.current.set(id, value + 1)
    setHistory({})
    setLoading(true)
    setError('')
    try {
      const result = await api.getPreferences()
      if (mounted.current && sequence === loadSequence.current) setPreferences(result.preferences)
    } catch (failure) {
      if (mounted.current && sequence === loadSequence.current) setError(failure.message || 'Could not load preferences.')
    } finally {
      if (mounted.current && sequence === loadSequence.current) setLoading(false)
    }
  }
  useEffect(() => {
    mounted.current = true
    load()
    return () => { mounted.current = false; loadSequence.current += 1 }
  }, [])

  async function mutate(action, preference, body) {
    if (busyRef.current) return
    busyRef.current = true
    setBusy(true)
    setError('')
    setNotice('')
    const id = preference?.preference_id || ''
    const signature = JSON.stringify([action, id, body])
    try {
      if (!pending.current.has(signature)) pending.current.set(signature, newRequestId())
      const key = pending.current.get(signature)
      const call = {
        create: () => api.createPreference(body, key),
        edit: () => api.editPreference(id, body, key),
        activate: () => api.activatePreference(id, body, key),
        stop: () => api.stopPreference(id, body, key),
        reject: () => api.rejectPreference(id, body, key),
      }[action]
      const result = await call()
      pending.current.delete(signature)
      if (!mounted.current) return
      historySequence.current.set(id, (historySequence.current.get(id) || 0) + 1)
      setPreferences(previous => {
        const rows = previous || []
        const exists = rows.some(entry => entry.preference_id === result.preference.preference_id)
        return exists ? rows.map(entry => entry.preference_id === result.preference.preference_id
          ? result.preference : entry) : [...rows, result.preference]
      })
      setHistory(previous => { const next = { ...previous }; delete next[id]; return next })
      setEditor(null)
      setText('')
      setNotice('Preference saved')
    } catch (failure) {
      if (mounted.current) setError(failure.message || 'Could not save this preference.')
    } finally {
      busyRef.current = false
      if (mounted.current) setBusy(false)
    }
  }
  async function showHistory(preference) {
    const id = preference.preference_id
    const sequence = (historySequence.current.get(id) || 0) + 1
    historySequence.current.set(id, sequence)
    if (history[id]) {
      setHistory(previous => { const next = { ...previous }; delete next[id]; return next })
      return
    }
    setError('')
    try {
      const result = await api.getPreferenceHistory(id)
      if (mounted.current && historySequence.current.get(id) === sequence) {
        setHistory(previous => ({ ...previous, [id]: result.events }))
      }
    } catch (failure) {
      if (mounted.current && historySequence.current.get(id) === sequence) {
        setError(failure.message || 'Could not load preference history.')
      }
    }
  }
  function startEdit(preference = null) {
    setEditor({ preference })
    setText(preference?.text || '')
    setError('')
    setNotice('')
  }
  function save(event) {
    event.preventDefault()
    if (!text.trim()) return
    const preference = editor.preference
    const body = preference
      ? { text, expected_revision: preference.revision, consent: true }
      : { text, consent: true }
    mutate(preference ? 'edit' : 'create', preference, body)
  }
  const active = preferences?.filter(entry => entry.status === 'active') || []
  const suggestions = preferences?.filter(entry => entry.status === 'pending') || []
  const past = preferences?.filter(entry => ['stopped', 'rejected'].includes(entry.status)) || []
  const card = preference => <article key={preference.preference_id} className="cm-subpanel space-y-3">
    <p className="cm-prose whitespace-pre-wrap">{preference.text}</p>
    <p className="cm-muted"><span>{statusLabel[preference.status]}</span> · <span>{originLabel[preference.origin]}</span></p>
    {preference.status === 'pending' && preference.conflict_preference_id &&
      <p className="cm-status cm-status-warning">This suggestion overlapped with an active preference when it was created.</p>}
    <div className="cm-page-actions">
      {preference.status === 'active' && <>
        <button className="cm-button cm-button-secondary" disabled={busy || loading || Boolean(editor)} onClick={() => startEdit(preference)}>Edit</button>
        <button className="cm-button cm-button-quiet" disabled={busy || loading || Boolean(editor)} onClick={() => mutate('stop', preference,
          { expected_revision: preference.revision })}>Stop using</button>
      </>}
      {preference.status === 'pending' && <>
        <button className="cm-button cm-button-secondary" disabled={busy || loading || Boolean(editor)} onClick={() => mutate('activate', preference,
          { expected_revision: preference.revision, consent: true })}>Use suggestion</button>
        <button className="cm-button cm-button-quiet" disabled={busy || loading || Boolean(editor)} onClick={() => startEdit(preference)}>
          Edit suggestion
        </button>
        <button className="cm-button cm-button-quiet" disabled={busy || loading || Boolean(editor)} onClick={() => mutate('reject', preference,
          { expected_revision: preference.revision })}>Dismiss suggestion</button>
      </>}
      {preference.status === 'stopped' && <button className="cm-button cm-button-secondary" disabled={busy || loading || Boolean(editor)}
        onClick={() => mutate('activate', preference, { expected_revision: preference.revision, consent: true })}>
        Use again
      </button>}
      <button className="cm-button cm-button-quiet" disabled={busy || loading} onClick={() => showHistory(preference)}>
        <Clock size={16} aria-hidden="true" />{history[preference.preference_id] ? 'Hide history' : 'History'}
      </button>
    </div>
    {history[preference.preference_id] && <ol className="cm-divider space-y-2">
      {history[preference.preference_id].map(event => <li key={event.revision} className="cm-muted">
        Revision {event.revision} · {statusLabel[event.status]} · {event.text}
      </li>)}
    </ol>}
  </article>

  return <div className="cm-page">
    <header className="cm-page-header">
      <div>
        <h1 className="cm-page-title">Writing preferences</h1>
        <p className="cm-page-description">Save reusable guidance for future content. You can change it whenever you like.</p>
      </div>
      <button className="cm-button cm-button-primary" disabled={busy || loading || !preferences || Boolean(editor)} onClick={() => startEdit()}>
        <Plus size={18} aria-hidden="true" />Add preference
      </button>
    </header>
    {error && <div className="cm-status cm-status-error" role="alert">{error}
      {preferences === null && <button className="cm-button cm-button-quiet" onClick={load}>Try again</button>}
    </div>}
    {notice && <p role="status" className="cm-status cm-status-success">{notice}</p>}
    {editor && <form className="cm-panel space-y-4" onSubmit={save}>
      <h2 className="cm-panel-title">{editor.preference ? 'Edit preference' : 'Add preference'}</h2>
      <label className="cm-label">Preference text
        <textarea className="cm-textarea mt-2" value={text} maxLength={10000} disabled={busy}
          onChange={event => setText(event.target.value)} />
      </label>
      <p className="cm-muted">Future AI requests use your active preferences. Saved drafts and approved versions stay unchanged.</p>
      <p className="cm-muted">Keep factual corrections in the content they belong to. Save a preference only for reusable writing guidance.</p>
      <div className="cm-page-actions">
        <button className="cm-button cm-button-primary" disabled={busy || loading || !text.trim()}>Save and use</button>
        <button type="button" className="cm-button cm-button-quiet" disabled={busy} onClick={() => setEditor(null)}>Cancel</button>
      </div>
    </form>}
    {loading && <p role="status" className="cm-muted">Loading preferences…</p>}
    {preferences && <>
      <section className="cm-panel space-y-4" aria-label="Active preferences">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="cm-panel-title">Active preferences</h2>
          <button className="cm-button cm-button-quiet" disabled={busy || loading} onClick={load}>Refresh</button>
        </div>
        {active.length ? active.map(card) : <p className="cm-muted">No active preferences yet.</p>}
      </section>
      {suggestions.length > 0 && <section className="cm-panel space-y-4" aria-label="Pending suggestions">
        <h2 className="cm-panel-title">Pending suggestions</h2>
        <p className="cm-muted">Choose individually which suggestions to use.</p>
        {suggestions.map(card)}
      </section>}
      {past.length > 0 && <details className="cm-panel space-y-4">
        <summary className="cursor-pointer font-medium">Stopped and dismissed</summary>
        {past.map(card)}
      </details>}
    </>}
  </div>
}
