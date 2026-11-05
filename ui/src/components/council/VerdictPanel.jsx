import React, { useEffect, useState } from 'react'
import RevisionComparison from './RevisionComparison'

export default function VerdictPanel({ result, best, draft, spikeId, humanizing, onLoadDraft, onHumanize, onRequestApproval, reviewIsEarlier = false }) {
  const [proposed, setProposed] = useState(null)
  useEffect(() => { setProposed(null) }, [draft, spikeId])
  if (!result) return null
  const matchesReview = !reviewIsEarlier && !result.replayed && result.reviewInput?.slug === spikeId &&
    (draft === result.reviewInput?.text || draft === result.draft)
  return (
    <section aria-label="Editorial feedback" className="cm-panel space-y-5">
      <div>
        <h4 className="cm-panel-title">What to improve next</h4>
        <p className="cm-muted mt-1">This is editorial feedback, not a factual verification. You decide what to publish.</p>
      </div>
      {result.replayed && <p className="cm-status cm-status-warning">Replayed sample result: this is a stored review of a seeded draft, not a review of yours.</p>}
      {result.actions?.length > 0 ? (
        <ul className="list-disc pl-5 space-y-3 text-base leading-relaxed">
          {result.actions.map((action, index) => <li key={index}>{action}</li>)}
        </ul>
      ) : <p className="cm-muted">No specific editorial changes were returned. Review the draft and its source material yourself.</p>}
      <details className="cm-divider">
        <summary className="cm-label cursor-pointer">Review score and verdict</summary>
        <p className="cm-prose mt-2">Editorial score: {Number(result.score).toFixed(2)} / 10 · Verdict: {result.verdict}</p>
        {best && best.score > result.score && <p className="cm-prose mt-2">A previous version scored higher ({best.score.toFixed(2)}).</p>}
      </details>
      <div className="flex flex-wrap gap-3">
        {result.draft && result.draft !== draft && <button type="button" onClick={() => setProposed(result.draft)} className="cm-button cm-button-secondary">Compare revised draft</button>}
        {best?.draft && best.draft !== draft && best.draft !== result.draft && <button type="button" onClick={() => setProposed(best.draft)} className="cm-button cm-button-secondary">Compare highest-scoring draft</button>}
        {onHumanize && <button type="button" onClick={() => onHumanize(draft)} disabled={humanizing || !draft?.trim()} className="cm-button cm-button-secondary">{humanizing ? 'Polishing wording...' : 'Polish current wording'}</button>}
      </div>
      {proposed !== null && <RevisionComparison currentText={draft} proposedText={proposed} onCancel={() => setProposed(null)} onAccept={text => { onLoadDraft(text); setProposed(null) }} />}
      {onRequestApproval && <button type="button" onClick={() => onRequestApproval(draft, matchesReview ? { verdict: result.verdict, score: result.score } : { verdict: 'unreviewed' })} className="cm-button cm-button-primary">Approve &amp; Distribute</button>}
    </section>
  )
}
