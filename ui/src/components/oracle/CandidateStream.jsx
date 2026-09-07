import React, { useState } from 'react'
import { Compass, Sparkles, Search } from 'lucide-react'
import ScanProgressHUD from './ScanProgressHUD'
import TriageToolbar from './TriageToolbar'
import CandidateCard from './CandidateCard'

export default function CandidateStream({
  candidates,
  loading,
  scanProgress,
  onDismissScanProgress,
  onSendToCouncil,
  onOpenInterview,
  onDismissCandidate,
}) {
  const [batchSearch, setBatchSearch] = useState('')
  const [batchSort, setBatchSort] = useState('score') // 'score' | 'recency'
  const [batchTopic, setBatchTopic] = useState('All')

  // Derive unique active batch topics from current candidates
  const batchTopics = ['All', ...Array.from(new Set(candidates.map(c => c.topic_tag).filter(Boolean)))]

  // Live filter and sort candidates in the active batch
  const filteredCandidates = candidates.filter((item) => {
    if (batchTopic !== 'All' && item.topic_tag !== batchTopic) {
      return false
    }
    if (batchSearch.trim()) {
      const q = batchSearch.trim().toLowerCase()
      const inTitle = (item.title || '').toLowerCase().includes(q)
      const inSource = (item.source || '').toLowerCase().includes(q)
      const inSnippet = (item.body_snippet || '').toLowerCase().includes(q)
      const inTopic = (item.topic_tag || '').toLowerCase().includes(q)
      if (!inTitle && !inSource && !inSnippet && !inTopic) return false
    }
    return true
  }).sort((a, b) => {
    if (batchSort === 'score') {
      const scoreA = typeof a.score === 'number' ? a.score : 0
      const scoreB = typeof b.score === 'number' ? b.score : 0
      return scoreB - scoreA
    } else if (batchSort === 'recency') {
      const dateA = a.published_at ? new Date(a.published_at).getTime() : 0
      const dateB = b.published_at ? new Date(b.published_at).getTime() : 0
      return dateB - dateA
    }
    return 0
  })

  return (
    <div className="md:col-span-2 space-y-4">
      <div className="flex items-center justify-between pb-2 border-b border-[#e3dacc]">
        <h3 className="text-xs uppercase font-mono tracking-wider text-[#87867f]">
          Scored Candidates {candidates.length > 0 && filteredCandidates.length !== candidates.length 
            ? `(${filteredCandidates.length} of ${candidates.length})` 
            : `(${candidates.length})`}
        </h3>
        <span className="text-[11px] text-[#87867f] font-mono">Gate: 8.0 &bull; Margin: &plusmn;0.5</span>
      </div>

      {/* ScanProgressHUD: 3-Phase Stepper, Zero-Token Badge, Scoring Progress */}
      {(loading || scanProgress) && (
        <ScanProgressHUD
          progress={scanProgress}
          loading={loading}
          onDismiss={onDismissScanProgress}
        />
      )}

      {candidates.length === 0 && !loading && !scanProgress && (
        <div className="border border-dashed border-[#b0aea5] rounded-2xl p-12 text-center text-[#87867f] bg-[#f0eee6]/30">
          <Compass className="w-8 h-8 mx-auto mb-3 stroke-1 text-[#b0aea5]" />
          <p className="text-sm font-medium text-[#141413]">No candidates scored in this scan yet.</p>
          <p className="text-xs text-[#87867f] mt-1">Configure sources on the left and trigger a scan, or switch to the Feed Archive tab to browse all past posts.</p>
        </div>
      )}

      {loading && candidates.length === 0 && (
        <div className="border border-dashed border-[#e3dacc] rounded-2xl p-8 text-center text-[#87867f] bg-[#faf9f5]/50 animate-fadeIn">
          <Sparkles className="w-5 h-5 mx-auto mb-2 text-[#d97757] animate-pulse" />
          <p className="text-xs font-serif text-[#141413]">Listening to real-time signal stream...</p>
          <p className="text-[11px] text-[#87867f] mt-0.5">Scored candidates will materialize here dynamically as consensus is reached.</p>
        </div>
      )}

      {!loading && candidates.length === 0 && scanProgress && (
        <div className="border border-dashed border-[#e3dacc] rounded-2xl p-8 text-center text-[#87867f] bg-[#faf9f5]/50 animate-fadeIn">
          <p className="text-xs font-serif text-[#141413]">No signals met the score threshold (≥8.0) in this batch.</p>
          <p className="text-[11px] text-[#87867f] mt-0.5">All items were either deduplicated from SQLite cache or scored below threshold.</p>
        </div>
      )}

      {/* Active Batch Triage Toolbar */}
      {candidates.length > 0 && (
        <TriageToolbar
          batchSearch={batchSearch}
          setBatchSearch={setBatchSearch}
          batchSort={batchSort}
          setBatchSort={setBatchSort}
          batchTopic={batchTopic}
          setBatchTopic={setBatchTopic}
          batchTopics={batchTopics}
          candidates={candidates}
        />
      )}

      {/* Zero Filter Matches State */}
      {candidates.length > 0 && filteredCandidates.length === 0 && (
        <div className="border border-dashed border-[#b0aea5] rounded-2xl p-8 text-center text-[#87867f] bg-[#f0eee6]/30 animate-fadeIn">
          <Search className="w-6 h-6 mx-auto mb-2 text-[#b0aea5]" />
          <p className="text-xs font-medium text-[#141413]">No candidates match the active filters.</p>
          <button
            type="button"
            onClick={() => { setBatchSearch(''); setBatchTopic('All'); }}
            className="text-[11px] text-[#c6613f] hover:underline mt-1.5 inline-block font-mono"
          >
            Reset batch filters &rarr;
          </button>
        </div>
      )}

      {/* Candidates Card Feed */}
      <div className="space-y-3">
        {filteredCandidates.map((item, idx) => (
          <CandidateCard
            key={item.url || item.title || idx}
            candidate={item}
            onSendToCouncil={onSendToCouncil}
            onOpenInterview={onOpenInterview}
            onDismiss={onDismissCandidate}
          />
        ))}
      </div>
    </div>
  )
}
