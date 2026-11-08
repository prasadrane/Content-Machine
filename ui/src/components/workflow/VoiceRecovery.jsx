import { createContext, useCallback, useContext, useRef, useState } from 'react'

const VoiceRecoveryContext = createContext(null)

export function VoiceRecoveryProvider({ identity, children }) {
  const [entries, setEntries] = useState([])
  const identityRef = useRef(identity)
  identityRef.current = identity
  const recover = useCallback((text, target) => {
    if (typeof text !== 'string' || !text || !target?.ownerId || !target?.itemId) return
    setEntries(previous => [...previous, { text, target }])
  }, [])
  const remove = useCallback(index => {
    setEntries(previous => previous.filter((_, position) => position !== index))
  }, [])
  const edit = useCallback((index, text) => {
    setEntries(previous => previous.map((entry, position) => position === index ? { ...entry, text } : entry))
  }, [])
  return <VoiceRecoveryContext.Provider value={{ identity, identityRef, entries, recover, remove, edit }}>
    {children}
  </VoiceRecoveryContext.Provider>
}

export function useVoiceRecovery() {
  return useContext(VoiceRecoveryContext)
}

export function VoiceRecoveryPanel() {
  const recovery = useVoiceRecovery()
  const [open, setOpen] = useState(false)
  const [message, setMessage] = useState('')
  const visible = (recovery?.entries || []).map((entry, index) => ({ ...entry, index }))
    .filter(entry => entry.target.ownerId === recovery.identity?.ownerId)
  if (!visible.length) return null
  const copy = async entry => {
    try {
      if (!navigator.clipboard?.writeText) throw new Error('Clipboard unavailable')
      await navigator.clipboard.writeText(entry.text)
      setMessage('Transcript copied')
    } catch {
      setMessage('Could not copy. Select the transcript and copy it manually.')
    }
  }
  return <section className="cm-panel space-y-3" aria-label="Recovered voice transcripts">
    <button type="button" className="cm-button cm-button-secondary" aria-expanded={open}
      onClick={() => setOpen(previous => !previous)}>
      {open ? 'Hide recovered transcripts' : `Show recovered transcripts (${visible.length})`}
    </button>
    {open && <>
      <p className="cm-muted">Copy a transcript into its original draft when you are ready.</p>
      {message && <p role="status" className="cm-muted">{message}</p>}
      <ul className="space-y-3">
        {visible.map(entry => <li key={entry.index} className="cm-subpanel space-y-2">
          <p className="cm-muted">{entry.target.field} · Item {entry.target.itemId} · Revision {entry.target.revision}</p>
          <label className="cm-label">Recovered transcript
            <textarea className="cm-textarea mt-2" value={entry.text}
              onChange={event => recovery.edit(entry.index, event.target.value)} />
          </label>
          <div className="cm-page-actions">
            <button type="button" className="cm-button cm-button-secondary" onClick={() => copy(entry)}>Copy transcript</button>
            <button type="button" className="cm-button cm-button-quiet" onClick={() => recovery.remove(entry.index)}>Dismiss</button>
          </div>
        </li>)}
      </ul>
    </>}
  </section>
}
