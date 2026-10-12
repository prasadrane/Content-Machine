import React, { useState } from 'react'
import { ShieldCheck, AlertTriangle } from 'lucide-react'

// Explicit human sign-off. Nothing moves to Distribute until the operator
// confirms they read this exact text. A below-gate verdict is allowed but
// flagged as an override.
export default function ApprovalGate({ text, verdict, score, onConfirm, onCancel }) {
  const [confirmed, setConfirmed] = useState(false)
  const override = verdict && verdict !== 'pass'

  return (
    <div role="dialog" aria-label="Approve draft" className="bg-[#faf9f5] border border-[#141413] rounded-2xl p-5 space-y-4 shadow-anthropic">
      <div className="flex items-center gap-2">
        <ShieldCheck className="w-4 h-4 text-[#c6613f]" />
        <h4 className="text-xs font-mono uppercase tracking-wider text-[#141413]">Approve for distribution</h4>
      </div>

      <pre className="max-h-48 overflow-auto whitespace-pre-wrap text-xs font-mono leading-relaxed bg-[#f0eee6]/70 border border-[#e3dacc] rounded-xl p-3 text-[#141413]">{text}</pre>

      {override && (
        <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-amber-900 text-xs flex items-start gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
          <span>
            Council verdict is <strong>{verdict}</strong>{typeof score === 'number' ? ` (${score.toFixed(3)})` : ''}. Approving overrides the judges; that is your call.
          </span>
        </div>
      )}

      <label className="flex items-start gap-2 text-xs text-[#141413] cursor-pointer">
        <input type="checkbox" checked={confirmed} onChange={(e) => setConfirmed(e.target.checked)} className="mt-0.5" />
        <span>I have read this exact text and approve it for distribution. Editing it later requires approving again.</span>
      </label>

      <div className="flex items-center justify-end gap-2">
        <button type="button" onClick={onCancel} className="px-4 py-2 rounded-full text-xs font-medium border border-[#e3dacc] text-[#87867f] hover:text-[#141413]">
          Cancel
        </button>
        <button
          type="button"
          disabled={!confirmed}
          onClick={onConfirm}
          className="px-4 py-2 rounded-full text-xs font-medium bg-[#141413] text-[#faf9f5] disabled:opacity-40"
        >
          Approve &amp; send to Distribute
        </button>
      </div>
    </div>
  )
}
