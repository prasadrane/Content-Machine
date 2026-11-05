import React from 'react'
import { Settings, AlertCircle, RotateCw, Share2, ShieldCheck } from 'lucide-react'
import { DISTRIBUTION_FORMATS, HUMANIZE_TONES } from '../../lib/constants'

export default function AnchorForm({
  anchorText,
  onAnchorChange,
  slug,
  onSlugChange,
  enabledFormats,
  onToggleFormat,
  onOpenConfig,
  humanize,
  onHumanizeToggle,
  humanizeTone,
  onToneChange,
  loading,
  error,
  onSubmit,
  activeFormatCount,
  isApproved = false,
  reviewed = false,
  onReviewedChange = () => {},
  onApprove = () => {},
}) {
  return (
    <form onSubmit={onSubmit} className="cm-panel space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h3 className="cm-panel-title">Anchor post</h3>
        <label className="cm-label flex flex-col gap-1">
          Post identifier
        <input
          type="text"
          value={slug}
          onChange={(e) => onSlugChange(e.target.value)}
          placeholder="Project Slug"
          className="cm-input w-36"
        />
        </label>
      </div>

      <textarea
        aria-label="Anchor post"
        rows={16}
        value={anchorText}
        onChange={(e) => onAnchorChange(e.target.value)}
        placeholder="Paste your approved anchor post or final draft..."
        className="cm-textarea w-full resize-y"
      />

      {/* Active Platform Chips */}
      <div className="cm-subpanel flex flex-wrap items-center justify-between gap-2">
        <div role="group" aria-label="Channel formats" className="flex items-center gap-2 flex-wrap text-sm">
          <span className="cm-muted mr-1">Formats:</span>
          {DISTRIBUTION_FORMATS.map(fmt => {
            const isEnabled = enabledFormats[fmt.id]
            return (
              <button
                key={fmt.id}
                type="button"
                aria-pressed={Boolean(isEnabled)}
                onClick={() => onToggleFormat(fmt.id)}
                className={`cm-chip ${isEnabled ? 'cm-chip-active' : ''}`}
              >
                {fmt.shortLabel}
              </button>
            )
          })}
        </div>
        <button
          type="button"
          onClick={onOpenConfig}
          aria-label="Edit channel formats"
          className="cm-button cm-button-quiet flex items-center gap-1 shrink-0"
        >
          <Settings className="w-3 h-3" />
          <span>Edit</span>
        </button>
      </div>

      {/* Humanize Polish Control Bar */}
      <div className="cm-subpanel space-y-2.5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="cm-muted font-semibold">
              Humanize Polish
            </span>
            <span className="cm-badge">
              Cross-Channel De-AI
            </span>
          </div>
          <button
            type="button"
            aria-pressed={humanize}
            onClick={onHumanizeToggle}
            className={`cm-chip ${humanize ? 'cm-chip-active' : ''}`}
          >
            <span>🪄 Humanize Polish</span>
            <span className="font-semibold">
              {humanize ? 'ON' : 'OFF'}
            </span>
          </button>
        </div>

        {humanize && (
          <div className="cm-divider flex items-center gap-1.5 flex-wrap">
            <span className="cm-muted mr-1">Tone:</span>
            {HUMANIZE_TONES.map(t => {
              const active = humanizeTone === t.id
              return (
                <button
                  key={t.id}
                  type="button"
                  aria-pressed={active}
                  onClick={() => onToneChange(t.id)}
                  className={`cm-chip ${active ? 'cm-chip-active' : ''}`}
                >
                  {t.label}
                </button>
              )
            })}
          </div>
        )}
      </div>

      {isApproved ? (
        <div role="status" className="cm-status cm-status-success flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 shrink-0" />
          <span><strong>Approved by you</strong>. Editing the text will require approval again.</span>
        </div>
      ) : (
        <div role="status" className="cm-status cm-status-warning space-y-2">
          <p className="font-semibold">Needs approval</p>
          <p>This text has not been approved. Derivatives are only generated for text you explicitly approve (use Approve in the Council tab, or confirm here).</p>
          <label className="cm-label flex items-start gap-2 cursor-pointer">
            <input type="checkbox" checked={reviewed} onChange={(e) => onReviewedChange(e.target.checked)} className="mt-1" />
            <span>I have read this exact text and approve it for distribution.</span>
          </label>
          <button
            type="button"
            disabled={!reviewed || !anchorText.trim()}
            onClick={onApprove}
            className="cm-button cm-button-primary"
          >
            Approve this text
          </button>
        </div>
      )}

      {error && (
        <div role="alert" className="cm-status cm-status-error flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
          <span>{error}</span>
        </div>
      )}

      <button
        type="submit"
        disabled={loading || !isApproved}
        className="cm-button cm-button-primary w-full flex items-center justify-center gap-2"
      >
        {loading ? <RotateCw className="w-3.5 h-3.5 animate-spin" /> : <Share2 className="w-3.5 h-3.5 text-[#d97757]" />}
        <span>{loading ? 'Synthesizing Platform Derivatives...' : `Generate Platform Bundle (${activeFormatCount} Formats)`}</span>
      </button>
    </form>
  )
}
