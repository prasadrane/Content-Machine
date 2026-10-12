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
  isApproved = true,
  reviewed = false,
  onReviewedChange = () => {},
  onApprove = () => {},
}) {
  return (
    <form onSubmit={onSubmit} className="space-y-4 bg-[#f0eee6]/60 p-6 rounded-2xl border border-[#e3dacc] shadow-anthropic">
      <div className="flex items-center justify-between">
        <h3 className="text-xs uppercase font-mono tracking-wider text-[#87867f]">Anchor Post (Verified)</h3>
        <input
          type="text"
          value={slug}
          onChange={(e) => onSlugChange(e.target.value)}
          placeholder="Project Slug"
          className="text-xs font-mono bg-[#faf9f5] border border-[#e3dacc] rounded-lg px-2.5 py-1 text-[#141413] w-36 focus:outline-none focus:border-[#141413]"
        />
      </div>

      <textarea
        rows={16}
        value={anchorText}
        onChange={(e) => onAnchorChange(e.target.value)}
        placeholder="Paste your approved anchor post or final draft..."
        className="w-full text-xs font-mono leading-relaxed bg-[#faf9f5] border border-[#e3dacc] rounded-xl p-4 text-[#141413] focus:outline-none focus:border-[#141413] resize-none placeholder-[#b0aea5]"
      />

      {/* Active Platform Chips */}
      <div className="flex items-center justify-between gap-2 p-3 bg-[#faf9f5] border border-[#e3dacc] rounded-xl">
        <div className="flex items-center gap-1.5 flex-wrap text-[11px] font-mono">
          <span className="text-[#87867f] mr-1">Active:</span>
          {DISTRIBUTION_FORMATS.map(fmt => {
            const isEnabled = enabledFormats[fmt.id]
            return (
              <span
                key={fmt.id}
                onClick={() => onToggleFormat(fmt.id)}
                className={`cursor-pointer px-2.5 py-0.5 rounded-full border transition ${
                  isEnabled
                    ? fmt.id === 'linkedin'
                      ? 'bg-[#141413] text-[#faf9f5] border-[#141413] font-semibold'
                      : 'bg-[#f0eee6] text-[#141413] border-[#b0aea5] hover:border-[#141413]'
                    : 'opacity-40 line-through text-[#87867f] border-transparent hover:opacity-60'
                }`}
              >
                {fmt.shortLabel}
              </span>
            )
          })}
        </div>
        <button
          type="button"
          onClick={onOpenConfig}
          className="text-xs text-[#c6613f] hover:text-[#a54c2d] font-mono flex items-center gap-1 shrink-0"
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
          <span>Approved by you. Editing the text will require approval again.</span>
        </div>
      ) : (
        <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-amber-900 text-xs space-y-2">
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
        <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-800 text-xs flex items-center gap-2">
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
