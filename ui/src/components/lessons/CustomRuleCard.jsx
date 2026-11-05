import React from 'react'
import { CheckCircle2, RotateCw, Sparkles } from 'lucide-react'

export default function CustomRuleCard({
  customRuleText,
  onTextChange,
  loadingCustom,
  customSuccess,
  onAdd,
}) {
  return (
    <form onSubmit={onAdd} className="cm-panel space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h3 className="cm-panel-title">Add Custom Writing Rule</h3>
        <span className="cm-badge">
          Instant Governance
        </span>
      </div>
      <div>
        <label htmlFor="custom-writing-rule" className="cm-label">Declarative Rule (Injected directly into Council drafter)</label>
        <textarea
          id="custom-writing-rule"
          rows={2}
          value={customRuleText}
          onChange={(e) => onTextChange(e.target.value)}
          placeholder="e.g. Never open with buzzwords or greetings. Start immediately on what failed in production."
          className="cm-textarea"
        />
      </div>
      {customSuccess && (
        <div className="cm-status cm-status-success flex items-center gap-2">
          <CheckCircle2 className="w-3.5 h-3.5 shrink-0 text-emerald-600" />
          <span>{customSuccess}</span>
        </div>
      )}
      <button
        type="submit"
        disabled={loadingCustom || !customRuleText.trim()}
        className="cm-button cm-button-primary w-full"
      >
        {loadingCustom ? <RotateCw className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5 text-[#d97757]" />}
        <span>{loadingCustom ? 'Saving & Activating...' : 'Save & Activate Rule'}</span>
      </button>
    </form>
  )
}
