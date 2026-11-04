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
    <form onSubmit={onSubmit} className="space-y-4 bg-[#f0eee6]/60 p-6 rounded-2xl border border-[#e3dacc] shadow-anthropic">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h3 className="text-sm font-semibold text-[#141413]">Anchor post</h3>
        <label className="text-sm text-[#58574f] flex flex-col gap-1">
          Post identifier
        <input
          type="text"
          value={slug}
          onChange={(e) => onSlugChange(e.target.value)}
          placeholder="Project Slug"
          className="text-sm font-mono bg-[#faf9f5] border border-[#b0aea5] rounded-lg px-2.5 py-2 text-[#141413] w-36 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#141413]"
        />
        </label>
      </div>

      <textarea
        aria-label="Anchor post"
        rows={16}
        value={anchorText}
        onChange={(e) => onAnchorChange(e.target.value)}
        placeholder="Paste your approved anchor post or final draft..."
        className="w-full text-base leading-relaxed bg-[#faf9f5] border border-[#b0aea5] rounded-xl p-4 text-[#141413] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#141413] resize-y placeholder-[#68675f]"
      />

      {/* Active Platform Chips */}
      <div className="flex flex-wrap items-center justify-between gap-2 p-3 bg-[#faf9f5] border border-[#e3dacc] rounded-xl">
        <div role="group" aria-label="Channel formats" className="flex items-center gap-2 flex-wrap text-sm">
          <span className="text-[#58574f] mr-1">Formats:</span>
          {DISTRIBUTION_FORMATS.map(fmt => {
            const isEnabled = enabledFormats[fmt.id]
            return (
              <button
                key={fmt.id}
                type="button"
                aria-pressed={Boolean(isEnabled)}
                onClick={() => onToggleFormat(fmt.id)}
                className={`min-h-9 px-3 py-1.5 rounded-full border transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#141413] ${
                  isEnabled
                    ? fmt.id === 'linkedin'
                      ? 'bg-[#141413] text-[#faf9f5] border-[#141413] font-semibold'
                      : 'bg-[#f0eee6] text-[#141413] border-[#b0aea5] hover:border-[#141413]'
                    : 'text-[#58574f] border-[#b0aea5] border-dashed hover:bg-[#f0eee6]'
                }`}
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
          className="min-h-9 text-sm text-[#a54c2d] font-medium flex items-center gap-1 shrink-0"
        >
          <Settings className="w-3 h-3" />
          <span>Edit</span>
        </button>
      </div>

      {/* Humanize Polish Control Bar */}
      <div className="p-3.5 bg-[#faf9f5] border border-[#e3dacc] rounded-xl space-y-2.5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-xs uppercase font-mono tracking-wider text-[#87867f] font-semibold">
              Humanize Polish
            </span>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-[#f0eee6] text-[#87867f] border border-[#e3dacc]">
              Cross-Channel De-AI
            </span>
          </div>
          <button
            type="button"
            aria-pressed={humanize}
            onClick={onHumanizeToggle}
            className={`px-3 py-1 rounded-full text-xs font-mono font-medium transition flex items-center gap-1.5 border shadow-sm ${
              humanize
                ? 'bg-[#c6613f] text-[#faf9f5] border-[#c6613f]'
                : 'bg-[#f0eee6] text-[#87867f] border-[#e3dacc] hover:text-[#141413]'
            }`}
          >
            <span>🪄 Humanize Polish</span>
            <span className={`px-1.5 py-0.2 rounded text-[10px] font-bold ${humanize ? 'bg-[#faf9f5]/20 text-[#faf9f5]' : 'bg-[#e3dacc] text-[#87867f]'}`}>
              {humanize ? 'ON' : 'OFF'}
            </span>
          </button>
        </div>

        {humanize && (
          <div className="pt-2 border-t border-[#e3dacc]/60 flex items-center gap-1.5 flex-wrap">
            <span className="text-[11px] font-mono text-[#87867f] mr-1">Tone:</span>
            {HUMANIZE_TONES.map(t => {
              const active = humanizeTone === t.id
              return (
                <button
                  key={t.id}
                  type="button"
                  aria-pressed={active}
                  onClick={() => onToneChange(t.id)}
                  className={`px-2.5 py-1 rounded-full text-[11px] font-mono border transition ${
                    active
                      ? 'bg-[#141413] text-[#faf9f5] border-[#141413] shadow-sm font-semibold'
                      : 'bg-[#f0eee6] text-[#87867f] hover:text-[#141413] border-[#e3dacc]'
                  }`}
                >
                  {t.label}
                </button>
              )
            })}
          </div>
        )}
      </div>

      {isApproved ? (
        <div role="status" className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-900 text-xs flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 shrink-0" />
          <span><strong>Approved by you</strong>. Editing the text will require approval again.</span>
        </div>
      ) : (
        <div role="status" className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-amber-900 text-sm space-y-2">
          <p className="font-semibold">Needs approval</p>
          <p>This text has not been approved. Derivatives are only generated for text you explicitly approve (use Approve in the Council tab, or confirm here).</p>
          <label className="flex items-start gap-2 cursor-pointer">
            <input type="checkbox" checked={reviewed} onChange={(e) => onReviewedChange(e.target.checked)} className="mt-0.5" />
            <span>I have read this exact text and approve it for distribution.</span>
          </label>
          <button
            type="button"
            disabled={!reviewed || !anchorText.trim()}
            onClick={onApprove}
            className="px-3 py-1.5 rounded-full text-xs font-medium bg-[#141413] text-[#faf9f5] disabled:opacity-40"
          >
            Approve this text
          </button>
        </div>
      )}

      {error && (
        <div role="alert" className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-800 text-sm flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
          <span>{error}</span>
        </div>
      )}

      <button
        type="submit"
        disabled={loading || !isApproved}
        className="w-full py-2.5 px-4 bg-[#141413] hover:bg-[#252524] disabled:opacity-50 text-[#faf9f5] rounded-full text-xs font-medium transition flex items-center justify-center gap-2 shadow-sm"
      >
        {loading ? <RotateCw className="w-3.5 h-3.5 animate-spin" /> : <Share2 className="w-3.5 h-3.5 text-[#d97757]" />}
        <span>{loading ? 'Synthesizing Platform Derivatives...' : `Generate Platform Bundle (${activeFormatCount} Formats)`}</span>
      </button>
    </form>
  )
}
