import { useEffect, useRef, useState } from 'react'
import { ExternalLink, RefreshCw, Search } from 'lucide-react'
import { refreshDiscovery } from '../../api/discovery'

const messages = {
  no_sources: 'Add an enabled source in Settings to find ideas.',
  unavailable: 'Discovery is unavailable. Your notes and saved work remain available.',
  empty: 'No new ideas were returned by your sources.',
  history_unavailable: 'No new ideas were returned. Previously found ideas are unavailable in this view.',
}

function webUrl(value) {
  try {
    const url = new URL(value)
    return ['http:', 'https:'].includes(url.protocol) && !url.username && !url.password ? value : null
  } catch {
    return null
  }
}

export default function DiscoveryPane({ attachedSources = [], onUse, onManageSources, disabled = false }) {
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [query, setQuery] = useState('')
  const active = useRef(true)
  const running = useRef(false)
  useEffect(() => {
    active.current = true
    return () => { active.current = false }
  }, [])

  async function refresh() {
    if (running.current) return
    running.current = true
    setLoading(true)
    setError('')
    try {
      const next = await refreshDiscovery()
      if (!active.current) return
      setResult(previous => {
        if (['failed', 'unavailable'].includes(next.status) && previous?.items.length) {
          return { ...next, items: previous.items, stale: true }
        }
        return next
      })
    } catch (failure) {
      if (active.current) setError(failure.message || 'Could not find ideas. Try again.')
    } finally {
      running.current = false
      if (active.current) setLoading(false)
    }
  }

  const search = query.trim().toLocaleLowerCase()
  const items = (result?.items || []).filter(item =>
    [item.title, item.excerpt, item.source_name].some(value => (value || '').toLocaleLowerCase().includes(search)))
  return <section aria-label="Discover ideas" className="cm-subpanel space-y-4">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h2 className="cm-panel-title">Find ideas from your sources</h2>
        <p className="cm-muted">Use a source as evidence, then add your own perspective.</p>
      </div>
      <div className="cm-page-actions">
        {onManageSources && <button type="button" className="cm-button cm-button-quiet" onClick={onManageSources}>Manage sources</button>}
        <button type="button" className="cm-button cm-button-secondary" disabled={loading}
          onClick={refresh}><RefreshCw size={16} aria-hidden="true" />{result ? 'Refresh ideas' : 'Find ideas'}</button>
      </div>
    </div>
    {loading && <p role="status" className="cm-muted">Checking your sources…</p>}
    {error && <p role="alert" className="cm-status cm-status-error">{error}</p>}
    {result?.incomplete && <p role="status" className="cm-status cm-status-warning">Time limit reached; some sources were skipped. Refresh again to continue.</p>}
    {result?.stale && <p className="cm-muted">Showing earlier results from this session.</p>}
    {result && messages[result.status] && <p className="cm-status cm-status-info">{messages[result.status]}</p>}
    {result?.errors?.map((failure, index) => <p key={`${failure.source_id}-${index}`} className="cm-status cm-status-warning">
      {failure.source_name} — {failure.message}
    </p>)}
    {result?.items?.length > 0 && result.unchanged_sources?.map(source =>
      <p key={source.source_id} className="cm-muted">{source.source_name} returned no new items. Previous results are unavailable.</p>)}
    {result?.items?.length > 0 && <>
      <div className="flex flex-wrap items-end gap-2">
        <label className="cm-label flex-1 min-w-0">Search ideas
          <span className="relative block mt-2">
            <Search aria-hidden="true" size={16} className="absolute left-3 top-3.5" />
            <input type="search" className="cm-input pl-10" value={query} onChange={event => setQuery(event.target.value)} />
          </span>
        </label>
        {query && <button type="button" className="cm-button cm-button-quiet" onClick={() => setQuery('')}>Clear search</button>}
      </div>
      {!items.length && <p className="cm-muted">No ideas match this search.</p>}
      {items.map(item => {
        const added = attachedSources.some(source => source.source_id === item.source_id && source.url === item.url)
        const href = webUrl(item.url)
        const full = attachedSources.length >= 200
        return <article key={`${item.source_id}-${item.url}`} className="cm-panel space-y-3">
          <h3 className="cm-panel-title">{item.title}</h3>
          <p className="cm-muted">{item.source_name}</p>
          {item.excerpt ? <p className="cm-prose whitespace-pre-wrap">{item.excerpt}</p> :
            <p className="cm-muted">No excerpt available from this source.</p>}
          <div className="cm-page-actions">
            <button type="button" className="cm-button cm-button-primary" disabled={disabled || added || full || !href}
              aria-label={`${added ? 'Already added' : 'Use'} ${item.title}`}
              onClick={() => onUse({ source_id: item.source_id, url: item.url, title: item.title,
                excerpt: item.excerpt, fetched_at: item.fetched_at })}>{added ? 'Added' : 'Use this idea'}</button>
            {href && <a className="cm-link inline-flex items-center gap-1" href={href} target="_blank" rel="noopener noreferrer">
              Open source<ExternalLink size={14} aria-hidden="true" />
            </a>}
          </div>
          {full && !added && <p className="cm-muted">This draft has reached the source limit.</p>}
        </article>
      })}
    </>}
  </section>
}
