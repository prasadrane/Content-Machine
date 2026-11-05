import React, { useState } from 'react'
import { ShieldCheck, AlertTriangle } from 'lucide-react'

// Explicit human sign-off. Nothing moves to Distribute until the operator
// confirms they read this exact text. A below-gate verdict is allowed but
// flagged as an override.
export default function ApprovalGate({ text, verdict, score, onConfirm, onCancel }) {
  const [confirmed, setConfirmed] = useState(false)
  const override = verdict && verdict !== 'pass'

  return (
    <div role="dialog" aria-label="Approve draft" className="cm-panel space-y-4">
      <div className="flex items-center gap-2">
        <ShieldCheck className="w-5 h-5 text-[var(--cm-accent)]" />
        <h4 className="cm-panel-title">Approve for distribution</h4>
      </div>

      <pre className="cm-subpanel cm-prose font-sans max-h-64 overflow-auto whitespace-pre-wrap">{text}</pre>

      {override && (
        <div className="cm-status cm-status-warning flex items-start gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
          <span>
            Council verdict is <strong>{verdict}</strong>{typeof score === 'number' ? ` (${score.toFixed(3)})` : ''}. Approving overrides the judges; that is your call.
          </span>
        </div>
      )}

      <label className="cm-prose flex items-start gap-3 cursor-pointer">
        <input type="checkbox" checked={confirmed} onChange={(e) => setConfirmed(e.target.checked)} className="mt-0.5" />
        <span>I have read this exact text and approve it for distribution. Editing it later requires approving again.</span>
      </label>

      <div className="cm-page-actions justify-end">
        <button type="button" onClick={onCancel} className="cm-button cm-button-secondary">
          Cancel
        </button>
        <button
          type="button"
          disabled={!confirmed}
          onClick={onConfirm}
          className="cm-button cm-button-primary"
        >
          Approve &amp; send to Distribute
        </button>
      </div>
    </div>
  )
}
