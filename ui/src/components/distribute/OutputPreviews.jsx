import React from 'react'
import { Share2, RotateCw, Check, Copy } from 'lucide-react'

export default function OutputPreviews({
  bundle,
  loading,
  slug,
  availableFormats,
  activeFormat,
  onFormatChange,
  copied,
  onCopy,
  getFormatContent,
  anchorSnapshot,
  isEarlier,
  origin,
}) {
  return (
    <div className="space-y-4 min-w-0">
      <div className="cm-divider flex items-center justify-between">
        <h3 className="cm-panel-title">Derivative Formats</h3>
        {bundle && (
          <span className="cm-muted">Anchor: {anchorSnapshot?.slug || slug}</span>
        )}
      </div>
      {anchorSnapshot && bundle && (
        <div className="cm-subpanel space-y-2">
          <p role="status">{origin === 'replayed' ? 'Replayed sample output; the actual sample anchor is unavailable in this response.' : `${isEarlier ? 'These outputs belong to an earlier anchor version.' : 'Outputs for this anchor version.'} ${origin === 'stored' ? 'Stored output; approval history is unavailable.' : 'Generated output; review before publishing.'}`}</p>
          <details><summary className="cm-label cursor-pointer">{origin === 'replayed' ? 'Submitted input (not the source of this replay)' : 'Original anchor'} · version {anchorSnapshot.version}</summary><p className="cm-prose whitespace-pre-wrap break-words mt-2">{anchorSnapshot.text}</p></details>
        </div>
      )}

      {!bundle && !loading && (
        <div className="cm-empty text-center">
          <Share2 className="w-8 h-8 mx-auto mb-3 stroke-1 text-[#b0aea5]" />
          <p className="cm-prose font-medium">No derivatives generated yet.</p>
          <p className="cm-muted mt-1">Submit anchor text to generate LinkedIn post, X thread, video scripts, and newsletter.</p>
        </div>
      )}

      {loading && (
        <div className="cm-subpanel text-center space-y-3">
          <RotateCw className="w-6 h-6 mx-auto animate-spin text-[#c6613f]" />
          <p className="cm-prose font-medium">Generating Enabled Platform Derivatives...</p>
          <p className="cm-muted">Waiting for channel formats. Review factual claims before use.</p>
        </div>
      )}

      {bundle && (
        <div className="space-y-4">
          {/* Channel Switcher */}
          <div className="cm-subpanel flex flex-wrap gap-2 items-center justify-between">
            <div className="flex flex-wrap items-center gap-1" role="group" aria-label="Output formats">
              {availableFormats.map(fmt => {
                const isActive = activeFormat === fmt.id || (fmt.id === 'video_script_short' && activeFormat === 'video_script')
                const isLinkedIn = fmt.id === 'linkedin'
                return (
                  <button
                    key={fmt.id}
                    type="button"
                    aria-pressed={isActive}
                    onClick={() => onFormatChange(fmt.id)}
                    className={`cm-chip ${isActive ? 'cm-chip-active' : ''}`}
                  >
                    {isLinkedIn && <span className="w-1.5 h-1.5 rounded-full bg-[#d97757]" />}
                    <span>{fmt.shortLabel}</span>
                  </button>
                )
              })}
            </div>

            <button
              type="button"
              onClick={() => onCopy(getFormatContent(activeFormat))}
              className="cm-button cm-button-secondary flex items-center gap-1.5 shrink-0 ml-2"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5 text-[#87867f]" />}
              <span>{copied ? 'Copied!' : 'Copy'}</span>
            </button>
          </div>
          <p className="cm-muted">{getFormatContent(activeFormat).length} characters{activeFormat === 'x_thread' ? ' across the thread; check each post separately' : ''}</p>

          {/* Text Preview Box */}
          <div className="cm-panel whitespace-pre-wrap break-words">
            {getFormatContent(activeFormat) || 'No content available for this format.'}
          </div>
        </div>
      )}
    </div>
  )
}
