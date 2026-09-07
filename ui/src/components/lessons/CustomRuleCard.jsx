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
    <form onSubmit={onAdd} className="space-y-3 bg-[#f0eee6]/60 p-5 rounded-2xl border border-[#e3dacc] shadow-anthropic">
      <div className="flex items-center justify-between">
        <h3 className="text-xs uppercase font-mono tracking-wider text-[#87867f]">Add Custom Writing Rule</h3>
        <span className="text-[10px] font-mono text-[#c6613f] bg-[#c6613f]/10 px-2 py-0.5 rounded-full border border-[#c6613f]/20">
          Instant Governance
        </span>
      </div>
      <div>
        <label className="block text-[11px] font-mono text-[#87867f] mb-1">Declarative Rule (Injected directly into Council drafter)</label>
        <textarea
          rows={2}
          value={customRuleText}
          onChange={(e) => onTextChange(e.target.value)}
          placeholder="e.g. Never open with buzzwords or greetings. Start immediately on what failed in production."
          className="w-full text-xs font-mono bg-[#faf9f5] border border-[#e3dacc] rounded-xl p-3 text-[#141413] focus:outline-none focus:border-[#141413] placeholder-[#b0aea5]"
        />
      </div>
      {customSuccess && (
        <div className="p-2.5 bg-emerald-50 text-emerald-800 text-xs rounded-xl border border-emerald-200 flex items-center gap-1.5">
          <CheckCircle2 className="w-3.5 h-3.5 shrink-0 text-emerald-600" />
          <span>{customSuccess}</span>
        </div>
      )}
      <button
        type="submit"
        disabled={loadingCustom || !customRuleText.trim()}
        className="w-full py-2.5 px-4 bg-[#141413] hover:bg-[#252524] disabled:opacity-50 text-[#faf9f5] rounded-full text-xs font-medium transition flex items-center justify-center gap-2 shadow-sm"
      >
        {loadingCustom ? <RotateCw className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5 text-[#d97757]" />}
        <span>{loadingCustom ? 'Saving & Activating...' : 'Save & Activate Rule'}</span>
      </button>
    </form>
  )
}
