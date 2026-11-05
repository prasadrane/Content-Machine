import React from 'react'
import { ShieldCheck } from 'lucide-react'

/**
 * InvariantsDisplay — read-only list of core voice invariants.
 * Props:
 *   invariants — array of { title, summary, description }
 */
export default function InvariantsDisplay({ invariants }) {
  return (
    <div className="cm-panel space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-[#c6613f]" />
          <h3 className="cm-panel-title">
            Non-Negotiable Voice Invariants
          </h3>
        </div>
        <span className="cm-badge cm-status-info">
          Permanently Enforced
        </span>
      </div>
      <p className="cm-muted">
        Hard negative constraints strictly enforced across all generation models and council evaluations:
      </p>

      <div className="space-y-2.5">
        {invariants.map((inv, idx) => (
          <div
            key={idx}
            className="cm-subpanel space-y-2"
          >
            <div className="flex items-center justify-between gap-2 flex-wrap">
              <div className="flex flex-wrap items-center gap-2">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                <span className="font-semibold">
                  {inv.title}
                </span>
              </div>
              <span className="cm-badge">
                {inv.summary}
              </span>
            </div>
            <p className="cm-muted pl-5">
              {inv.description}
            </p>
          </div>
        ))}
      </div>
    </div>
  )
}
