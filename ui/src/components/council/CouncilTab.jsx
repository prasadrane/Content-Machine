import React, { useState, useEffect } from 'react'
import { Trophy, RotateCw, Sparkles, Share2, AlertCircle, Users, History } from 'lucide-react'
import { runCouncil, getCouncilHistory, getCouncilSpikes } from '../../api/council'
import { runHumanize } from '../../api/humanize'
import { useCopyToClipboard } from '../../hooks/useCopyToClipboard'
import HumanizedDraftCard from './HumanizedDraftCard'
import DraftingStudio from './DraftingStudio'
import VerdictPanel from './VerdictPanel'
import HistoryTimeline from './HistoryTimeline'

export default function CouncilTab({ draft, setDraft, spikeId, setSpikeId, onSendToDistribute }) {
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [historyData, setHistoryData] = useState(null)
  const [recentSpikes, setRecentSpikes] = useState([])
  const [showHistory, setShowHistory] = useState(false)
  const [humanizing, setHumanizing] = useState(false)
  const [humanizedResult, setHumanizedResult] = useState(null)
  const { copied: humanizeCopied, copy: copyHumanized } = useCopyToClipboard()
  const [humanizeError, setHumanizeError] = useState('')

  const fetchHistory = async (slug) => {
    if (!slug) return
    try {
      const data = await getCouncilHistory(slug)
      setHistoryData(data)
    } catch {
      // ignore
    }
  }

  const fetchSpikes = async () => {
    try {
      const data = await getCouncilSpikes()
      setRecentSpikes(data || [])
    } catch {
      // ignore
    }
  }

  useEffect(() => {
    fetchSpikes()
  }, [])

  useEffect(() => {
    if (spikeId) {
      fetchHistory(spikeId)
    }
  }, [spikeId])

  const handleReview = async (e) => {
    e.preventDefault()
    if (!draft.trim()) {
      setError('Draft text cannot be empty.')
      return
    }
    setLoading(true)
    setError('')
    setResult(null)

    try {
      const targetSlug = spikeId || 'council-ui'
      const data = await runCouncil({ draft, spike_id: targetSlug })
      setResult(data)
      fetchHistory(targetSlug)
      fetchSpikes()
    } catch (err) {
      setError(err.message || 'Council run failed.')
    } finally {
      setLoading(false)
    }
  }

  const handleSelectSpike = (slug) => {
    setSpikeId(slug)
    fetchHistory(slug)
  }

  const handleLoadDraft = (text) => {
    if (text) {
      setDraft(text)
    }
  }

  const best = historyData?.best

  const handleHumanize = async (sourceText) => {
    const textToHumanize = sourceText || best?.draft || draft
    if (!textToHumanize || !textToHumanize.trim()) {
      setHumanizeError('No draft text available to humanize.')
      return
    }

    setHumanizing(true)
    setHumanizeError('')
    try {
      const data = await runHumanize({
        text: textToHumanize,
        channel: 'linkedin_post',
        tone: 'pragmatic_architect',
      })
      setHumanizedResult(data)
    } catch (err) {
      setHumanizeError(err.message || 'Failed to humanize draft.')
    } finally {
      setHumanizing(false)
    }
  }

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Editorial Title */}
      <div>
        <h2 className="font-serif text-2xl font-medium tracking-tight text-[#141413]">Writer's Council</h2>
        <p className="text-sm text-[#87867f] mt-1 font-sans">
          Multi-judge editorial review and iterative revision.
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
                <span className="text-xs font-mono font-bold uppercase tracking-wider text-[#c6613f]">All-Time Peak Iteration</span>
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
                onClick={() => handleLoadDraft(best.draft)}
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
            {best.draft && onSendToDistribute && (
              <button
                type="button"
                onClick={() => onSendToDistribute(best.draft, spikeId)}
                className="px-4 py-2 bg-[#c6613f] hover:bg-[#b55535] text-[#faf9f5] rounded-full text-xs font-medium transition flex items-center gap-1.5 shadow-sm"
              >
                <Share2 className="w-3.5 h-3.5" />
                <span>Distribute Peak Post</span>
              </button>
            )}
          </div>
        </div>
      )}

      {/* Humanized Peak Draft Card */}
      <HumanizedDraftCard
        humanizedResult={humanizedResult}
        onUseInEditor={setDraft}
        onCopy={copyHumanized}
        copied={humanizeCopied}
        onDismiss={() => setHumanizedResult(null)}
      />

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
              <p className="text-sm font-medium text-[#141413]">Obfuscating authorship & gathering parallel verdicts...</p>
              <p className="text-xs text-[#87867f] font-mono">Running z-score normalization against rolling history</p>
            </div>
          )}

          <VerdictPanel
            result={result}
            best={best}
            draft={draft}
            spikeId={spikeId}
            humanizing={humanizing}
            onLoadDraft={handleLoadDraft}
            onHumanize={handleHumanize}
            onSendToDistribute={onSendToDistribute}
          />

          <HistoryTimeline
            show={showHistory}
            historyData={historyData}
            best={best}
            onLoadDraft={handleLoadDraft}
          />
        </div>
      </div>
    </div>
  )
}
