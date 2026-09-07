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
        <div className="space-y-3 bg-[#c6613f]/5 p-5 rounded-2xl border border-[#c6613f]/30 shadow-anthropic">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-[#c6613f] animate-pulse" />
              <h3 className="text-xs uppercase font-mono tracking-wider text-[#c6613f] font-semibold">
                Governance Review Queue ({pendingRules.length} Pending)
              </h3>
            </div>
            <span className="text-[10px] font-mono text-[#87867f]">Human Approval Gate</span>
          </div>
          <p className="text-[11px] text-[#87867f] font-sans">
            Extracted declarative rules must be approved before injection into the Writer's Council loop.
          </p>
          <div className="space-y-2.5 pt-1">
            {pendingRules.map((rule) => (
              <div key={rule.id} className="bg-[#faf9f5] border border-[#e3dacc] rounded-xl p-3.5 space-y-2.5 shadow-sm">
                <div className="flex items-center justify-between text-[10px] font-mono text-[#87867f]">
                  <span className="font-semibold text-[#141413]">Pending Rule #{rule.id}</span>
                  <span className="bg-[#f0eee6] px-1.5 py-0.5 rounded text-[#141413]">{rule.provenance_project || 'diff'}</span>
                </div>
                <p className="text-xs text-[#141413] font-serif leading-relaxed">{rule.rule_text}</p>
                <div className="flex justify-end gap-2 pt-1 border-t border-[#e3dacc]/60">
                  <button
                    type="button"
                    onClick={() => onReject(rule.id)}
                    className="px-3 py-1 text-[11px] font-mono text-[#87867f] hover:text-rose-700 hover:bg-rose-50 rounded-full transition"
                  >
                    Reject
                  </button>
                  <button
                    type="button"
                    onClick={() => onApprove(rule.id)}
                    className="px-3.5 py-1 text-[11px] font-mono text-[#faf9f5] bg-emerald-700 hover:bg-emerald-600 rounded-full transition shadow-sm flex items-center gap-1"
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
      <div className="space-y-4">
        <div className="flex items-center justify-between pb-2 border-b border-[#e3dacc]">
          <h3 className="text-xs uppercase font-mono tracking-wider text-[#87867f]">Active Governed Rules ({activeRules.length})</h3>
          <button type="button" onClick={onRefresh} className="text-xs text-[#87867f] hover:text-[#141413] font-mono flex items-center gap-1">
            <RotateCw className="w-3 h-3" />
            <span>refresh</span>
          </button>
        </div>

        <div className="space-y-2.5 max-h-[600px] overflow-y-auto pr-1">
          {activeRules.length === 0 ? (
            <div className="border border-dashed border-[#b0aea5] rounded-2xl p-8 text-center text-[#87867f] bg-[#f0eee6]/30">
              <p className="text-xs">No active lessons codified yet.</p>
            </div>
          ) : (
            activeRules.map((rule) => (
              <div key={rule.id} className="bg-[#faf9f5] border border-[#e3dacc] rounded-xl p-3.5 space-y-1 shadow-anthropic">
                <div className="flex items-center justify-between text-[10px] font-mono text-[#87867f]">
                  <span>#{rule.id}</span>
                  <span className="bg-[#f0eee6] px-1.5 py-0.5 rounded text-[#141413]">{rule.provenance_project || 'manual'}</span>
                </div>
                <p className="text-xs text-[#141413] font-serif leading-relaxed">{rule.rule_text}</p>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}
