import React from 'react'
import { CheckCircle2, AlertCircle, Sparkles, Copy, Check, Users, ChevronUp, ChevronDown, ChevronRight } from 'lucide-react'
import { countSentences } from '../../lib/textStats'

const COUNCIL_JUDGES = [
  {
    id: 'perell',
    name: 'David Perell',
    role: 'Thesis & Signal',
    description: 'Originality, counter-intuitive insight, and compelling hook',
  },
  {
    id: 'puri',
    name: 'Shaan Puri',
    role: 'Brevity & Punch',
    description: 'Fast velocity, high impact per word, zero conversational filler',
  },
  {
    id: 'housel',
    name: 'Morgan Housel',
    role: 'Psychology & Timelessness',
    description: 'Deeper human and market dynamics, timeless principles',
  },
  {
    id: 'slop_allergist',
    name: 'Slop Allergist',
    role: 'Zero Cliches / Platitudes',
    description: 'Purges generic praise ("Great post!"), platitudes, and empty jargon',
  },
]

function getVerdictBadge(peakScore, verdict) {
  const scoreText = typeof peakScore === 'number' ? peakScore.toFixed(1) : '-'
  const cleanVerdict = (verdict || 'publish').toLowerCase()

  if (cleanVerdict === 'publish' || cleanVerdict === 'pass' || peakScore >= 8.5) {
    return {
      label: `${scoreText} / 10 • PASSED COUNCIL`,
      classes: 'bg-emerald-100 text-emerald-800 border-emerald-300/80',
      icon: CheckCircle2,
    }
  }
  if (cleanVerdict === 'break_with_best') {
    return {
      label: `${scoreText} / 10 • BREAK-WITH-BEST`,
      classes: 'bg-amber-100 text-amber-900 border-amber-300/80',
      icon: AlertCircle,
    }
  }
  return {
    label: `${scoreText} / 10 • ${cleanVerdict.toUpperCase().replace(/_/g, '-')}`,
    classes: 'bg-rose-100 text-rose-900 border-rose-300/80',
    icon: AlertCircle,
  }
}

export default function PolishCard({ result, copied, onCopy, accordionOpen, onToggleAccordion }) {
  if (!result) return null

  const badge = getVerdictBadge(result.peak_score, result.verdict)
  const IconComponent = badge.icon

  return (
    <div className="bg-[#faf9f5] border border-[#e3dacc] rounded-2xl p-6 sm:p-7 space-y-6 shadow-anthropic animate-fadeIn">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#e3dacc] pb-4">
        <div className="flex items-center gap-2.5 flex-wrap">
          <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono font-semibold border ${badge.classes}`}>
            <IconComponent className="w-3.5 h-3.5" />
            <span>{badge.label}</span>
          </span>
          {result.humanized && (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono font-semibold bg-[#c6613f]/10 text-[#c6613f] border border-[#c6613f]/30">
              <Sparkles className="w-3.5 h-3.5" />
              <span>Humanized ✨ (Burstiness: {typeof result.burstiness_score === 'number' ? result.burstiness_score.toFixed(1) : (result.burstiness_score || '0.0')})</span>
            </span>
          )}
          <span className="text-[11px] font-mono px-2.5 py-0.5 rounded-full bg-[#f0eee6] text-[#141413] border border-[#e3dacc]">
            Iter {result.iteration}
          </span>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-[11px] font-mono px-2.5 py-0.5 rounded-full bg-[#f0eee6] text-[#87867f] border border-[#e3dacc]">
            {countSentences(result.final_comment)} sentences
          </span>
          <span className="text-[11px] font-mono px-2.5 py-0.5 rounded-full bg-[#f0eee6] text-[#87867f] border border-[#e3dacc]">
            {result.final_comment ? result.final_comment.length : 0} chars
          </span>
        </div>
      </div>

      {/* Generated Comment Block */}
      <div className="bg-[#f0eee6]/40 border border-[#e3dacc] rounded-2xl p-5 sm:p-6 relative space-y-4 shadow-anthropic">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-mono uppercase tracking-wider text-[#87867f] font-semibold">
            Polished Comment
          </span>
          <button
            type="button"
            onClick={() => onCopy(result.final_comment)}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-xs font-mono font-medium transition bg-[#141413] hover:bg-[#252524] text-[#faf9f5] shadow-sm"
          >
            {copied ? (
              <>
                <Check className="w-3.5 h-3.5 text-emerald-400" />
                <span>Copied!</span>
              </>
            ) : (
              <>
                <Copy className="w-3.5 h-3.5" />
                <span>Copy Comment</span>
              </>
            )}
          </button>
        </div>

        <blockquote className="font-serif text-base sm:text-lg text-[#141413] leading-relaxed whitespace-pre-wrap selection:bg-[#c6613f]/20">
          {result.final_comment}
        </blockquote>

        {result.initial_draft && result.initial_draft !== result.final_comment && (
          <details className="pt-3 border-t border-[#e3dacc]/70 text-xs text-[#87867f]">
            <summary className="cursor-pointer font-mono text-[11px] hover:text-[#141413]">
              View Initial Draft (Pre-Council Polish)
            </summary>
            <div className="mt-2 p-3 bg-[#faf9f5] border border-[#e3dacc] rounded-xl font-serif text-xs leading-relaxed text-[#87867f] italic">
              {result.initial_draft}
            </div>
          </details>
        )}
      </div>

      {/* Expandable Council Deliberation Accordion */}
      <div className="border border-[#e3dacc] rounded-xl overflow-hidden bg-[#faf9f5]">
        <button
          type="button"
          onClick={onToggleAccordion}
          className="w-full px-5 py-3.5 bg-[#f0eee6]/50 hover:bg-[#f0eee6] flex items-center justify-between text-left transition"
        >
          <div className="flex items-center gap-2">
            <Users className="w-4 h-4 text-[#c6613f]" />
            <span className="text-xs font-mono uppercase tracking-wider text-[#141413] font-semibold">
              Writer's Council Deliberation &amp; Critiques
            </span>
          </div>
          {accordionOpen ? (
            <ChevronUp className="w-4 h-4 text-[#87867f]" />
          ) : (
            <ChevronDown className="w-4 h-4 text-[#87867f]" />
          )}
        </button>

        {accordionOpen && (
          <div className="p-5 space-y-4 border-t border-[#e3dacc] bg-[#faf9f5] animate-fadeIn">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
              {COUNCIL_JUDGES.map((judge) => {
                const score =
                  result.judge_scores?.[judge.id] ??
                  result.judge_scores?.[judge.id.toLowerCase()]
                const critique =
                  result.judge_critiques?.[judge.id] ??
                  result.judge_critiques?.[judge.id.toLowerCase()] ??
                  'No specific critique logged.'

                const scoreColor =
                  typeof score === 'number'
                    ? score >= 8.5
                      ? 'bg-emerald-100 text-emerald-800 border-emerald-300'
                      : score >= 7.0
                      ? 'bg-amber-100 text-amber-900 border-amber-300'
                      : 'bg-rose-100 text-rose-900 border-rose-300'
                    : 'bg-[#f0eee6] text-[#87867f] border-[#e3dacc]'

                return (
                  <div
                    key={judge.id}
                    className="bg-[#f0eee6]/40 border border-[#e3dacc] rounded-xl p-4 space-y-2 shadow-anthropic"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <div>
                        <span className="text-xs font-medium text-[#141413] block">{judge.name}</span>
                        <span className="text-[10px] font-mono text-[#87867f] block">{judge.role}</span>
                      </div>
                      <span className={`text-xs font-mono font-semibold px-2 py-0.5 rounded-full border ${scoreColor}`}>
                        {typeof score === 'number' ? `${score.toFixed(1)} / 10` : '-'}
                      </span>
                    </div>
                    <p className="text-xs font-serif text-[#141413] leading-relaxed italic">
                      "{critique}"
                    </p>
                  </div>
                )
              })}
            </div>

            {result.actions && result.actions.length > 0 && (
              <div className="pt-3 border-t border-[#e3dacc] space-y-2">
                <span className="text-[11px] font-mono uppercase tracking-wider text-[#87867f] font-semibold block">
                  Council Action Items
                </span>
                <ul className="space-y-1.5">
                  {result.actions.map((act, idx) => (
                    <li key={idx} className="text-xs text-[#141413] flex items-start gap-2 bg-[#f0eee6]/60 p-2.5 rounded-lg border border-[#e3dacc]">
                      <ChevronRight className="w-3.5 h-3.5 text-[#c6613f] shrink-0 mt-0.5" />
                      <span>{act}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
