import React, { useEffect, useState } from 'react'
import RevisionComparison from './RevisionComparison'

export default function VerdictPanel({ result, best, draft, spikeId, humanizing, onLoadDraft, onHumanize, onRequestApproval, reviewIsEarlier = false }) {
  const [proposed, setProposed] = useState(null)
  useEffect(() => { setProposed(null) }, [draft, spikeId])
  if (!result) return null
  const matchesReview = !reviewIsEarlier && !result.replayed && result.reviewInput?.slug === spikeId &&
    (draft === result.reviewInput?.text || draft === result.draft)
  return (
    <section aria-label="Editorial feedback" className="bg-[#faf9f5] border border-[#e3dacc] rounded-2xl p-5 space-y-5 shadow-anthropic">
      <div>
        <h4 className="font-serif text-xl">What to improve next</h4>
        <p className="text-sm text-[#58574f] mt-1">This is editorial feedback, not a factual verification. You decide what to publish.</p>
      </div>
      {result.replayed && <p className="p-3 bg-amber-50 text-amber-900 rounded-xl text-sm">Replayed sample result: this is a stored review of a seeded draft, not a review of yours.</p>}
      {result.actions?.length > 0 ? (
        <ul className="list-disc pl-5 space-y-3 text-base leading-relaxed">
          {result.actions.map((action, index) => <li key={index}>{action}</li>)}
        </ul>
      ) : <p className="text-sm text-[#58574f]">No specific editorial changes were returned. Review the draft and its source material yourself.</p>}
      <details className="border-t border-[#e3dacc] pt-3">
        <summary className="cursor-pointer min-h-10 text-sm font-medium">Review score and verdict</summary>
        <p className="text-base mt-2">Editorial score: {Number(result.score).toFixed(2)} / 10 · Verdict: {result.verdict}</p>
        {best && best.score > result.score && <p className="text-sm mt-2">A previous version scored higher ({best.score.toFixed(2)}).</p>}
      </details>
      <div className="flex flex-wrap gap-3">
        {result.draft && result.draft !== draft && <button type="button" onClick={() => setProposed(result.draft)} className="min-h-10 px-4 py-2 border border-[#b0aea5] rounded-full text-sm">Compare revised draft</button>}
        {best?.draft && best.draft !== draft && best.draft !== result.draft && <button type="button" onClick={() => setProposed(best.draft)} className="min-h-10 px-4 py-2 border border-[#b0aea5] rounded-full text-sm">Compare highest-scoring draft</button>}
        {onHumanize && <button type="button" onClick={() => onHumanize(draft)} disabled={humanizing || !draft?.trim()} className="min-h-10 px-4 py-2 border border-[#b0aea5] rounded-full text-sm disabled:opacity-50">{humanizing ? 'Polishing wording...' : 'Polish current wording'}</button>}
      </div>
      {proposed !== null && <RevisionComparison currentText={draft} proposedText={proposed} onCancel={() => setProposed(null)} onAccept={text => { onLoadDraft(text); setProposed(null) }} />}
      {onRequestApproval && <button type="button" onClick={() => onRequestApproval(draft, matchesReview ? { verdict: result.verdict, score: result.score } : { verdict: 'unreviewed' })} className="min-h-10 px-5 py-2 rounded-full bg-[#141413] text-[#faf9f5] text-sm">Approve &amp; Distribute</button>}
    </section>
  )
}
