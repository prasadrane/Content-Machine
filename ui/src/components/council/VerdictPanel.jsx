import React from 'react'
import { CheckCircle2, RotateCw, XCircle, ChevronRight, Sparkles, Share2 } from 'lucide-react'

export default function VerdictPanel({
  result,
  best,
  draft,
  spikeId,
  humanizing,
  onLoadDraft,
  onHumanize,
  onSendToDistribute,
}) {
  if (!result) return null

  return (
    <div className="bg-[#faf9f5] border border-[#e3dacc] rounded-2xl p-6 space-y-6 shadow-anthropic">
      <div className="flex items-center justify-between">
        <div>
          <span className="text-xs font-mono uppercase text-[#87867f]">Current Run Score</span>
          <div className="text-3xl font-serif font-bold text-[#141413] mt-0.5">
            {result.score.toFixed(3)}
          </div>
        </div>

        <div className={`px-4 py-1.5 rounded-full border text-xs font-mono font-semibold uppercase tracking-wider flex items-center gap-1.5 ${
          result.verdict === 'pass' 
            ? 'bg-[#c6613f]/10 text-[#c6613f] border-[#c6613f]/30' 
            : result.verdict === 'revise'
            ? 'bg-[#d97757]/10 text-[#d97757] border-[#d97757]/30'
            : 'bg-rose-50 text-rose-800 border-rose-200'
        }`}>
          {result.verdict === 'pass' && <CheckCircle2 className="w-3.5 h-3.5" />}
          {result.verdict === 'revise' && <RotateCw className="w-3.5 h-3.5" />}
          {result.verdict === 'reject' && <XCircle className="w-3.5 h-3.5" />}
          <span>{result.verdict}</span>
        </div>
      </div>

      {/* Peak comparison note */}
      {best && best.score > result.score && (
        <div className="p-3 bg-[#f0eee6] border border-[#e3dacc] rounded-xl flex items-center justify-between gap-3 text-xs text-[#87867f]">
          <span>A previous iteration scored higher ({best.score.toFixed(3)}).</span>
          <button
            type="button"
            onClick={() => onLoadDraft(best.draft)}
            className="text-[#c6613f] hover:underline font-mono font-medium text-[11px]"
          >
            Restore Peak Draft
          </button>
        </div>
      )}

      {result.actions && result.actions.length > 0 && (
        <div className="space-y-3 pt-4 border-t border-[#e3dacc]">
          <h4 className="text-xs font-mono uppercase tracking-wider text-[#87867f]">Required Editorial Actions</h4>
          <ul className="space-y-2">
            {result.actions.map((act, idx) => (
              <li key={idx} className="text-xs text-[#141413] flex items-start gap-2 bg-[#f0eee6]/70 p-3 rounded-xl border border-[#e3dacc]">
                <ChevronRight className="w-3.5 h-3.5 text-[#c6613f] shrink-0 mt-0.5" />
                <span>{act}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

        {/* Revised draft note */}
        {result.draft && result.draft !== draft && (
          <div className="p-3.5 bg-[#f0eee6] border border-[#e3dacc] rounded-xl flex items-center justify-between gap-3 text-xs">
            <span className="text-[#141413]">Council revised this draft for iteration {result.iteration}.</span>
            <button
              type="button"
              onClick={() => onLoadDraft(result.draft)}
              className="text-[#c6613f] hover:underline font-mono font-medium text-[11px]"
            >
              Load Revised Draft
            </button>
          </div>
        )}

        <div className="pt-4 border-t border-[#e3dacc] flex items-center justify-between gap-3 flex-wrap">
          {(result.verdict === 'pass' || best?.draft) && (
            <button
              type="button"
              onClick={() => onHumanize(best?.draft || draft)}
              disabled={humanizing}
              className="px-4 py-2 bg-[#faf9f5] hover:bg-[#e3dacc]/50 text-[#c6613f] border border-[#c6613f]/40 hover:border-[#c6613f] rounded-full text-xs font-medium transition flex items-center gap-1.5 shadow-sm disabled:opacity-50"
            >
              {humanizing ? (
                <RotateCw className="w-3.5 h-3.5 animate-spin text-[#c6613f]" />
              ) : (
                <Sparkles className="w-3.5 h-3.5 text-[#c6613f]" />
              )}
              <span>{humanizing ? 'Humanizing...' : '🪄 Humanize Peak Draft'}</span>
            </button>
          )}

          {onSendToDistribute && (
            <button
              type="button"
              onClick={() => onSendToDistribute(draft, spikeId)}
              className="px-5 py-2.5 bg-[#141413] hover:bg-[#252524] text-[#faf9f5] rounded-full text-xs font-medium transition flex items-center gap-2 shadow-sm ml-auto"
            >
              <span>Distribute Current Post</span>
              <Share2 className="w-3.5 h-3.5 text-[#d97757]" />
            </button>
          )}
        </div>
      </div>
    )
  }

