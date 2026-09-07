import React from 'react'
import {
  Check,
  ChevronRight,
  X,
  RotateCw,
  CheckCircle2,
  AlertCircle,
  ShieldCheck,
} from 'lucide-react'

export default function ScanProgressHUD({ progress, loading, onDismiss }) {
  if (!progress) return null

  const {
    phase = 'fetching',
    message = '',
    sourcesFetched = 0,
    sourcesTotal = 0,
    cachedSkipped = 0,
    newSignals = 0,
    current = 0,
    total = 0,
    currentItemTitle = '',
    passed = 0,
    elapsedSec = 0,
  } = progress

  const isFetchingDone = ['deduplicating', 'scoring', 'complete'].includes(phase)
  const isFetchingActive = phase === 'fetching'

  const isDedupDone = ['scoring', 'complete'].includes(phase)
  const isDedupActive = phase === 'deduplicating'

  const isScoringDone = phase === 'complete'
  const isScoringActive = phase === 'scoring'

  const isComplete = phase === 'complete'
  const isError = phase === 'error'

  let progressPercent = 0
  if (isComplete) {
    progressPercent = 100
  } else if (isScoringActive) {
    const fraction = total > 0 ? current / total : 0
    progressPercent = Math.min(95, Math.round(35 + fraction * 60))
  } else if (isDedupActive) {
    progressPercent = 30
  } else if (isFetchingActive) {
    const fraction = sourcesTotal > 0 ? sourcesFetched / sourcesTotal : 0
    progressPercent = Math.min(25, Math.round(5 + fraction * 20))
  }

  return (
    <div className="bg-[#faf9f5] border border-[#e3dacc] rounded-2xl p-5 sm:p-6 shadow-anthropic space-y-4 animate-fadeIn">
      {/* 3-Phase Stepper Header */}
      <div className="flex items-center justify-between gap-3 border-b border-[#e3dacc]/70 pb-3.5">
        <div className="flex items-center gap-2 sm:gap-4 overflow-x-auto w-full py-0.5">
          {/* Phase 1: Ingesting */}
          <div className="flex items-center gap-2.5 shrink-0">
            <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-mono font-medium transition ${
              isFetchingDone
                ? 'bg-emerald-100 text-emerald-800 border border-emerald-300/60'
                : isFetchingActive
                ? 'bg-[#c6613f] text-[#faf9f5] shadow-xs font-semibold'
                : 'bg-[#f0eee6] text-[#87867f] border border-[#e3dacc]'
            }`}>
              {isFetchingDone ? <Check className="w-3.5 h-3.5 stroke-[2.5]" /> : '1'}
            </div>
            <div className="flex flex-col">
              <span className={`text-xs ${isFetchingActive ? 'font-semibold text-[#141413]' : 'font-medium text-[#87867f]'}`}>
                Ingesting Sources
              </span>
              <span className="text-[10px] font-mono text-[#87867f]">
                {sourcesFetched}/{sourcesTotal || 1} sources
              </span>
            </div>
          </div>

          <ChevronRight className="w-3.5 h-3.5 text-[#b0aea5] shrink-0" />

          {/* Phase 2: Zero-Token Deduplication */}
          <div className="flex items-center gap-2.5 shrink-0">
            <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-mono font-medium transition ${
              isDedupDone
                ? 'bg-emerald-100 text-emerald-800 border border-emerald-300/60'
                : isDedupActive
                ? 'bg-[#c6613f] text-[#faf9f5] shadow-xs font-semibold'
                : 'bg-[#f0eee6] text-[#87867f] border border-[#e3dacc]'
            }`}>
              {isDedupDone ? <Check className="w-3.5 h-3.5 stroke-[2.5]" /> : '2'}
            </div>
            <div className="flex flex-col">
              <span className={`text-xs ${isDedupActive ? 'font-semibold text-[#141413]' : 'font-medium text-[#87867f]'}`}>
                Zero-Token Dedup
              </span>
              <span className="text-[10px] font-mono text-[#87867f]">
                {cachedSkipped} cached skipped
              </span>
            </div>
          </div>

          <ChevronRight className="w-3.5 h-3.5 text-[#b0aea5] shrink-0" />

          {/* Phase 3: Scoring & Ranking */}
          <div className="flex items-center gap-2.5 shrink-0">
            <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-mono font-medium transition ${
              isScoringDone
                ? 'bg-emerald-100 text-emerald-800 border border-emerald-300/60'
                : isScoringActive
                ? 'bg-[#c6613f] text-[#faf9f5] shadow-xs font-semibold'
                : 'bg-[#f0eee6] text-[#87867f] border border-[#e3dacc]'
            }`}>
              {isScoringDone ? <Check className="w-3.5 h-3.5 stroke-[2.5]" /> : '3'}
            </div>
            <div className="flex flex-col">
              <span className={`text-xs ${isScoringActive ? 'font-semibold text-[#141413]' : 'font-medium text-[#87867f]'}`}>
                Scoring &amp; Ranking
              </span>
              <span className="text-[10px] font-mono text-[#87867f]">
                {current}/{total || '-'} signals
              </span>
            </div>
          </div>
        </div>

        {/* Dismiss Button */}
        {(isComplete || isError) && (
          <button
            type="button"
            onClick={onDismiss}
            className="p-1 rounded-full text-[#87867f] hover:text-[#141413] hover:bg-[#e3dacc]/50 transition shrink-0"
            title="Dismiss HUD"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Live Message Badge & Metric Pills */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-0.5">
        {/* Live Message Badge */}
        <div className="flex items-center gap-2.5 min-w-0 flex-1">
          {loading ? (
            <RotateCw className="w-4 h-4 animate-spin text-[#c6613f] shrink-0" />
          ) : isComplete ? (
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
          ) : (
            <AlertCircle className="w-4 h-4 text-rose-500 shrink-0" />
          )}
          <span className="text-xs font-mono text-[#141413] truncate font-medium">
            {message || (loading ? 'Processing scan pipeline...' : 'Scan idle.')}
          </span>
        </div>

        {/* Live Metrics */}
        <div className="flex items-center gap-2 flex-wrap shrink-0">
          <span className="inline-flex items-center gap-1.5 text-[11px] font-mono px-3 py-1 rounded-full bg-emerald-50 text-emerald-900 border border-emerald-200/80 font-medium">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
            <span>Zero-Token: <strong>{cachedSkipped}</strong> cached</span>
          </span>

          <span className="text-[11px] font-mono px-3 py-1 rounded-full bg-[#f0eee6] text-[#141413] border border-[#e3dacc] font-medium">
            Scored: <strong>{current}</strong>/{total}
          </span>

          <span className="text-[11px] font-mono px-3 py-1 rounded-full bg-[#c6613f]/10 text-[#c6613f] border border-[#c6613f]/30 font-medium">
            Passed: <strong>{passed}</strong>
          </span>

          {isComplete && elapsedSec > 0 && (
            <span className="text-[11px] font-mono px-3 py-1 rounded-full bg-[#f0eee6] text-[#87867f] border border-[#e3dacc]">
              {elapsedSec}s
            </span>
          )}
        </div>
      </div>

      {/* Progress Bar for Item Scoring */}
      <div className="bg-[#f0eee6]/50 border border-[#e3dacc] rounded-xl p-3.5 space-y-2">
        <div className="flex items-center justify-between text-xs font-mono text-[#87867f]">
          <span className="truncate max-w-[80%]">
            {isScoringActive 
              ? (currentItemTitle ? `Evaluating: "${currentItemTitle}"` : 'Evaluating signals consensus...')
              : isComplete 
              ? 'Scan pipeline completed & cached' 
              : isDedupActive 
              ? 'Deduplicating signals with SQLite (0 tokens)' 
              : 'Pulling items from registered sources...'}
          </span>
          <span className="font-semibold text-[#141413]">{progressPercent}%</span>
        </div>
        <div className="w-full h-2 bg-[#e3dacc]/60 rounded-full overflow-hidden border border-[#e3dacc]/50">
          <div
            className={`h-full transition-all duration-300 rounded-full ${
              isComplete ? 'bg-emerald-600' : 'bg-[#c6613f]'
            }`}
            style={{ width: `${progressPercent}%` }}
          />
        </div>
      </div>
    </div>
  )
}
