import { useEffect, useState } from 'react'
import ReviewStatus from './ReviewStatus'
import { formatLabel } from './workflowUtils'

export default function ApproveStage({ flow }) {
  const [consent, setConsent] = useState(false)
  useEffect(() => { setConsent(false) }, [flow.item.item_id, flow.item.working_revision, flow.dirty])
  const segments = flow.item.artifact.segments
  const blank = segments.length === 0 || segments.some(text => !text.trim())
  return <section className="cm-panel space-y-5">
    <h2 className="cm-panel-title">Approve the exact version</h2>
    <p className="cm-muted">{formatLabel(flow.item)} · Revision {flow.item.working_revision}</p>
    <ReviewStatus flow={flow} />
    {segments.map((text, index) => <div key={index} className="cm-subpanel">
      {segments.length > 1 && <h3 className="cm-label">Post {index + 1}</h3>}
      <pre className="cm-prose whitespace-pre-wrap">{text}</pre>
    </div>)}
    {flow.dirty && <p className="cm-status cm-status-warning">Save your changes in the editor before approving.</p>}
    {blank && <p className="cm-muted">Add draft text before approving.</p>}
    <label className="flex items-start gap-3 cm-prose">
      <input type="checkbox" className="mt-1" checked={consent} disabled={flow.busy || flow.dirty || blank}
        onChange={event => setConsent(event.target.checked)} />
      I approve this exact version and have checked its facts and personal claims.
    </label>
    <div className="cm-page-actions">
      <button className="cm-button cm-button-secondary" disabled={flow.busy} onClick={() => flow.setStage('draft_review')}>Back to draft</button>
      <button className="cm-button cm-button-primary" disabled={!consent || flow.busy || flow.dirty || blank}
        onClick={flow.approve}>Approve this version</button>
    </div>
  </section>
}
