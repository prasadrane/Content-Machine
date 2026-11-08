import React from 'react'
import { Sparkles, FileText, Check, Copy, X } from 'lucide-react'

export default function HumanizedDraftCard({
  humanizedResult,
  onUseInEditor,
  onCopy,
  copied,
  onDismiss,
}) {
  if (!humanizedResult) return null

  return (
    <div className="cm-panel space-y-4 animate-fadeIn">
      <div className="cm-divider flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-2.5 flex-wrap">
          <div className="cm-subpanel flex items-center gap-1.5 font-semibold">
            <Sparkles className="w-3.5 h-3.5" />
            <span>{{ model_rewrite: 'Model wording suggestion', deterministic_cleanup: 'Local text cleanup',
              no_change: 'Wording unchanged' }[humanizedResult.provenance] || 'Wording suggestion'}</span>
          </div>
          <span className="cm-badge">
            {humanizedResult.sentence_count || 0} sentences
          </span>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => onUseInEditor(humanizedResult.humanized_text)}
            className="cm-button cm-button-primary flex items-center gap-1.5"
            title="Use this wording suggestion in the editor"
          >
            <FileText className="w-3.5 h-3.5 text-[#d97757]" />
            <span>Use in Editor</span>
          </button>

          <button
            type="button"
            onClick={() => onCopy(humanizedResult.humanized_text)}
            className="cm-button cm-button-secondary flex items-center gap-1.5"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5 text-[#87867f]" />}
            <span>{copied ? 'Copied!' : 'Copy'}</span>
          </button>

          <button
            type="button"
            onClick={onDismiss}
            className="cm-icon-button"
            title="Dismiss"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Purged Clichés Chips */}
      {humanizedResult.banned_words_purged && humanizedResult.banned_words_purged.length > 0 && (
        <div className="flex items-center gap-2 flex-wrap text-sm">
          <span className="cm-muted font-semibold">
            Local wording changes ({humanizedResult.banned_words_purged.length}):
          </span>
          {humanizedResult.banned_words_purged.map((word, idx) => (
            <span
              key={idx}
              className="cm-badge cm-status-error line-through"
            >
              {word}
            </span>
          ))}
        </div>
      )}

      {/* Humanized Text Box */}
      <div className="cm-subpanel whitespace-pre-wrap">
        {humanizedResult.humanized_text}
      </div>
    </div>
  )
}
