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
import { formatTopicLabel } from '../../lib/topics'
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
            className="cm-badge flex items-center gap-1"
          >
            <span className="text-anthropic-cloud-dark">{label}:</span>
            <span className="font-semibold text-anthropic-slate-dark">{val}</span>
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
    <div className="cm-panel duration-200 space-y-3.5 group">
      {/* Top Row: Topic Badge & Score Capsule */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2 flex-wrap">
          {candidate.topic_tag && (
            <span className="cm-badge">
              {formatTopicLabel(candidate.topic_tag)}
            </span>
          )}
          <span className="text-sm text-anthropic-cloud-dark">{candidate.source}</span>
          {candidate.published_at && (
            <>
              <span className="text-anthropic-cloud-medium">&bull;</span>
              <span className="text-sm text-anthropic-cloud-dark">
                {new Date(candidate.published_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}
              </span>
            </>
          )}
        </div>

        {/* Score Capsule: PASS 8.95 */}
        <div className="flex items-center shrink-0">
          <span className={` cm-badge flex items-center gap-1.5 ${
            isPass
              ? ""
              : isReview
              ? ""
              : ""
          }  `}>
            <span className="text-sm uppercase font-bold tracking-wider">{verdictText}</span>
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
            className="cm-panel-title leading-snug inline-block"
          >
            {candidate.title}
          </a>
        ) : (
          <h4 className="cm-panel-title leading-snug">
            {candidate.title}
          </h4>
        )}
      </div>

      {/* 2-line Clean Excerpt Preview */}
      {candidate.body_snippet && (
        <p
          className="cm-prose leading-relaxed line-clamp-2"
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
      {candidate.dimension_scores && <details className="text-sm text-anthropic-cloud-dark"><summary className="cursor-pointer">Score breakdown</summary>{renderDimensionScores()}</details>}

      {/* Card Footer Action Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-anthropic-oat">
        {/* Quick Actions */}
        <div className="flex items-center gap-1.5 flex-wrap">
          {/* Brief & Perspective (Subsystem 2) */}
          {onOpenInterview && (
            <button
              type="button"
              onClick={() => onSendToCouncil(candidate)}
              className="cm-button cm-button-quiet flex items-center gap-1"
              title="Start a draft directly without an interview"
            >
              <Sparkles className="w-3 h-3 text-anthropic-clay" />
              <span>Review a draft</span>
            </button>
          )}

          {/* Copy Summary */}
          <button
            type="button"
            onClick={handleCopySummary}
            className={` cm-button cm-button-quiet flex items-center gap-1 ${
              copied
                ? "cm-status-success"
                : ""
            }  `}
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
              className="cm-link inline-flex items-center gap-1"
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
            className="cm-button cm-button-quiet flex items-center gap-1"
            title="Dismiss candidate from active batch"
          >
            <X className="w-3 h-3" />
            <span>Dismiss</span>
          </button>
        </div>

        {/* Primary Action: Send to Council */}
        <button
          type="button"
          onClick={() => onOpenInterview ? onOpenInterview(candidate) : onSendToCouncil(candidate)}
          className="cm-button cm-button-primary flex items-center gap-1.5 ml-auto shrink-0"
        >
          <span>{onOpenInterview ? 'Add my perspective' : 'Send to Council'}</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  )
}
