import React from 'react'
import { ShieldCheck } from 'lucide-react'

/**
 * IdentityCard — author identity block + current focus textarea.
 * Props:
 *   profile         — full profile object (may be null while loading)
 *   currentFocus    — controlled textarea value
 *   onFocusChange   — (value: string) => void
 *   onSave          — () => void
 *   saving          — boolean
 *   saveSuccess     — boolean
 *   error           — string
 *   hasChanges      — boolean
 *   loading         — boolean
 */
export default function IdentityCard({
  profile,
  currentFocus,
  onFocusChange,
  onSave,
  saving,
  saveSuccess,
  error,
  hasChanges,
  loading,
}) {
  return (
    <>
      {/* Author Identity Card */}
      <div className="bg-[#f0eee6]/60 border border-[#e3dacc] rounded-2xl p-5 sm:p-6 space-y-4 shadow-anthropic">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-center gap-3.5">
            <div className="w-12 h-12 rounded-2xl bg-[#141413] text-[#faf9f5] flex items-center justify-center font-serif text-lg font-semibold shrink-0 shadow-sm">
              PR
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-serif text-lg font-medium text-[#141413]">
                  {profile?.name || 'Prasad Rane'}
                </h3>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200 flex items-center gap-1">
                  <ShieldCheck className="w-3 h-3 text-emerald-600" />
                  <span>Verified Persona</span>
                </span>
              </div>
              <p className="text-xs text-[#87867f] mt-0.5 font-sans leading-relaxed">
                {profile?.headline || 'Senior Software & AI Systems Engineer'} &mdash; The Bridge between Enterprise Systems and Modern AI
              </p>
            </div>
          </div>
        </div>
        <div className="pt-3 border-t border-[#e3dacc]/70 grid grid-cols-2 gap-3 text-[11px] font-mono text-[#87867f]">
          <div>
            <span className="text-[#141413] font-medium">Domain:</span> Enterprise &bull; Distributed &bull; AI
          </div>
          <div className="text-right">
            <span className="text-[#141413] font-medium">Anchor:</span> Local-First Engine Grounding
          </div>
        </div>
      </div>

      {/* Current Focus Card */}
      <div className="bg-[#f0eee6]/60 border border-[#e3dacc] rounded-2xl p-5 sm:p-6 space-y-3 shadow-anthropic">
        <div className="flex items-center justify-between">
          <label className="text-xs uppercase font-mono tracking-wider text-[#87867f] font-semibold">
            Current Operational Reality
          </label>
          <span className="text-[10px] font-mono text-[#87867f]">
            Active Hands-on Focus
          </span>
        </div>
        <p className="text-xs text-[#87867f] font-sans">
          Edit current upskilling and hands-on building focus. Injected dynamically into generation prompts:
        </p>
        <textarea
          rows={4}
          value={currentFocus}
          onChange={(e) => onFocusChange(e.target.value)}
          placeholder="e.g., Agentic AI systems, local multi-model orchestration, distributed patterns..."
          className="w-full text-xs font-sans bg-[#faf9f5] border border-[#e3dacc] rounded-xl p-3.5 text-[#141413] focus:outline-none focus:border-[#141413] focus:bg-[#faf9f5] transition placeholder-[#b0aea5] leading-relaxed shadow-xs"
        />
      </div>
    </>
  )
}
