import { X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { getVersion } from '../../api/workflow'

const purposeLabels = {
  review: 'Review',
  skip_review: 'Review skipped',
  approval: 'Approval',
  restore: 'Restored',
  adaptation: 'Adaptation',
}

export default function HistoryPanel({ itemId, currentArtifact, history, busy, dirty, onRestore, onClose }) {
  const [snapshot, setSnapshot] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const sequence = useRef(0)
  const mounted = useRef(true)
  useEffect(() => {
    mounted.current = true
    setSnapshot(null)
    return () => { mounted.current = false; sequence.current += 1 }
  }, [itemId])
  const compare = async versionId => {
    const request = ++sequence.current
    setLoading(true)
    setError('')
    try {
      const { version } = await getVersion(itemId, versionId)
      if (!mounted.current || sequence.current !== request) return
      if (version?.item_id !== itemId || version.version_id !== versionId ||
          !Array.isArray(version.artifact?.segments)) throw new Error('The snapshot does not match this item.')
      setSnapshot(version)
    } catch (failure) {
      if (mounted.current && sequence.current === request) setError(failure.message || 'Could not load this snapshot. Try Compare again.')
    } finally {
      if (mounted.current && sequence.current === request) setLoading(false)
    }
  }
  return <section className="cm-panel space-y-4" aria-label="Version history">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h2 className="cm-panel-title">Version history</h2>
        <p className="cm-muted">Restoring creates a new draft revision that needs approval before export.</p>
      </div>
      <button type="button" className="cm-button cm-button-quiet" onClick={onClose}>
        <X size={16} aria-hidden="true" />Close history
      </button>
    </div>
    {dirty && <p className="cm-status cm-status-warning">Save your changes before restoring a version.</p>}
    {loading && <p role="status" className="cm-muted">Loading snapshot. Your current draft is preserved.</p>}
    {error && <p role="alert" className="cm-status cm-status-error">{error}</p>}
    {snapshot && <section aria-label="Snapshot comparison" className="cm-subpanel space-y-4">
      <h3 className="cm-panel-title">Compare revision {snapshot.revision} with your current draft</h3>
      <p className="cm-muted">This saved snapshot is read-only. Viewing it does not approve or change your draft.</p>
      <div className="grid gap-4 md:grid-cols-2">
        <div className="space-y-3"><h4 className="cm-label">Saved snapshot</h4>
          {snapshot.artifact.segments.map((text, index) => <pre key={index} className="cm-prose whitespace-pre-wrap break-words">{text}</pre>)}
          <details className="cm-divider"><summary className="cursor-pointer">Saved idea context</summary>
            {[snapshot.context?.notes, snapshot.context?.experience, snapshot.context?.interpretation].filter(Boolean)
              .map((text, index) => <pre key={index} className="cm-prose whitespace-pre-wrap">{text}</pre>)}
            {snapshot.context?.sources?.map((source, index) => <p key={index} className="cm-muted">{source.title}</p>)}
          </details>
        </div>
        <div className="space-y-3"><h4 className="cm-label">Current draft{dirty ? ' (unsaved changes)' : ''}</h4>
          {currentArtifact?.segments?.map((text, index) => <pre key={index} className="cm-prose whitespace-pre-wrap break-words">{text}</pre>)}
        </div>
      </div>
    </section>}
    {history.versions.length === 0 && <p className="cm-empty">No saved snapshots yet.</p>}
    <ol className="space-y-3">
      {history.versions.map(version => {
        const approvals = history.approvals.filter(approval => approval.version_id === version.version_id)
        const isActive = approvals.some(approval => approval.status === 'active')
        const wasApproved = approvals.some(approval => approval.status === 'historical')
        const date = new Date(version.created_at)
        const createdAt = Number.isNaN(date.getTime()) ? version.created_at : date.toLocaleString()
        return <li key={version.version_id} className="cm-subpanel flex flex-wrap items-center justify-between gap-4">
          <div className="space-y-1 min-w-0">
            <h3 className="cm-panel-title">Revision {version.revision}</h3>
            <p className="cm-muted">{purposeLabels[version.purpose] || version.purpose}</p>
            <p className="cm-muted"><time dateTime={version.created_at}>{createdAt}</time></p>
            {isActive && <p className="cm-muted">Currently approved</p>}
            {!isActive && wasApproved && <p className="cm-muted">Previously approved</p>}
          </div>
          <div className="cm-page-actions">
          <button type="button" className="cm-button cm-button-quiet" disabled={busy || loading || !itemId}
            aria-label={`Compare revision ${version.revision}`} onClick={() => compare(version.version_id)}>Compare</button>
          <button type="button" className="cm-button cm-button-secondary" disabled={busy || dirty}
            aria-label={`Restore revision ${version.revision}`} onClick={() => onRestore(version.version_id)}>
            Restore
          </button>
          </div>
        </li>
      })}
    </ol>
  </section>
}
