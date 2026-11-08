import { useState } from 'react'
import PlatformIcon from '../ui/PlatformIcon'
import { getPlatform } from '../../lib/platforms'
import { formatLabel } from './workflowUtils'

export default function NewContent({ flow }) {
  const [title, setTitle] = useState('')
  const [selected, setSelected] = useState('')
  const pair = flow.pairs.find(entry => `${entry.destination}/${entry.format}` === selected) || flow.pairs[0]
  const platforms = [...new Set(flow.pairs.map(entry => entry.destination))]
  return <section className="cm-panel max-w-3xl space-y-5">
    <h1 className="cm-page-title">Start a piece of content</h1>
    <p className="cm-muted">Choose where it will go. You can adapt the approved version afterward.</p>
    <form className="space-y-5" onSubmit={event => { event.preventDefault(); if (pair && title.trim()) flow.create(title, pair) }}>
      <label className="cm-label">Title
        <input className="cm-input mt-2" required maxLength={500} value={title}
          onChange={event => setTitle(event.target.value)} placeholder="A working title for your idea" />
      </label>
      <fieldset className="space-y-3">
        <legend className="cm-label">Platform</legend>
        <div className="flex flex-wrap gap-2">
          {platforms.map(platform => <button type="button" key={platform}
            aria-pressed={pair?.destination === platform}
            className={`cm-chip ${pair?.destination === platform ? 'cm-chip-active' : ''}`}
            onClick={() => {
              const first = flow.pairs.find(entry => entry.destination === platform)
              setSelected(`${first.destination}/${first.format}`)
            }}><PlatformIcon platform={platform} size={18} />{getPlatform(platform)?.label || platform}</button>)}
        </div>
      </fieldset>
      <label className="cm-label">Content format
        <select className="cm-select mt-2" disabled={!pair}
          value={pair ? `${pair.destination}/${pair.format}` : ''}
          onChange={event => setSelected(event.target.value)}>
          {flow.pairs.filter(entry => entry.destination === pair?.destination).map(entry =>
            <option key={entry.format} value={`${entry.destination}/${entry.format}`}>{formatLabel(entry)}</option>)}
        </select>
      </label>
      {!pair && (flow.capabilitiesLoading
        ? <p role="status" className="cm-muted">Loading destinations…</p>
        : <p className="cm-status cm-status-warning">Destinations are unavailable. Retry loading before creating content.</p>)}
      <div className="cm-page-actions">
        <button className="cm-button cm-button-primary" disabled={!title.trim() || !pair || flow.busy}>Create content</button>
        <button type="button" className="cm-button cm-button-quiet" disabled={flow.busy}
          onClick={() => { setTitle(''); setSelected(''); flow.setScreen('list') }}>Cancel</button>
      </div>
    </form>
  </section>
}
