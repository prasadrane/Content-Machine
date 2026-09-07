import React from 'react'
import { History, RotateCw, Copy, Check, ChevronUp, ChevronDown } from 'lucide-react'

function getAnglePill(angleKey) {
  switch (angleKey) {
    case 'insightful':
      return '💡 Nuanced Insight'
    case 'contrarian':
      return '⚖️ Respectful Contrarian'
    case 'question':
      return '❓ Senior Question'
    default:
      return angleKey
  }
}

function countSentences(text) {
  if (!text || !text.trim()) return 0
  const matches = text.trim().match(/[^.!?]+[.!?]+(\s|$)/g)
  if (matches) return matches.length
  return text.trim().length > 0 ? 1 : 0
}

export default function CommentsHistory({
  history,
  historyLoading,
  showHistory,
  copiedId,
  onRefresh,
  onToggleShow,
  onLoadFromHistory,
  onCopyHistory,
}) {
  return (
    <div className="bg-[#f0eee6]/60 border border-[#e3dacc] rounded-2xl p-6 sm:p-7 space-y-4 shadow-anthropic">
      <div className="flex items-center justify-between pb-3 border-b border-[#e3dacc]">
        <div className="flex items-center gap-2">
          <History className="w-4 h-4 text-[#87867f]" />
          <h3 className="text-xs uppercase font-mono tracking-wider text-[#87867f] font-semibold">
            Recent Comments History ({history ? history.length : 0})
          </h3>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={onRefresh}
            disabled={historyLoading}
            className="text-xs text-[#87867f] hover:text-[#141413] font-mono flex items-center gap-1 transition"
            title="Refresh history"
          >
            <RotateCw className={`w-3 h-3 ${historyLoading ? 'animate-spin' : ''}`} />
            <span>refresh</span>
          </button>
          <button
            type="button"
            onClick={onToggleShow}
            className="text-xs text-[#87867f] hover:text-[#141413] p-1 rounded-full"
          >
            {showHistory ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {showHistory && (
        <div className="space-y-3 max-h-[600px] overflow-y-auto pr-1">
          {historyLoading && (!history || history.length === 0) ? (
            <div className="p-8 text-center text-[#87867f] text-xs font-mono">
              <RotateCw className="w-4 h-4 animate-spin inline-block text-[#c6613f] mb-2" />
              <p>Loading recent comments...</p>
            </div>
          ) : !history || history.length === 0 ? (
            <div className="border border-dashed border-[#b0aea5] rounded-xl p-8 text-center text-[#87867f] bg-[#faf9f5]">
              <p className="text-xs">No comments generated yet. Generated comments will be saved here.</p>
            </div>
          ) : (
            history.map((item) => {
              const isItemCopied = copiedId === item.id
              return (
                <div
                  key={item.id}
                  className="bg-[#faf9f5] border border-[#e3dacc] rounded-xl p-4 space-y-3 shadow-anthropic transition hover:border-[#b0aea5]"
                >
                  <div className="flex items-center justify-between gap-2 flex-wrap">
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-[#f0eee6] text-[#141413] border border-[#e3dacc]">
                        {getAnglePill(item.angle)}
                      </span>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200">
                        {typeof item.peak_score === 'number' ? item.peak_score.toFixed(1) : item.peak_score} / 10 • {item.verdict}
                      </span>
                      {item.humanized && (
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-[#c6613f]/10 text-[#c6613f] border border-[#c6613f]/30 font-semibold">
                          Humanized ✨
                        </span>
                      )}
                      <span className="text-[10px] font-mono text-[#87867f]">
                        Iter {item.iteration_count}
                      </span>
                    </div>

                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-mono text-[#87867f]">
                        {new Date(item.created_at).toLocaleString([], {
                          month: 'short',
                          day: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </span>
                      <button
                        type="button"
                        onClick={() => onCopyHistory(item.final_comment, item.id)}
                        className="p-1 text-[#87867f] hover:text-[#141413] transition"
                        title="Copy final comment"
                      >
                        {isItemCopied ? (
                          <Check className="w-3.5 h-3.5 text-emerald-600" />
                        ) : (
                          <Copy className="w-3.5 h-3.5" />
                        )}
                      </button>
                      <button
                        type="button"
                        onClick={() => onLoadFromHistory(item)}
                        className="text-[11px] font-mono text-[#c6613f] hover:underline"
                      >
                        Use in Editor
                      </button>
                    </div>
                  </div>

                  <div className="text-xs font-serif text-[#141413] leading-relaxed">
                    {item.final_comment}
                  </div>

                  <div className="pt-2 border-t border-[#e3dacc]/60 flex items-center justify-between text-[10px] font-mono text-[#87867f]">
                    <span className="truncate max-w-[70%]">
                      Post: "{(item.post_content || item.post_excerpt || '').slice(0, 100)}..."
                    </span>
                    <span>
                      {countSentences(item.final_comment)} sentences • {item.final_comment ? item.final_comment.length : 0} chars
                    </span>
                  </div>
                </div>
              )
            })
          )}
        </div>
      )}
    </div>
  )
}
