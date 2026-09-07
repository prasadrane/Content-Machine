import React, { useMemo } from 'react'
import { Globe, RotateCw } from 'lucide-react'

export default function LinkedinPane({
  linkedInProfiles,
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
  const selectedHandles = useMemo(() => {
    return new Set(linkedInProfiles.split('\n').map(s => s.trim()).filter(Boolean))
  }, [linkedInProfiles])

  return (
    <div className="space-y-3 animate-fadeIn">
      <div className="flex items-center justify-between">
        <label className="block text-xs font-medium text-[#141413]">LinkedIn Engine</label>
        {linkedInStatus?.session_valid ? (
          <span className="flex items-center gap-1 text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
            Active Session
          </span>
        ) : (
          <span className="flex items-center gap-1 text-[10px] font-mono px-2 py-0.5 rounded-full bg-sky-50 text-sky-700 border border-sky-200">
            <Globe className="w-2.5 h-2.5" />
            Public Bridge Mode
          </span>
        )}
      </div>

      <p className="text-[11px] text-[#87867f] leading-tight">
        {linkedInStatus?.session_valid
          ? "Authenticated session active. Pulls home feed and full creator updates."
          : "Zero-auth public bridge active. Ingests public creator and company posts without login."}
      </p>

      {/* Creator & Company Handles */}
      <div>
        <label className="block text-[10px] font-mono text-[#87867f] mb-1">
          Target Handles (in/slug or company/slug):
        </label>
        <textarea
          rows={3}
          value={linkedInProfiles}
          onChange={(e) => setLinkedInProfiles(e.target.value)}
          placeholder="satyanadella&#10;company/cloudflare"
          className="w-full text-xs font-mono bg-[#faf9f5] border border-[#e3dacc] rounded-xl p-2.5 text-[#141413] focus:outline-none focus:border-[#141413] focus:ring-1 focus:ring-[#141413] placeholder-[#b0aea5]"
        />
      </div>

      {/* Quick Add Presets */}
      <div className="space-y-1">
        <span className="text-[10px] text-[#87867f] font-mono block">Creator Presets:</span>
        <div className="flex flex-wrap gap-1.5">
          {linkedInPresets.map((p) => {
            const isSelected = selectedHandles.has(p.handle)
            return (
              <button
                key={p.handle}
                type="button"
                onClick={() => onAddLinkedInPreset(p.handle)}
                className={`text-[10px] font-mono px-2.5 py-0.5 rounded-full border transition duration-150 flex items-center gap-1 ${
                  isSelected
                    ? 'bg-[#141413] text-[#faf9f5] border-[#141413] font-semibold shadow-xs'
                    : 'bg-[#faf9f5] text-[#87867f] hover:text-[#141413] border-[#e3dacc] hover:border-[#b0aea5]'
                }`}
                title={isSelected ? `Remove ${p.handle}` : `Add ${p.handle}`}
              >
                <span>{isSelected ? '✓' : '+'}</span>
                <span>{p.label}</span>
              </button>
            )
          })}
        </div>
      </div>

      {/* Auto-Sync Session Action */}
      <div className="pt-2 border-t border-[#e3dacc]/60 flex items-center justify-between gap-2">
        <button
          type="button"
          onClick={onSyncLinkedIn}
          disabled={syncingLinkedIn}
          className="flex items-center gap-1.5 text-[11px] font-sans px-3 py-1.5 rounded-xl bg-[#faf9f5] hover:bg-[#e3dacc]/70 border border-[#e3dacc] text-[#141413] transition disabled:opacity-50"
          title="Auto-extract session from local Playwright persistent browser context"
        >
          <RotateCw className={`w-3 h-3 ${syncingLinkedIn ? 'animate-spin' : ''}`} />
          <span>{syncingLinkedIn ? 'Syncing...' : 'Auto-Sync Session'}</span>
        </button>

        <span className="text-[10px] text-[#87867f] font-mono truncate max-w-[140px]">
          {linkedInStatus?.saved_at ? `Synced ${new Date(linkedInStatus.saved_at).toLocaleDateString()}` : 'No session'}
        </span>
      </div>

      {syncMsg && (
        <p className="text-[10px] font-mono text-[#c6613f] bg-[#f0eee6] p-1.5 rounded-lg border border-[#e3dacc]">
          {syncMsg}
        </p>
      )}

      {/* Optional Manual li_at Override */}
      <details className="group pt-1">
        <summary className="text-[10px] font-mono text-[#87867f] cursor-pointer hover:text-[#141413] transition select-none">
          ▸ Manual li_at Cookie Override
        </summary>
        <div className="mt-2 space-y-1">
          <input
            type="password"
            value={linkedInLiAt}
            onChange={(e) => setLinkedInLiAt(e.target.value)}
            placeholder="Paste li_at cookie..."
            className="w-full text-xs font-mono bg-[#faf9f5] border border-[#e3dacc] rounded-xl p-2 text-[#141413] focus:outline-none focus:border-[#141413] placeholder-[#b0aea5]"
          />
          <span className="text-[10px] text-[#87867f] block">
            DevTools &rarr; Application &rarr; Cookies &rarr; <code className="text-[#141413] bg-[#e3dacc]/50 px-1 rounded">li_at</code>
          </span>
        </div>
      </details>
    </div>
  )
}
