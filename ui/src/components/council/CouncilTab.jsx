import React, { useEffect, useState } from 'react'
import { Trophy, RotateCw, Sparkles, Share2, AlertCircle, Users, History } from 'lucide-react'
import { useCouncilSession } from './useCouncilSession'
import { useCopyToClipboard } from '../../hooks/useCopyToClipboard'
import HumanizedDraftCard from './HumanizedDraftCard'
import DraftingStudio from './DraftingStudio'
import VerdictPanel from './VerdictPanel'
import HistoryTimeline from './HistoryTimeline'
import ApprovalGate from '../approval/ApprovalGate'
import RevisionComparison from './RevisionComparison'

export default function CouncilTab({ draft, setDraft, spikeId, setSpikeId, onApprove, councilIdentity }) {
  const {
    loading, result, error, historyData, recentSpikes, showHistory, setShowHistory,
    humanizing, humanizedResult, setHumanizedResult, humanizeError, maxIterations, setMaxIterations,
    pendingApproval, setPendingApproval, requestApproval, confirmApproval, best,
    handleReview, handleHumanize, handleSelectSpike, handleLoadDraft, resultIsEarlier, polishIsEarlier,
  } = useCouncilSession({ draft, setDraft, spikeId, setSpikeId, onApprove, councilIdentity })
  const { copied: humanizeCopied, copy: copyHumanized } = useCopyToClipboard()
  const [replacement, setReplacement] = useState(null)
  const compareReplacement = text => {
    if (text && text !== draft) setReplacement({ text, base: draft, slug: spikeId })
  }
  useEffect(() => { setReplacement(null) }, [draft, spikeId, councilIdentity?.itemId, councilIdentity?.version])
  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Editorial Title */}
      <div>
        <h2 className="font-serif text-2xl font-medium tracking-tight text-[#141413]">Writer's Council</h2>
        <p className="text-sm text-[#87867f] mt-1 font-sans">
          Review and improve your draft. Editorial scores do not verify factual claims.
        </p>
      </div>

      {/* Historical Peak Banner */}
      {best && (
        <div className="p-5 bg-[#f0eee6] border border-[#e3dacc] rounded-2xl flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-anthropic">
          <div className="flex items-start gap-3.5">
            <div className="p-2.5 bg-[#c6613f]/10 text-[#c6613f] rounded-xl shrink-0 mt-0.5 border border-[#c6613f]/20">
              <Trophy className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono font-bold uppercase tracking-wider text-[#c6613f]">Highest-scoring reviewed version</span>
                <span className="text-[10px] font-mono px-2.5 py-0.5 rounded-full bg-[#faf9f5] text-[#141413] border border-[#e3dacc]">
                  Iteration {best.iteration}
                </span>
                {best.score >= 8.0 && (
                  <span className="text-[10px] font-mono px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-300">
                    PASS
                  </span>
                )}
              </div>
              <div className="text-2xl font-serif font-semibold text-[#141413] mt-0.5">
                {best.score.toFixed(3)}
                <span className="text-xs font-normal text-[#87867f] ml-2 font-mono">/ 10.0</span>
              </div>
              <p className="text-xs text-[#87867f] mt-0.5">
                Highest scoring version recorded for <span className="font-mono text-[#141413] font-medium">{spikeId}</span>.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2.5 shrink-0 flex-wrap">
            {best.draft && (
              <button
                type="button"
                onClick={() => compareReplacement(best.draft)}
                className="px-4 py-2 bg-[#faf9f5] hover:bg-[#e3dacc]/50 text-[#141413] rounded-full text-xs font-medium transition flex items-center gap-1.5 border border-[#e3dacc] shadow-sm"
              >
                <RotateCw className="w-3.5 h-3.5 text-[#87867f]" />
                <span>Load Peak Draft</span>
              </button>
            )}
            {best.draft && (
              <button
                type="button"
                onClick={() => handleHumanize(best.draft)}
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
            {best.draft && onApprove && (
              <button
                type="button"
                onClick={() => requestApproval(best.draft, { verdict: best.threshold_met ? 'pass' : best.verdict || 'revise', score: best.score })}
                className="px-4 py-2 bg-[#c6613f] hover:bg-[#b55535] text-[#faf9f5] rounded-full text-xs font-medium transition flex items-center gap-1.5 shadow-sm"
              >
                <Share2 className="w-3.5 h-3.5" />
                <span>Approve Peak Post</span>
              </button>
            )}
          </div>
        </div>
      )}

      {pendingApproval && onApprove && (
        <ApprovalGate
          text={pendingApproval.text}
          verdict={pendingApproval.verdict}
          score={pendingApproval.score}
          onCancel={() => setPendingApproval(null)}
          onConfirm={confirmApproval}
        />
      )}

      {polishIsEarlier && (
        <p role="status" className="text-sm text-amber-900">Polished wording belongs to an earlier version of {humanizedResult.reviewInput.slug}. Your current draft has not been replaced.</p>
      )}
      {/* Humanized Peak Draft Card */}
      <HumanizedDraftCard
        humanizedResult={humanizedResult}
        onUseInEditor={compareReplacement}
        onCopy={copyHumanized}
        copied={humanizeCopied}
        onDismiss={() => setHumanizedResult(null)}
      />

      {replacement && <RevisionComparison
        currentText={draft}
        proposedText={replacement.text}
        onCancel={() => setReplacement(null)}
        onAccept={() => {
          if (replacement.base === draft && replacement.slug === spikeId) handleLoadDraft(replacement.text)
          setReplacement(null)
        }}
      />}

      {humanizeError && (
        <div className="p-3.5 bg-rose-50 border border-rose-200 rounded-xl text-rose-800 text-xs flex items-center gap-2 animate-fadeIn">
          <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
          <span>{humanizeError}</span>
        </div>
      )}

      {/* Signature High-Contrast Dual Panel Layout */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-start">
        <DraftingStudio
          draft={draft}
          onDraftChange={setDraft}
          spikeId={spikeId}
          onSpikeChange={setSpikeId}
          recentSpikes={recentSpikes}
          onSelectSpike={handleSelectSpike}
          maxIterations={maxIterations}
          onMaxIterationsChange={setMaxIterations}
          loading={loading}
          error={error}
          onSubmit={handleReview}
        />

        <div className="space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-[#e3dacc]">
            <h3 className="text-xs uppercase font-mono tracking-wider text-[#87867f]">Editorial Verdict</h3>
            <div className="flex items-center gap-3">
              {result && (
                <span className="text-[11px] font-mono text-[#87867f]">Iteration {result.iteration}</span>
              )}
              {historyData?.history?.length > 0 && (
                <button
                  type="button"
                  onClick={() => setShowHistory(!showHistory)}
                  className="text-[11px] font-mono text-[#87867f] hover:text-[#141413] flex items-center gap-1 transition"
                >
                  <History className="w-3 h-3" />
                  <span>{showHistory ? 'Hide History' : `History (${historyData.history.length})`}</span>
                </button>
              )}
            </div>
          </div>

          {!result && !loading && (
            <div className="border border-dashed border-[#b0aea5] rounded-2xl p-12 text-center text-[#87867f] bg-[#f0eee6]/30">
              <Users className="w-8 h-8 mx-auto mb-3 stroke-1 text-[#b0aea5]" />
              <p className="text-sm font-medium text-[#141413]">No active evaluation.</p>
              <p className="text-xs text-[#87867f] mt-1">Submit your draft or load a historical peak iteration to view the multi-judge evaluation.</p>
            </div>
          )}

          {loading && (
            <div className="border border-[#e3dacc] rounded-2xl p-12 text-center text-[#87867f] space-y-3 bg-[#f0eee6]/50 shadow-anthropic">
              <RotateCw className="w-6 h-6 mx-auto animate-spin text-[#c6613f]" />
              <p role="status" className="text-sm font-medium text-[#141413]">Reviewing the submitted draft...</p>
              <p className="text-xs text-[#87867f]">You can keep editing. The review will remain linked to the submitted version.</p>
            </div>
          )}

          {resultIsEarlier && (
            <div role="status" className="p-3 bg-amber-50 text-amber-900 rounded-xl text-sm">
              Review of an earlier version of {result.reviewInput.slug}. Your current draft has not been replaced.
            </div>
          )}
          <VerdictPanel
            result={result}
            reviewIsEarlier={resultIsEarlier}
            best={best}
            draft={draft}
            spikeId={spikeId}
            humanizing={humanizing}
            onLoadDraft={handleLoadDraft}
            onHumanize={handleHumanize}
            onRequestApproval={onApprove ? requestApproval : undefined}
          />

          <HistoryTimeline
            show={showHistory}
            historyData={historyData}
            best={best}
            onLoadDraft={compareReplacement}
          />
        </div>
      </div>
    </div>
  )
}
