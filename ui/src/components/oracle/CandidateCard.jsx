import React from 'react'
import {
  Sparkles,
  ArrowRight,
  ExternalLink,
  Copy,
  Check,
  X,
} from 'lucide-react'
import { DIMENSION_LABELS } from '../../lib/constants'
import { getTopicBadgeClass } from '../../lib/topics'
import { useCopyToClipboard } from '../../hooks/useCopyToClipboard'

export default function CandidateCard({ candidate, onSendToCouncil, onOpenInterview, onDismiss }) {
  const { copied, copy, setCopied } = useCopyToClipboard()

  const handleCopySummary = async (e) => {
    e.stopPropagation()
    const parts = [
      candidate.title,
      candidate.url ? `Source: ${candidate.url}` : null,
      candidate.source ? `Feed: ${candidate.source}` : null,
      candidate.body_snippet ? `Excerpt:\n${candidate.body_snippet}` : null,
    ].filter(Boolean)
    const text = parts.join('\n')

    if (!(await copy(text))) {
      try {
        const textArea = document.createElement('textarea')
        textArea.value = text
        textArea.style.position = 'fixed'
        textArea.style.opacity = '0'
        document.body.appendChild(textArea)
        textArea.focus()
        textArea.select()
        document.execCommand('copy')
        document.body.removeChild(textArea)
        setCopied(true)
        setTimeout(() => setCopied(false), 2000)
      } catch (fallbackErr) {
        console.error('Failed to copy', fallbackErr)
      }
    }
  }

  const renderDimensionScores = () => {
    if (!candidate.dimension_scores || typeof candidate.dimension_scores !== 'object') return null

    const seen = new Set()
    const chips = []
    const preferredOrder = ['lived_experience', 'novelty', 'counter_intuitive', 'specificity', 'pov', 'relevance', 'rigor']
    const allKeys = [...preferredOrder, ...Object.keys(candidate.dimension_scores)]

    for (const key of allKeys) {
      if (key === 'composite') continue
      const val = candidate.dimension_scores[key]
      if (typeof val !== 'number') continue
      const label = DIMENSION_LABELS[key] || (key.charAt(0).toUpperCase() + key.slice(1).replace(/_/g, ' '))
      if (seen.has(label)) continue
      seen.add(label)
      chips.push({ label, val: val.toFixed(1) })
      if (chips.length >= 5) break
    }

    if (chips.length === 0) return null

    return (
      <div className="flex items-center gap-1.5 flex-wrap pt-0.5">
        {chips.map(({ label, val }) => (
          <span
            key={label}
            className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-[#f0eee6] text-[#5c5a55] border border-[#e3dacc] flex items-center gap-1"
          >
            <span className="text-[#87867f]">{label}:</span>
            <span className="font-semibold text-[#141413]">{val}</span>
          </span>
        ))}
      </div>
    )
  }

  const isPass = candidate.verdict === 'pass'
  const isReview = candidate.verdict === 'review'
  const scoreFormatted = typeof candidate.score === 'number' ? candidate.score.toFixed(2) : candidate.score
  const verdictText = (candidate.verdict || 'PASS').toUpperCase()

  return (
    <div className="bg-[#faf9f5] hover:bg-[#f0eee6]/30 transition-all duration-200 border border-[#e3dacc] hover:border-[#b0aea5] rounded-2xl p-5 space-y-3.5 shadow-anthropic group">
      {/* Top Row: Topic Badge & Score Capsule */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2 flex-wrap">
          {candidate.topic_tag && (
            <span className={`text-[10px] font-medium px-2.5 py-0.5 rounded-full border ${getTopicBadgeClass(candidate.topic_tag)}`}>
              {candidate.topic_tag}
            </span>
          )}
          <span className="text-[11px] text-[#87867f] font-mono">{candidate.source}</span>
          {candidate.published_at && (
            <>
              <span className="text-[#b0aea5]">&bull;</span>
              <span className="text-[11px] text-[#87867f] font-mono">
                {new Date(candidate.published_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}
              </span>
            </>
          )}
        </div>

        {/* Score Capsule: PASS 8.95 */}
        <div className="flex items-center shrink-0">
          <span className={`text-xs font-mono font-semibold px-2.5 py-0.5 rounded-full border flex items-center gap-1.5 ${
            isPass
              ? 'bg-[#c6613f]/10 text-[#c6613f] border-[#c6613f]/30'
              : isReview
              ? 'bg-[#d97757]/10 text-[#d97757] border-[#d97757]/30'
              : 'bg-[#f0eee6] text-[#87867f] border-[#e3dacc]'
          }`}>
            <span className="text-[10px] uppercase font-bold tracking-wider">{verdictText}</span>
            <span className="font-bold">{scoreFormatted}</span>
          </span>
        </div>
      </div>

      {/* Title (Clickable link to source) */}
      <div>
        {candidate.url ? (
          <a
            href={candidate.url}
            target="_blank"
            rel="noreferrer"
            className="text-base font-serif font-medium text-[#141413] hover:text-[#c6613f] transition leading-snug inline-block"
          >
            {candidate.title}
          </a>
        ) : (
          <h4 className="text-base font-serif font-medium text-[#141413] leading-snug">
            {candidate.title}
          </h4>
        )}
      </div>

      {/* 2-line Clean Excerpt Preview */}
      {candidate.body_snippet && (
        <p
          className="text-xs text-[#5c5a55] font-sans leading-relaxed line-clamp-2"
          style={{
            display: '-webkit-box',
            WebkitLineClamp: 2,
            WebkitBoxOrient: 'vertical',
            overflow: 'hidden',
          }}
        >
          {candidate.body_snippet}
        </p>
      )}

      {/* Dimension Scores Micro-Chips */}
      {renderDimensionScores()}

      {/* Card Footer Action Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-[#e3dacc]">
        {/* Quick Actions */}
        <div className="flex items-center gap-1.5 flex-wrap">
          {/* Brief & Perspective (Subsystem 2) */}
          {onOpenInterview && (
            <button
              type="button"
              onClick={() => onOpenInterview(candidate)}
              className="text-xs text-[#87867f] hover:text-[#141413] px-2.5 py-1 rounded-full hover:bg-[#e3dacc]/50 transition flex items-center gap-1 font-medium"
              title="Open Topic Briefing & Perspective Intake"
            >
              <Sparkles className="w-3 h-3 text-[#d97757]" />
              <span>Perspective</span>
            </button>
          )}

          {/* Copy Summary */}
          <button
            type="button"
            onClick={handleCopySummary}
            className={`text-xs px-2.5 py-1 rounded-full transition flex items-center gap-1 font-mono ${
              copied
                ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                : 'text-[#87867f] hover:text-[#141413] hover:bg-[#e3dacc]/50'
            }`}
            title="Copy title, link, and excerpt to clipboard"
          >
            {copied ? (
              <>
                <Check className="w-3 h-3 text-emerald-600 stroke-[2.5]" />
                <span className="font-semibold">Copied!</span>
              </>
            ) : (
              <>
                <Copy className="w-3 h-3" />
                <span>Copy Summary</span>
              </>
            )}
          </button>

          {/* Open Source */}
          {candidate.url && (
            <a
              href={candidate.url}
              target="_blank"
              rel="noreferrer"
              className="text-xs text-[#87867f] hover:text-[#141413] px-2 py-1 rounded-full hover:bg-[#e3dacc]/50 transition inline-flex items-center gap-1 font-mono"
              title="Open source URL in new tab"
            >
              <span>Open Source</span>
              <ExternalLink className="w-3 h-3" />
            </a>
          )}

          {/* Dismiss */}
          <button
            type="button"
            onClick={() => onDismiss(candidate)}
            className="text-xs text-[#87867f] hover:text-rose-600 px-2 py-1 rounded-full hover:bg-rose-50 transition flex items-center gap-1 font-mono"
            title="Dismiss candidate from active batch"
          >
            <X className="w-3 h-3" />
            <span>Dismiss</span>
          </button>
        </div>

        {/* Primary Action: Send to Council */}
        <button
          type="button"
          onClick={() => onSendToCouncil(candidate)}
          className="py-1.5 px-4 bg-[#141413] hover:bg-[#252524] text-[#faf9f5] rounded-full text-xs font-medium transition flex items-center gap-1.5 shadow-sm ml-auto shrink-0"
        >
          <span>Send to Council</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  )
}
