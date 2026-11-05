import React from 'react'

export default function HistoryTimeline({
  show,
  historyData,
  best,
  onLoadDraft,
}) {
  if (!show || !historyData?.history || historyData.history.length === 0) return null

  return (
    <div className="cm-subpanel space-y-3 animate-fadeIn">
      <div className="flex items-center justify-between">
        <span className="cm-muted">Iteration History</span>
        <span className="cm-muted">{historyData.history.length} records</span>
      </div>
      <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
        {historyData.history.map((item) => (
          <div
            key={item.id}
            className="cm-subpanel flex flex-wrap items-center justify-between gap-3"
          >
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-sans font-semibold text-[#141413]">Iter {item.iteration}</span>
              <span className={`cm-badge ${item.score >= 8.0 ? 'cm-status-success' : 'cm-status-warning'}`}>
                {item.score.toFixed(3)}
              </span>
              {item.score === best?.score && (
                <span className="cm-badge">PEAK</span>
              )}
            </div>

            <div className="flex items-center gap-2">
              <span className="cm-muted">
                {new Date(item.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
              {item.draft && (
                <button
                  type="button"
                  onClick={() => onLoadDraft(item.draft)}
                  className="cm-button cm-button-quiet"
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
