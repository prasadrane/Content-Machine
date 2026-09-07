import React from 'react'

export default function HistoryTimeline({
  show,
  historyData,
  best,
  onLoadDraft,
}) {
  if (!show || !historyData?.history || historyData.history.length === 0) return null

  return (
    <div className="bg-[#f0eee6]/60 border border-[#e3dacc] rounded-2xl p-4 space-y-3 animate-fadeIn shadow-anthropic">
      <div className="flex items-center justify-between">
        <span className="text-xs font-mono uppercase tracking-wider text-[#87867f]">Iteration History</span>
        <span className="text-[10px] font-mono text-[#87867f]">{historyData.history.length} records</span>
      </div>
      <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
        {historyData.history.map((item) => (
          <div
            key={item.id}
            className="flex items-center justify-between p-2.5 bg-[#faf9f5] border border-[#e3dacc] rounded-xl text-xs"
          >
            <div className="flex items-center gap-2">
              <span className="font-mono font-semibold text-[#141413]">Iter {item.iteration}</span>
              <span className={`px-2 py-0.5 rounded-full text-[10px] font-mono ${
                item.score >= 8.0 ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'
              }`}>
                {item.score.toFixed(3)}
              </span>
              {item.score === best?.score && (
                <span className="text-[9px] font-mono px-2 py-0.5 bg-[#c6613f]/15 text-[#c6613f] rounded-full border border-[#c6613f]/30">PEAK</span>
              )}
            </div>

            <div className="flex items-center gap-2">
              <span className="text-[10px] font-mono text-[#87867f]">
                {new Date(item.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
              {item.draft && (
                <button
                  type="button"
                  onClick={() => onLoadDraft(item.draft)}
                  className="text-[11px] font-mono text-[#c6613f] hover:underline"
                >
                  Load
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
