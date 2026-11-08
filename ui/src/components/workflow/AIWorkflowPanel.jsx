import { useState } from 'react'
import { Lightbulb, RefreshCw, Users } from 'lucide-react'

function ProposalComparison({ flow, operation }) {
  const before = operation.editorial_snapshot?.artifact?.segments || []
  const after = operation.result.artifact.segments
  return <section className="cm-subpanel space-y-4" aria-label="Draft suggestion">
    <h3 className="cm-panel-title">Compare the suggestion</h3>
    <p className="cm-muted">The suggestion is separate from your saved draft. Check it before choosing to save it.</p>
    {!flow.aiIsCurrent && <p className="cm-status cm-status-warning">This suggestion is for an earlier saved version. Your current draft is preserved.</p>}
    <div className="grid gap-3 md:grid-cols-2">
      <div className="space-y-2"><h4 className="cm-label">Saved draft</h4>
        {before.length ? before.map((text, index) => <pre key={index} className="cm-prose whitespace-pre-wrap">{text}</pre>) :
          <p className="cm-muted">No saved draft text.</p>}
      </div>
      <div className="space-y-2"><h4 className="cm-label">Suggested draft</h4>
        {after.map((text, index) => <pre key={index} className="cm-prose whitespace-pre-wrap">{text}</pre>)}
      </div>
    </div>
    <div className="cm-page-actions">
      <button className="cm-button cm-button-secondary" disabled={flow.busy || !flow.aiIsCurrent}
        onClick={flow.acceptProposal}>Save this suggestion</button>
      <button className="cm-button cm-button-quiet" disabled={flow.busy} onClick={flow.cancelProposal}>Discard suggestion</button>
    </div>
  </section>
}

function CouncilAdvice({ flow, operation }) {
  const review = operation.result?.review
  if (!review) return null
  const actions = Array.isArray(review.actions?.required_actions) ? review.actions.required_actions : []
  const notes = Array.isArray(review.actions?.notes) ? review.actions.notes : []
  const proposals = Array.isArray(review.proposals) ? review.proposals : []
  const raw = review.score_basis?.raw
  return <section className="cm-subpanel space-y-4" aria-label="Council advice">
    <h3 className="cm-panel-title">Council advice</h3>
    <p className="cm-muted">{flow.aiIsCurrent ? 'Advice for this saved version.' : 'Advice for an earlier saved version.'}</p>
    {typeof raw?.composite === 'number' && <p className="cm-muted">Raw composite {raw.composite} / {raw.scale?.[1] ?? 10}</p>}
    {actions.length > 0 ? <ul className="list-disc pl-5 space-y-1">
      {actions.map((action, index) => <li key={index} className="cm-prose">{action}</li>)}
    </ul> : <p className="cm-muted">No specific actions were returned.</p>}
    {notes.map((note, index) => <p key={index} className="cm-status cm-status-info">{note}</p>)}
    {proposals.map((suggestion, index) => <div key={index} role="group"
      aria-label={`Suggestion for post ${suggestion.segment + 1}`} className="cm-divider space-y-3">
      <p className="cm-muted">{suggestion.provenance === 'deterministic_cleanup' ? 'Local cleanup suggestion'
        : suggestion.provenance === 'model_rewrite' ? 'Model wording suggestion' : 'Wording suggestion'}</p>
      <p className="cm-label">Current wording</p><pre className="cm-prose whitespace-pre-wrap break-words" style={{ overflowWrap: 'anywhere' }}>{suggestion.current}</pre>
      <p className="cm-label">Suggested wording</p><pre className="cm-prose whitespace-pre-wrap break-words" style={{ overflowWrap: 'anywhere' }}>{suggestion.proposed}</pre>
      <button className="cm-button cm-button-secondary" disabled={flow.busy || !flow.aiIsCurrent}
        onClick={() => flow.acceptReviewProposal(suggestion)}>Save this change</button>
    </div>)}
  </section>
}

function PendingOperation({ flow }) {
  const [confirmAbandon, setConfirmAbandon] = useState(false)
  return <div className="cm-status cm-status-info space-y-2">
    <p>{flow.ai.pending.kind === 'review' ? 'Council review' : 'AI drafting'} is pending. Your saved draft is unchanged.</p>
    <button className="cm-button cm-button-secondary" disabled={flow.busy} onClick={flow.checkAIStatus}>
      <RefreshCw size={16} aria-hidden="true" />Check status</button>
    {!confirmAbandon ? <button className="cm-button cm-button-quiet" disabled={flow.busy} onClick={() => setConfirmAbandon(true)}>Close pending request</button> :
      <div className="space-y-2"><p>The provider may still finish this request. Starting another request may duplicate work. Close it anyway?</p>
        <button className="cm-button cm-button-secondary" disabled={flow.busy} onClick={() => { setConfirmAbandon(false); flow.abandonAI() }}>Yes, close request</button>
        <button className="cm-button cm-button-quiet" onClick={() => setConfirmAbandon(false)}>Keep waiting</button></div>}
  </div>
}

export default function AIWorkflowPanel({ flow }) {
  const pair = flow.pairs.find(entry => entry.destination === flow.item.destination && entry.format === flow.item.format)
  const ready = !flow.capabilitiesLoading && !flow.capabilitiesError
  const operation = flow.ai.operation
  const label = operation?.kind === 'review' ? 'Council review' : 'AI drafting'
  const blocked = flow.busy || flow.ai.loading || flow.ai.loadError || flow.ai.pending?.state === 'pending'
  return <section className="space-y-4" aria-label="AI assistance">
    <div className="cm-page-actions">
      <button className="cm-button cm-button-secondary" disabled={blocked || !ready || !pair?.can_generate}
        onClick={flow.generateDraft}><Lightbulb size={16} aria-hidden="true" />Create draft suggestion</button>
      <button className="cm-button cm-button-secondary" disabled={blocked || !ready || !pair?.can_review ||
        !(flow.draft?.artifact?.segments || flow.item.artifact.segments).some(text => text.trim())}
        onClick={flow.requestReview}><Users size={16} aria-hidden="true" />Request Council review</button>
    </div>
    {(!ready || !pair?.can_generate || !pair?.can_review) &&
      <p className="cm-muted">Some AI assistance is unavailable. You can write your draft yourself and continue.</p>}
    {flow.ai.loading && <p role="status" className="cm-muted">Checking AI activity…</p>}
    {flow.ai.loadError && <div className="cm-status cm-status-warning space-y-2">
      <p>Could not check earlier AI activity. Your draft is still available.</p>
      <button className="cm-button cm-button-secondary" disabled={flow.busy} onClick={flow.loadAIActivity}>Retry AI activity</button>
    </div>}
    {flow.ai.pending?.state === 'pending' && <PendingOperation key={`${flow.ai.pending.item_id}:${flow.ai.pending.operation_id}`} flow={flow} />}
    {operation?.state === 'failed' && <p className="cm-status cm-status-error">{label} failed. Your saved draft is unchanged.</p>}
    {flow.ai.proposal && <ProposalComparison flow={flow} operation={flow.ai.proposal} />}
    {operation?.kind === 'review' && operation.state === 'completed' && <CouncilAdvice flow={flow} operation={operation} />}
    <details className="cm-divider space-y-3">
      <summary className="cursor-pointer font-medium">AI activity</summary>
      <button className="cm-button cm-button-quiet" disabled={flow.busy} onClick={flow.loadAIActivity}>Load AI activity</button>
      {flow.ai.activities?.length === 0 && <p className="cm-muted">No AI activity for this item.</p>}
      {flow.ai.activities?.map(entry => <div key={entry.operation_id} className="flex flex-wrap items-center gap-3">
        <span className="cm-muted">{entry.kind === 'review' ? 'Council review' : 'Draft suggestion'} · {entry.state}</span>
        <button className="cm-button cm-button-quiet" disabled={flow.busy} aria-label={`View ${entry.kind === 'review' ? 'Council review' : 'draft suggestion'} ${entry.state} ${entry.operation_id}`} onClick={() => flow.showAIActivity(entry)}>View</button>
      </div>)}
    </details>
  </section>
}
