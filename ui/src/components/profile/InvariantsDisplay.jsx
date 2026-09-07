import React from 'react'
import { ShieldCheck } from 'lucide-react'

/**
 * InvariantsDisplay — read-only list of core voice invariants.
 * Props:
 *   invariants — array of { title, summary, description }
 */
export default function InvariantsDisplay({ invariants }) {
  return (
    <div className="bg-[#f0eee6]/60 border border-[#e3dacc] rounded-2xl p-5 sm:p-6 space-y-4 shadow-anthropic">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-[#c6613f]" />
          <h3 className="text-xs uppercase font-mono tracking-wider text-[#87867f] font-semibold">
            Non-Negotiable Voice Invariants
          </h3>
        </div>
        <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-rose-50 text-rose-800 border border-rose-200">
          Permanently Enforced
        </span>
      </div>
      <p className="text-xs text-[#87867f] font-sans">
        Hard negative constraints strictly enforced across all generation models and council evaluations:
      </p>

      <div className="space-y-2.5">
        {invariants.map((inv, idx) => (
          <div
            key={idx}
            className="bg-[#faf9f5] border border-[#e3dacc] rounded-xl p-3.5 space-y-1.5 shadow-xs transition hover:border-[#b0aea5]"
          >
            <div className="flex items-center justify-between gap-2 flex-wrap">
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                <span className="text-xs font-mono font-semibold text-[#141413]">
                  🛡️ {inv.title}
                </span>
              </div>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-[#f0eee6] text-[#87867f] border border-[#e3dacc]">
                {inv.summary}
              </span>
            </div>
            <p className="text-[11px] text-[#87867f] font-sans leading-relaxed pl-5">
              {inv.description}
            </p>
          </div>
        ))}
      </div>
    </div>
  )
}
