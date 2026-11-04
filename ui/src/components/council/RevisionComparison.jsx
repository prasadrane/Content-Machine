import React from 'react'

// Linear text comparison deliberately makes no claim to identify factual changes.
export default function RevisionComparison({ currentText, proposedText, onAccept, onCancel }) {
  return (
    <section aria-label="Compare draft versions" className="space-y-4 rounded-xl border border-[#b0aea5] bg-[#faf9f5] p-4">
      <p className="text-sm text-[#58574f]">Review wording, attribution, and factual claims before replacing your draft. This comparison does not verify facts.</p>
      <div>
        <h4 className="font-semibold text-sm">Current draft</h4>
        <pre className="mt-2 max-h-72 overflow-auto whitespace-pre-wrap break-words font-sans text-base leading-relaxed">{currentText || '(Empty draft)'}</pre>
      </div>
      <div className="border-t border-[#e3dacc] pt-3">
        <h4 className="font-semibold text-sm">Proposed draft</h4>
        <pre className="mt-2 max-h-72 overflow-auto whitespace-pre-wrap break-words font-sans text-base leading-relaxed">{proposedText}</pre>
      </div>
      <div className="flex flex-wrap gap-3">
        <button type="button" onClick={() => onAccept(proposedText)} className="min-h-10 rounded-full bg-[#141413] px-4 py-2 text-sm text-[#faf9f5]">Use proposed draft</button>
        <button type="button" onClick={onCancel} className="min-h-10 rounded-full border border-[#b0aea5] px-4 py-2 text-sm">Keep current draft</button>
      </div>
    </section>
  )
}
