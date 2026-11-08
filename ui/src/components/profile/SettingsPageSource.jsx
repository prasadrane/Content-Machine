import { useEffect, useRef, useState } from 'react'
import { createRequestId, updateSource } from '../../api/settings'

const fields = source => ({ name: source.name, url: source.url, enabled: source.enabled })

export default function SettingsPageSource({ source, onSaved, onDirtyChange, onSavingChange, disabled = false }) {
  const [draft, setDraft] = useState(() => fields(source))
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const keys = useRef(new Map())
  const dirty = JSON.stringify(draft) !== JSON.stringify(fields(source))

  useEffect(() => {
    onDirtyChange(source.source_id, dirty)
  }, [source.source_id, dirty, onDirtyChange])

  const update = (name, value) => {
    setDraft(previous => ({ ...previous, [name]: value }))
    setNotice('')
  }

  async function save(event) {
    event.preventDefault()
    setSaving(true)
    onSavingChange(source.source_id, true)
    setError('')
    setNotice('')
    const body = { expected_revision: source.revision, ...draft }
    const signature = JSON.stringify(body)
    try {
      if (!keys.current.has(signature)) keys.current.set(signature, createRequestId())
      const result = await updateSource(source.source_id, body, keys.current.get(signature))
      keys.current.delete(signature)
      onSaved(result.source)
      setNotice('Source saved')
    } catch (failure) {
      setError(failure.message || 'Could not save this source.')
    } finally {
      setSaving(false)
      onSavingChange(source.source_id, false)
    }
  }

  return <fieldset className="cm-subpanel space-y-3" disabled={disabled}>
    <legend className="cm-label">{source.name} source</legend>
    <label className="cm-label">Source name
      <input className="cm-input mt-2" value={draft.name} maxLength={200}
        onChange={event => update('name', event.target.value)} />
    </label>
    <label className="cm-label">RSS or Atom URL
      <input className="cm-input mt-2" type="url" value={draft.url} maxLength={2000}
        onChange={event => update('url', event.target.value)} />
    </label>
    <label className="flex items-center gap-2">
      <input type="checkbox" checked={draft.enabled} onChange={event => update('enabled', event.target.checked)} />
      Enabled for discovery
    </label>
    {error && <p role="alert" className="cm-status cm-status-error">{error}</p>}
    {notice && !dirty && <p role="status" className="cm-status cm-status-success">{notice}</p>}
    {dirty && <p className="cm-muted">Unsaved source changes</p>}
    <button type="button" className="cm-button cm-button-secondary" disabled={saving || !dirty || !draft.name.trim() || !draft.url.trim()}
      onClick={save}>Save source</button>
  </fieldset>
}
