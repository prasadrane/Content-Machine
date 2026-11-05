import React from 'react'
import { ShieldAlert, AlertCircle } from 'lucide-react'

export default function ProposalsQueue({ proposals, onApprove, onReject }) {
  if (!proposals || proposals.length === 0) return null

  return (
    <div className="cm-divider mt-4 pt-4 space-y-3">
      <h4 className="cm-panel-title">Proposed Rules Pending Approval</h4>
      {proposals.map((prop, idx) => (
        <div key={idx} className="cm-subpanel space-y-3">
          <p className="cm-prose">{prop.rule}</p>
          
          {prop.is_conflict && (
            <div className="cm-status cm-status-warning flex items-center gap-2">
              <ShieldAlert className="w-3.5 h-3.5 shrink-0" />
              <span>Potential conflict with existing rule #{prop.conflict_rule_id}</span>
            </div>
          )}

          {prop.merge_required && (
            <div className="cm-status cm-status-error flex items-center gap-2">
              <AlertCircle className="w-3.5 h-3.5 shrink-0" />
              <span>Rule cap reached (150 rules). Merge pass recommended.</span>
            </div>
          )}

          <div className="flex flex-wrap justify-end gap-2 pt-1">
            <button
              type="button"
              onClick={() => onReject(prop.rule_id)}
              className="cm-button cm-button-quiet"
            >
              Reject
            </button>
            <button
              type="button"
              onClick={() => onApprove(prop.rule_id)}
              className="cm-button cm-button-primary"
            >
              Approve Rule
            </button>
          </div>
        </div>
      ))}
    </div>
  )
}
