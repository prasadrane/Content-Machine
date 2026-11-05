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
    <div className="cm-panel space-y-4">
      <h3 className="cm-panel-title">Diff Extractor (Draft vs Published)</h3>

      <div className="space-y-3">
        <div>
          <label htmlFor="lesson-original-draft" className="cm-label">Original Draft (AI generated)</label>
          <textarea
            id="lesson-original-draft"
            rows={5}
            value={draftText}
            onChange={(e) => onDraftChange(e.target.value)}
            placeholder="Paste AI generated draft..."
            className="cm-textarea"
          />
        </div>

        <div>
          <label htmlFor="lesson-published-text" className="cm-label">Published Text (Operator final edit)</label>
          <textarea
            id="lesson-published-text"
            rows={5}
            value={pubText}
            onChange={(e) => onPubChange(e.target.value)}
            placeholder="Paste published final version..."
            className="cm-textarea"
          />
        </div>

        {error && (
          <div className="cm-status cm-status-error">{error}</div>
        )}

        <button
          type="button"
          onClick={onDiff}
          disabled={loadingDiff}
          className="cm-button cm-button-primary w-full"
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
