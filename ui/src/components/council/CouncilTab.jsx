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
    <div className="cm-page">
      {/* Editorial Title */}
      <div className="cm-page-header">
        <div>
          <h2 className="cm-page-title">Writer's Council</h2>
          <p className="cm-page-description">
            Review and improve your draft. Editorial scores do not verify factual claims.
          </p>
        </div>
      </div>

      {/* Historical Peak Banner */}
      {best && (
        <div className="cm-panel flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-start gap-3.5">
            <div className="cm-subpanel shrink-0 mt-0.5">
              <Trophy className="w-5 h-5" />
            </div>
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <span className="cm-panel-title">Highest-scoring reviewed version</span>
                <span className="cm-badge">
                  Iteration {best.iteration}
                </span>
                {best.score >= 8.0 && (
                  <span className="cm-badge cm-status-success">
                    PASS
                  </span>
                )}
              </div>
              <div className="text-2xl font-serif font-semibold text-[#141413] mt-0.5">
                {best.score.toFixed(3)}
                <span className="cm-muted ml-2">/ 10.0</span>
              </div>
              <p className="cm-muted mt-0.5">
                Highest scoring version recorded for <span className="font-sans text-[#141413] font-medium">{spikeId}</span>.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2.5 shrink-0 flex-wrap">
            {best.draft && (
              <button
                type="button"
                onClick={() => compareReplacement(best.draft)}
                className="cm-button cm-button-secondary flex items-center gap-1.5"
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
                className="cm-button cm-button-secondary flex items-center gap-1.5"
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
                className="cm-button cm-button-primary flex items-center gap-1.5"
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
        <p role="status" className="cm-status cm-status-warning">Polished wording belongs to an earlier version of {humanizedResult.reviewInput.slug}. Your current draft has not been replaced.</p>
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
        <div className="cm-status cm-status-error flex items-center gap-2 animate-fadeIn">
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
          <div className="cm-divider flex items-center justify-between">
            <h3 className="cm-panel-title">Editorial Verdict</h3>
            <div className="flex items-center gap-3">
              {result && (
                <span className="cm-muted">Iteration {result.iteration}</span>
              )}
              {historyData?.history?.length > 0 && (
                <button
                  type="button"
                  onClick={() => setShowHistory(!showHistory)}
                  className="cm-button cm-button-quiet flex items-center gap-1"
                >
                  <History className="w-3 h-3" />
                  <span>{showHistory ? 'Hide History' : `History (${historyData.history.length})`}</span>
                </button>
              )}
            </div>
          </div>

          {!result && !loading && (
            <div className="cm-empty text-center">
              <Users className="w-8 h-8 mx-auto mb-3 stroke-1 text-[#b0aea5]" />
              <p className="cm-prose font-medium">No active evaluation.</p>
              <p className="cm-muted mt-1">Submit your draft or load a historical peak iteration to view the multi-judge evaluation.</p>
            </div>
          )}

          {loading && (
            <div className="cm-subpanel text-center space-y-3">
              <RotateCw className="w-6 h-6 mx-auto animate-spin text-[#c6613f]" />
              <p role="status" className="cm-prose font-medium">Reviewing the submitted draft...</p>
              <p className="cm-muted">You can keep editing. The review will remain linked to the submitted version.</p>
            </div>
          )}

          {resultIsEarlier && (
            <div role="status" className="cm-status cm-status-warning">
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
