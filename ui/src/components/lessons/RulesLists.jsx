import React from 'react'
import { RotateCw, Check } from 'lucide-react'

export default function RulesLists({
  pendingRules,
  activeRules,
  onApprove,
  onReject,
  onRefresh,
}) {
  return (
    <div className="space-y-6">
      {/* Pending Approval Queue from DB */}
      {pendingRules.length > 0 && (
        <div className="cm-panel space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-[#c6613f] animate-pulse" />
              <h3 className="cm-panel-title">
                Governance Review Queue ({pendingRules.length} Pending)
              </h3>
            </div>
            <span className="cm-muted">Human Approval Gate</span>
          </div>
          <p className="cm-muted">
            Extracted declarative rules must be approved before injection into the Writer's Council loop.
          </p>
          <div className="space-y-2.5 pt-1">
            {pendingRules.map((rule) => (
              <div key={rule.id} className="cm-subpanel space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-2 cm-muted">
                  <span className="font-semibold text-[#141413]">Pending Rule #{rule.id}</span>
                  <span className="cm-badge">{rule.provenance_project || 'diff'}</span>
                </div>
                <p className="cm-prose">{rule.rule_text}</p>
                <div className="cm-divider flex flex-wrap justify-end gap-2 pt-3">
                  <button
                    type="button"
                    onClick={() => onReject(rule.id)}
                    className="cm-button cm-button-quiet"
                  >
                    Reject
                  </button>
                  <button
                    type="button"
                    onClick={() => onApprove(rule.id)}
                    className="cm-button cm-button-primary"
                  >
                    <Check className="w-3 h-3" />
                    <span>Approve Rule</span>
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Active Rules List */}
      <div className="cm-panel space-y-4">
        <div className="cm-panel-header flex flex-wrap items-center justify-between gap-3">
          <h3 className="cm-panel-title">Active Governed Rules ({activeRules.length})</h3>
          <button type="button" onClick={onRefresh} className="cm-button cm-button-quiet">
            <RotateCw className="w-3 h-3" />
            <span>refresh</span>
          </button>
        </div>

        <div className="space-y-2.5 max-h-[600px] overflow-y-auto pr-1">
          {activeRules.length === 0 ? (
            <div className="cm-empty">
              <p className="text-sm">No active lessons codified yet.</p>
            </div>
          ) : (
            activeRules.map((rule) => (
              <div key={rule.id} className="cm-subpanel space-y-2">
                <div className="flex flex-wrap items-center justify-between gap-2 cm-muted">
                  <span>#{rule.id}</span>
                  <span className="cm-badge">{rule.provenance_project || 'manual'}</span>
                </div>
                <p className="cm-prose">{rule.rule_text}</p>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}
