import React from 'react'
import { ShieldAlert, AlertCircle } from 'lucide-react'

export default function ProposalsQueue({ proposals, onApprove, onReject }) {
  if (!proposals || proposals.length === 0) return null

  return (
    <div className="mt-4 pt-4 border-t border-[#e3dacc] space-y-3">
      <h4 className="text-xs font-mono uppercase text-[#87867f]">Proposed Rules Pending Approval</h4>
      {proposals.map((prop, idx) => (
        <div key={idx} className="bg-[#faf9f5] p-3.5 rounded-xl border border-[#e3dacc] space-y-2">
          <p className="text-xs text-[#141413] font-medium">{prop.rule}</p>
          
          {prop.is_conflict && (
            <div className="flex items-center gap-1.5 text-[11px] text-[#c6613f] bg-[#c6613f]/10 p-2 rounded-lg border border-[#c6613f]/20 font-mono">
              <ShieldAlert className="w-3.5 h-3.5 shrink-0" />
              <span>Potential conflict with existing rule #{prop.conflict_rule_id}</span>
            </div>
          )}

          {prop.merge_required && (
            <div className="flex items-center gap-1.5 text-[11px] text-rose-800 bg-rose-50 p-2 rounded-lg border border-rose-200 font-mono">
              <AlertCircle className="w-3.5 h-3.5 shrink-0" />
              <span>Rule cap reached (150 rules). Merge pass recommended.</span>
            </div>
          )}

          <div className="flex justify-end gap-2 pt-1">
            <button
              type="button"
              onClick={() => onReject(prop.rule_id)}
              className="px-3 py-1 text-[11px] font-mono text-[#87867f] hover:text-[#141413] hover:bg-[#e3dacc]/50 rounded-full transition"
            >
              Reject
            </button>
            <button
              type="button"
              onClick={() => onApprove(prop.rule_id)}
              className="px-3.5 py-1 text-[11px] font-mono text-[#faf9f5] bg-emerald-700 hover:bg-emerald-600 rounded-full transition shadow-sm"
            >
              Approve Rule
            </button>
          </div>
        </div>
      ))}
    </div>
  )
}
