import React from 'react'
import { RotateCw, BookOpen } from 'lucide-react'
import ProposalsQueue from './ProposalsQueue'

export default function DiffExtractor({
  draftText,
  pubText,
  onDraftChange,
  onPubChange,
  loadingDiff,
  error,
  onDiff,
  proposals,
  onApproveProposal,
  onRejectProposal,
}) {
  return (
    <div className="space-y-4 bg-[#f0eee6]/60 p-5 rounded-2xl border border-[#e3dacc] shadow-anthropic">
      <h3 className="text-xs uppercase font-mono tracking-wider text-[#87867f]">Diff Extractor (Draft vs Published)</h3>

      <div className="space-y-3">
        <div>
          <label className="block text-[11px] font-mono text-[#87867f] mb-1">Original Draft (AI generated)</label>
          <textarea
            rows={5}
            value={draftText}
            onChange={(e) => onDraftChange(e.target.value)}
            placeholder="Paste AI generated draft..."
            className="w-full text-xs font-mono bg-[#faf9f5] border border-[#e3dacc] rounded-xl p-3 text-[#141413] focus:outline-none focus:border-[#141413] placeholder-[#b0aea5]"
          />
        </div>

        <div>
          <label className="block text-[11px] font-mono text-[#87867f] mb-1">Published Text (Operator final edit)</label>
          <textarea
            rows={5}
            value={pubText}
            onChange={(e) => onPubChange(e.target.value)}
            placeholder="Paste published final version..."
            className="w-full text-xs font-mono bg-[#faf9f5] border border-[#e3dacc] rounded-xl p-3 text-[#141413] focus:outline-none focus:border-[#141413] placeholder-[#b0aea5]"
          />
        </div>

        {error && (
          <div className="p-2.5 bg-rose-50 text-rose-800 text-xs rounded-xl border border-rose-200">{error}</div>
        )}

        <button
          type="button"
          onClick={onDiff}
          disabled={loadingDiff}
          className="w-full py-2.5 px-4 bg-[#141413] hover:bg-[#252524] disabled:opacity-50 text-[#faf9f5] rounded-full text-xs font-medium transition flex items-center justify-center gap-2 shadow-sm"
        >
          {loadingDiff ? <RotateCw className="w-3.5 h-3.5 animate-spin" /> : <BookOpen className="w-3.5 h-3.5 text-[#d97757]" />}
          <span>{loadingDiff ? 'Analyzing Diff Patterns...' : 'Extract Declarative Rules'}</span>
        </button>
      </div>

      <ProposalsQueue
        proposals={proposals}
        onApprove={onApproveProposal}
        onReject={onRejectProposal}
      />
    </div>
  )
}
