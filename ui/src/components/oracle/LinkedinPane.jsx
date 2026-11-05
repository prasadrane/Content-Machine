import React, { useMemo } from 'react'
import { Globe, RotateCw } from 'lucide-react'
import { PresetChipGroup, selectedSetFrom } from './PresetEditorPane'

export default function LinkedinPane({
  linkedInProfiles,
  sourceError = '',
  setLinkedInProfiles,
  linkedInLiAt,
  setLinkedInLiAt,
  linkedInStatus,
  syncingLinkedIn,
  syncMsg,
  onSyncLinkedIn,
  linkedInPresets,
  onAddLinkedInPreset,
}) {
  const selectedHandles = useMemo(() => selectedSetFrom(linkedInProfiles), [linkedInProfiles])

  return (
    <div className="space-y-3 animate-fadeIn">
      <div className="flex items-center justify-between">
        <label className="cm-label block">LinkedIn Engine</label>
        {linkedInStatus?.session_valid ? (
          <span className="cm-badge flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
            Active Session
          </span>
        ) : (
          <span className="cm-badge flex items-center gap-1">
            <Globe className="w-2.5 h-2.5" />
            Public Bridge Mode
          </span>
        )}
      </div>

      <p className="cm-prose leading-tight">
        {linkedInStatus?.session_valid
          ? "Authenticated session active. Pulls home feed and full creator updates."
          : "Zero-auth public bridge active. Ingests public creator and company posts without login."}
      </p>

      {/* Creator & Company Handles */}
      <div>
        <label htmlFor="oracle-linkedin-profiles" className="cm-label block mb-1">
          Target Handles (in/slug or company/slug):
        </label>
        <textarea
          id="oracle-linkedin-profiles"
          aria-invalid={Boolean(sourceError)}
          aria-describedby={sourceError ? 'oracle-source-error' : undefined}
          rows={3}
          value={linkedInProfiles}
          onChange={(e) => setLinkedInProfiles(e.target.value)}
          placeholder="satyanadella&#10;company/cloudflare"
          className="cm-textarea w-full font-mono"
        />
      </div>

      {/* Quick Add Presets */}
      <PresetChipGroup
        label="Creator Presets:"
        labelClass="cm-label block mb-2"
        wrapClass="space-y-1"
        presets={linkedInPresets}
        valueKey="handle"
        selected={selectedHandles}
        onAdd={onAddLinkedInPreset}
      />

      {/* Auto-Sync Session Action */}
      <div className="pt-2 border-t border-anthropic-oat/60 flex items-center justify-between gap-2">
        <button
          type="button"
          onClick={onSyncLinkedIn}
          disabled={syncingLinkedIn}
          className="cm-button cm-button-secondary flex items-center gap-1.5 disabled:opacity-50"
          title="Auto-extract session from local Playwright persistent browser context"
        >
          <RotateCw className={` w-3 h-3 ${syncingLinkedIn ? "animate-spin" : ""}  `} />
          <span>{syncingLinkedIn ? 'Syncing...' : 'Auto-Sync Session'}</span>
        </button>

        <span className="text-sm text-anthropic-cloud-dark truncate max-w-[140px]">
          {linkedInStatus?.saved_at ? `Synced ${new Date(linkedInStatus.saved_at).toLocaleDateString()}` : 'No session'}
        </span>
      </div>

      {syncMsg && (
        <p className="cm-prose">
          {syncMsg}
        </p>
      )}

      {/* Optional Manual li_at Override */}
      <details className="group pt-1">
        <summary className="text-sm text-anthropic-cloud-dark cursor-pointer hover:text-anthropic-slate-dark transition select-none">
          ▸ Manual li_at Cookie Override
        </summary>
        <div className="mt-2 space-y-1">
          <input
            type="password"
            value={linkedInLiAt}
            onChange={(e) => setLinkedInLiAt(e.target.value)}
            placeholder="Paste li_at cookie..."
            className="cm-input w-full font-mono"
          />
          <span className="text-sm text-anthropic-cloud-dark block">
            DevTools &rarr; Application &rarr; Cookies &rarr; <code className="text-anthropic-slate-dark bg-anthropic-oat/50 px-1 rounded">li_at</code>
          </span>
        </div>
      </details>
    </div>
  )
}
