import { useState } from 'react'
import { ArrowRight, Plus, RefreshCw } from 'lucide-react'
import PlatformIcon from '../ui/PlatformIcon'
import { formatLabel } from './workflowUtils'

export const STAGES = [
  ['idea', 'Idea'], ['draft_review', 'Draft & review'], ['approve', 'Approve'], ['export', 'Export'],
]

export default function ContentList({ flow }) {
  const [query, setQuery] = useState('')
  const saved = flow.items || []
  const search = query.trim().toLocaleLowerCase()
  const matching = saved.filter(item => [item.title, formatLabel(item),
    STAGES.find(([id]) => id === item.stage)?.[1]].some(value => value?.toLocaleLowerCase().includes(search)))
  const reference = item => {
    const short = item.item_id.slice(-8)
    return saved.some(other => other.item_id !== item.item_id && other.item_id.slice(-8) === short)
      ? item.item_id : short
  }
  return <>
    <header className="cm-page-header">
      <div>
        <h1 className="cm-page-title">Your content</h1>
        <p className="cm-page-description">Turn your engineering ideas into something worth publishing.</p>
      </div>
      <button className="cm-button cm-button-primary" disabled={flow.busy}
        onClick={() => flow.setScreen('new')}><Plus size={18} aria-hidden="true" />New content</button>
    </header>
    <section aria-label="Saved work" className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="cm-panel-title">Ideas and drafts</h2>
        <button className="cm-button cm-button-quiet" disabled={flow.loading || flow.busy}
          onClick={flow.refresh}><RefreshCw size={16} aria-hidden="true" />Refresh</button>
      </div>
      {flow.loading && <p role="status" className="cm-muted">Loading saved content…</p>}
      {flow.error && saved.length > 0 && <p className="cm-status cm-status-warning">Showing previously loaded saved content. Refresh to try again.</p>}
      {saved.length > 0 && <div className="flex flex-wrap items-end gap-2">
        <label className="cm-label flex-1 min-w-0">Search saved content
          <input type="search" className="cm-input mt-2" value={query} onChange={event => setQuery(event.target.value)} />
        </label>
        {query && <button className="cm-button cm-button-quiet" onClick={() => setQuery('')}>Clear search</button>}
      </div>}
      {flow.items?.length === 0 && !flow.loading && !flow.error &&
        <div className="cm-empty">No saved content yet. Start with an idea or an existing draft.</div>}
      {saved.length > 0 && matching.length === 0 && <p className="cm-muted">No saved content matches this search.</p>}
      {matching.map((item, index) => {
        const duplicate = saved.filter(other => other.title === item.title).length > 1
        return <article key={item.item_id} className="cm-panel flex flex-wrap items-center justify-between gap-4">
        <div className="min-w-0 space-y-2">
          <h3 className="cm-panel-title break-words">{item.title}</h3>
          {item.guest_example_label === 'Demo example' &&
            <span className="cm-badge">Demo example</span>}
          {duplicate && <p className="cm-muted break-all">Reference {reference(item)}</p>}
          <p className="cm-muted flex flex-wrap items-center gap-2">
            <PlatformIcon platform={item.destination} size={18} />{formatLabel(item)}
            <span aria-hidden="true">·</span>{STAGES.find(([id]) => id === item.stage)?.[1] || 'Saved'}
          </p>
          <p className="cm-muted">Revision {item.working_revision} · {new Date(item.updated_at).toLocaleString()}</p>
        </div>
        <button className={`cm-button ${index === 0 ? 'cm-button-primary' : 'cm-button-secondary'}`}
          disabled={flow.busy} onClick={() => flow.open(item.item_id)}
          aria-label={`Resume ${item.title}${duplicate ? `, reference ${reference(item)}` : ''}`}>
          Resume<ArrowRight size={16} aria-hidden="true" />
        </button>
      </article>})}
    </section>
  </>
}
