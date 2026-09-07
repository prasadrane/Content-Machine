import React from 'react'
import { Sparkles, FileText, Check, Copy, X } from 'lucide-react'

export default function HumanizedDraftCard({
  humanizedResult,
  onUseInEditor,
  onCopy,
  copied,
  onDismiss,
}) {
  if (!humanizedResult) return null

  return (
    <div className="p-6 bg-[#faf9f5] border border-[#e3dacc] rounded-2xl shadow-anthropic space-y-4 animate-fadeIn">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#e3dacc] pb-4">
        <div className="flex items-center gap-2.5 flex-wrap">
          <div className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono font-semibold bg-[#c6613f]/10 text-[#c6613f] border border-[#c6613f]/30">
            <Sparkles className="w-3.5 h-3.5" />
            <span>Humanized ✨ (Burstiness: {typeof humanizedResult.burstiness_score === 'number' ? humanizedResult.burstiness_score.toFixed(1) : humanizedResult.burstiness_score})</span>
          </div>
          <span className="text-[11px] font-mono px-2.5 py-0.5 rounded-full bg-[#f0eee6] text-[#87867f] border border-[#e3dacc]">
            {humanizedResult.sentence_count || 0} sentences
          </span>
          <span className="text-[11px] font-mono px-2.5 py-0.5 rounded-full bg-[#f0eee6] text-[#87867f] border border-[#e3dacc]">
            Tone: Pragmatic Architect
          </span>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => onUseInEditor(humanizedResult.humanized_text)}
            className="px-3.5 py-1.5 rounded-full text-xs font-mono font-medium transition bg-[#141413] hover:bg-[#252524] text-[#faf9f5] flex items-center gap-1.5 shadow-sm"
            title="Replace editor content with this humanized version"
          >
            <FileText className="w-3.5 h-3.5 text-[#d97757]" />
            <span>Use in Editor</span>
          </button>

          <button
            type="button"
            onClick={() => onCopy(humanizedResult.humanized_text)}
            className="px-3.5 py-1.5 rounded-full text-xs font-mono font-medium transition bg-[#faf9f5] hover:bg-[#e3dacc]/50 text-[#141413] border border-[#e3dacc] flex items-center gap-1.5 shadow-sm"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5 text-[#87867f]" />}
            <span>{copied ? 'Copied!' : 'Copy'}</span>
          </button>

          <button
            type="button"
            onClick={onDismiss}
            className="p-1.5 rounded-full text-[#87867f] hover:text-[#141413] hover:bg-[#f0eee6] transition"
            title="Dismiss"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Purged Clichés Chips */}
      {humanizedResult.banned_words_purged && humanizedResult.banned_words_purged.length > 0 && (
        <div className="flex items-center gap-2 flex-wrap text-xs">
          <span className="text-[#87867f] font-mono text-[11px] uppercase tracking-wider font-semibold">
            Purged AI Clichés ({humanizedResult.banned_words_purged.length}):
          </span>
          {humanizedResult.banned_words_purged.map((word, idx) => (
            <span
              key={idx}
              className="px-2.5 py-0.5 rounded-full text-[11px] font-mono bg-rose-50 text-rose-800 border border-rose-200 line-through"
            >
              {word}
            </span>
          ))}
        </div>
      )}

      {/* Humanized Text Box */}
      <div className="bg-[#f0eee6]/40 border border-[#e3dacc] rounded-xl p-5 font-serif text-sm sm:text-base leading-relaxed text-[#141413] whitespace-pre-wrap selection:bg-[#c6613f]/20">
        {humanizedResult.humanized_text}
      </div>
    </div>
  )
}
