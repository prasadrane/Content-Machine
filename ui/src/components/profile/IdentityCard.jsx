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
      <div className="cm-panel space-y-4">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-center gap-3.5">
            <div className="cm-chip cm-chip-active w-12 h-12 justify-center shrink-0">
              PR
            </div>
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <h3 className="cm-panel-title">
                  {profile?.name || 'Prasad Rane'}
                </h3>
                <span className="cm-badge cm-status-success inline-flex items-center gap-1">
                  <ShieldCheck className="w-3 h-3 text-emerald-600" />
                  <span>Verified Persona</span>
                </span>
              </div>
              <p className="cm-muted mt-1">
                {profile?.headline || 'Senior Software & AI Systems Engineer'} &mdash; The Bridge between Enterprise Systems and Modern AI
              </p>
            </div>
          </div>
        </div>
        <div className="cm-divider pt-4 grid grid-cols-1 sm:grid-cols-2 gap-3 cm-muted">
          <div>
            <span className="text-[#141413] font-medium">Domain:</span> Enterprise &bull; Distributed &bull; AI
          </div>
          <div className="sm:text-right">
            <span className="text-[#141413] font-medium">Anchor:</span> Local-First Engine Grounding
          </div>
        </div>
      </div>

      {/* Current Focus Card */}
      <div className="cm-panel space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <label htmlFor="profile-current-focus" className="cm-label">
            Current Operational Reality
          </label>
          <span className="cm-muted">
            Active Hands-on Focus
          </span>
        </div>
        <p className="cm-muted">
          Edit current upskilling and hands-on building focus. Injected dynamically into generation prompts:
        </p>
        <textarea
          id="profile-current-focus"
          rows={4}
          value={currentFocus}
          onChange={(e) => onFocusChange(e.target.value)}
          placeholder="e.g., Agentic AI systems, local multi-model orchestration, distributed patterns..."
          className="cm-textarea"
        />
      </div>
    </>
  )
}
