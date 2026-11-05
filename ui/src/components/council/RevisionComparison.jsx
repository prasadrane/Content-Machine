import React from 'react'

// Linear text comparison deliberately makes no claim to identify factual changes.
export default function RevisionComparison({ currentText, proposedText, onAccept, onCancel }) {
  return (
    <section aria-label="Compare draft versions" className="cm-subpanel space-y-4">
      <p className="cm-muted">Review wording, attribution, and factual claims before replacing your draft. This comparison does not verify facts.</p>
      <div>
        <h4 className="cm-panel-title">Current draft</h4>
        <pre className="cm-prose mt-2 max-h-72 overflow-auto whitespace-pre-wrap break-words">{currentText || '(Empty draft)'}</pre>
      </div>
      <div className="cm-divider">
        <h4 className="cm-panel-title">Proposed draft</h4>
        <pre className="cm-prose mt-2 max-h-72 overflow-auto whitespace-pre-wrap break-words">{proposedText}</pre>
      </div>
      <div className="flex flex-wrap gap-3">
        <button type="button" onClick={() => onAccept(proposedText)} className="cm-button cm-button-primary">Use proposed draft</button>
        <button type="button" onClick={onCancel} className="cm-button cm-button-secondary">Keep current draft</button>
      </div>
    </section>
  )
}
