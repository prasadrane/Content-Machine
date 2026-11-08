import { useCallback, useEffect, useRef, useState } from 'react'
import { createRequestId, createSource, getSettings, saveProfile } from '../../api/settings'
import SettingsPageSource from './SettingsPageSource'

const profileFields = profile => ({ name: profile.name, role: profile.role, bio: profile.bio })

export default function SettingsPage({ onOpenLessons }) {
  const [saved, setSaved] = useState(null)
  const [profile, setProfile] = useState(null)
  const [sources, setSources] = useState([])
  const [newSource, setNewSource] = useState({ name: '', url: '' })
  const [dirtySources, setDirtySources] = useState({})
  const [sourceSaves, setSourceSaves] = useState({})
  const [generation, setGeneration] = useState(0)
  const [loading, setLoading] = useState(true)
  const [profileSaving, setProfileSaving] = useState(false)
  const [sourceSaving, setSourceSaving] = useState(false)
  const [loadError, setLoadError] = useState('')
  const [profileError, setProfileError] = useState('')
  const [sourceError, setSourceError] = useState('')
  const [profileNotice, setProfileNotice] = useState('')
  const [sourceNotice, setSourceNotice] = useState('')
  const profileRef = useRef(profile)
  const newSourceRef = useRef(newSource)
  const keys = useRef(new Map())
  const latestLoad = useRef(0)
  const profileDirty = Boolean(saved && profile) && JSON.stringify(profile) !== JSON.stringify(profileFields(saved))
  const sourceDirty = Object.values(dirtySources).some(Boolean)
  const sourceSavePending = Object.values(sourceSaves).some(Boolean)
  const newDirty = Boolean(newSource.name || newSource.url)
  const hasChanges = profileDirty || sourceDirty || newDirty

  const markSourceDirty = useCallback((id, dirty) => {
    setDirtySources(previous => previous[id] === dirty ? previous : { ...previous, [id]: dirty })
  }, [])
  const markSourceSaving = useCallback((id, saving) => {
    setSourceSaves(previous => ({ ...previous, [id]: saving }))
  }, [])
  const load = useCallback(async () => {
    const token = ++latestLoad.current
    setLoading(true)
    setLoadError('')
    try {
      const data = await getSettings()
      if (token !== latestLoad.current) return
      setSaved(data.profile)
      profileRef.current = profileFields(data.profile)
      setProfile(profileRef.current)
      setSources(data.sources)
      setDirtySources({})
      setGeneration(previous => previous + 1)
    } catch (failure) {
      if (token === latestLoad.current) setLoadError(failure.message || 'Could not load settings.')
    } finally {
      if (token === latestLoad.current) setLoading(false)
    }
  }, [])
  useEffect(() => {
    load()
    return () => { latestLoad.current += 1 }
  }, [load])
  useEffect(() => {
    if (!hasChanges) return
    const warn = event => { event.preventDefault(); event.returnValue = '' }
    window.addEventListener('beforeunload', warn)
    return () => window.removeEventListener('beforeunload', warn)
  }, [hasChanges])

  const keyFor = (operation, body) => {
    const signature = JSON.stringify([operation, body])
    if (!keys.current.has(signature)) keys.current.set(signature, createRequestId())
    return { signature, id: keys.current.get(signature) }
  }
  const changeProfile = (field, value) => {
    profileRef.current = { ...profileRef.current, [field]: value }
    setProfile(profileRef.current)
    setProfileNotice('')
  }
  const changeNewSource = (field, value) => {
    newSourceRef.current = { ...newSourceRef.current, [field]: value }
    setNewSource(newSourceRef.current)
    setSourceNotice('')
  }
  const save = async event => {
    event.preventDefault()
    const submitted = profileRef.current
    const body = { ...submitted, expected_revision: saved.revision }
    setProfileSaving(true)
    setProfileError('')
    setProfileNotice('')
    try {
      const key = keyFor('profile', body)
      const result = await saveProfile(body, key.id)
      keys.current.delete(key.signature)
      setSaved(result.profile)
      if (JSON.stringify(profileRef.current) === JSON.stringify(submitted)) {
        profileRef.current = profileFields(result.profile)
        setProfile(profileRef.current)
      }
      setProfileNotice('Profile saved')
    } catch (failure) {
      setProfileError(failure.message || 'Could not save your profile.')
    } finally {
      setProfileSaving(false)
    }
  }
  const addSource = async event => {
    event.preventDefault()
    const submitted = newSourceRef.current
    const body = { kind: 'rss', ...submitted, enabled: true }
    setSourceSaving(true)
    setSourceError('')
    setSourceNotice('')
    try {
      const key = keyFor('source', body)
      const result = await createSource(body, key.id)
      keys.current.delete(key.signature)
      setSources(previous => [...previous, result.source])
      if (JSON.stringify(newSourceRef.current) === JSON.stringify(submitted)) {
        newSourceRef.current = { name: '', url: '' }
        setNewSource(newSourceRef.current)
      }
      setSourceNotice('Source added')
    } catch (failure) {
      setSourceError(failure.message || 'Could not add this source.')
    } finally {
      setSourceSaving(false)
    }
  }
  const sourceSaved = useCallback(source => {
    setSources(previous => previous.map(entry => entry.source_id === source.source_id ? source : entry))
  }, [])

  return <div className="cm-page">
    <header className="cm-page-header">
      <div><h1 className="cm-page-title">Settings</h1>
        <p className="cm-page-description">Add optional author context and choose sources for discovery.</p></div>
      <button className="cm-button cm-button-secondary" disabled={loading || hasChanges || profileSaving || sourceSaving || sourceSavePending}
        onClick={load}>Refresh settings</button>
    </header>
    {loading && <p role="status" className="cm-muted">Loading settings…</p>}
    {loadError && <div role="alert" className="cm-status cm-status-error space-y-2">
      <p>{loadError}</p>{!saved && <button className="cm-button cm-button-secondary" onClick={load}>Try again</button>}
    </div>}
    {profile && <>
      <form className="cm-panel space-y-4" onSubmit={save}>
        <fieldset disabled={loading} className="space-y-4">
        <h2 className="cm-panel-title">About you</h2>
        <p className="cm-muted">These fields are optional. Add only facts you want to use as context.</p>
        <label className="cm-label">Name
          <input className="cm-input mt-2" value={profile.name} maxLength={200}
            onChange={event => changeProfile('name', event.target.value)} />
        </label>
        <label className="cm-label">Role
          <input className="cm-input mt-2" value={profile.role} maxLength={200}
            onChange={event => changeProfile('role', event.target.value)} />
        </label>
        <label className="cm-label">About you
          <textarea className="cm-textarea mt-2" value={profile.bio} maxLength={20000}
            onChange={event => changeProfile('bio', event.target.value)} />
        </label>
        {profileError && <p role="alert" className="cm-status cm-status-error">{profileError}</p>}
        {profileNotice && !profileDirty && <p role="status" className="cm-status cm-status-success">{profileNotice}</p>}
        {profileDirty && <p className="cm-muted">Unsaved profile changes</p>}
        <button className="cm-button cm-button-primary" disabled={profileSaving || !profileDirty}>Save profile</button>
        </fieldset>
      </form>
      <section className="cm-panel space-y-4">
        <h2 className="cm-panel-title">Discovery sources</h2>
        <p className="cm-muted">Configure RSS or Atom feeds you want to use. Turning a source off keeps previously saved evidence.</p>
        {sources.length === 0 && <p className="cm-muted">No sources configured yet.</p>}
        {sources.map(source => <SettingsPageSource key={`${source.source_id}:${generation}`} source={source}
          disabled={loading} onSaved={sourceSaved} onDirtyChange={markSourceDirty} onSavingChange={markSourceSaving} />)}
        <form className="cm-subpanel space-y-3" onSubmit={addSource}>
          <fieldset disabled={loading} className="space-y-3">
          <h3 className="cm-panel-title">Add a source</h3>
          <label className="cm-label">New source name
            <input className="cm-input mt-2" value={newSource.name} maxLength={200}
              onChange={event => changeNewSource('name', event.target.value)} />
          </label>
          <label className="cm-label">New RSS or Atom URL
            <input className="cm-input mt-2" type="url" value={newSource.url} maxLength={2000}
              onChange={event => changeNewSource('url', event.target.value)} />
          </label>
          {sourceError && <p role="alert" className="cm-status cm-status-error">{sourceError}</p>}
          {sourceNotice && !newDirty && <p role="status" className="cm-status cm-status-success">{sourceNotice}</p>}
          <button className="cm-button cm-button-secondary" disabled={sourceSaving || !newSource.name.trim() || !newSource.url.trim()}>Add source</button>
          </fieldset>
        </form>
      </section>
      <section className="cm-panel space-y-3">
        <h2 className="cm-panel-title">Writing preferences</h2>
        <p className="cm-muted">Manage your reusable writing preferences in Lessons.</p>
        {onOpenLessons && <button className="cm-button cm-button-secondary" onClick={onOpenLessons}>Open writing preferences</button>}
      </section>
    </>}
  </div>
}
