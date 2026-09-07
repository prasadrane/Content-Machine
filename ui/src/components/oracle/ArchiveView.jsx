import React from 'react'
import { Search, X, RotateCw, Tag, Database, ExternalLink, Sparkles, ArrowRight } from 'lucide-react'
import { getTopicBadgeClass } from '../../lib/topics'

export default function ArchiveView({
  archiveSearch,
  setArchiveSearch,
  archiveVerdict,
  setArchiveVerdict,
  archiveTopic,
  setArchiveTopic,
  availableTopics,
  archiveItems,
  archiveTotal,
  archiveLoading,
  fetchArchive,
  onOpenInterview,
}) {
  return (
    <div className="space-y-6">
      {/* Search & Filter Bar */}
      <div className="bg-[#f0eee6]/60 p-5 rounded-2xl border border-[#e3dacc] space-y-4 shadow-anthropic">
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="w-4 h-4 absolute left-3.5 top-3 text-[#87867f]" />
            <input
              type="text"
              value={archiveSearch}
              onChange={(e) => setArchiveSearch(e.target.value)}
              placeholder="Search past scanned posts by title or source..."
              className="w-full pl-10 pr-8 py-2.5 bg-[#faf9f5] border border-[#e3dacc] rounded-full text-xs text-[#141413] placeholder-[#b0aea5] focus:outline-none focus:border-[#141413]"
            />
            {archiveSearch && (
              <button 
                onClick={() => setArchiveSearch('')}
                className="absolute right-3.5 top-3 text-[#87867f] hover:text-[#141413]"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          {/* Verdict Filter Buttons */}
          <div className="flex items-center gap-1 bg-[#faf9f5] p-1 rounded-full border border-[#e3dacc] overflow-x-auto shadow-sm">
            {[
              { key: 'All', label: 'All' },
              { key: 'pass', label: 'Pass (≥8.0)' },
              { key: 'review', label: 'Review (7.5-8.0)' },
              { key: 'reject', label: 'Rejected' },
            ].map((v) => (
              <button
                key={v.key}
                type="button"
                onClick={() => setArchiveVerdict(v.key)}
                className={`px-3 py-1 rounded-full text-xs font-mono transition shrink-0 ${
                  archiveVerdict === v.key
                    ? 'bg-[#141413] text-[#faf9f5] font-medium shadow-sm'
                    : 'text-[#87867f] hover:text-[#141413]'
                }`}
              >
                {v.label}
              </button>
            ))}
          </div>

          {/* Refresh Archive Button */}
          <button
            type="button"
            onClick={fetchArchive}
            className="px-4 py-2 rounded-full bg-[#faf9f5] border border-[#e3dacc] hover:border-[#b0aea5] text-[#141413] text-xs flex items-center gap-1.5 transition shrink-0 self-start sm:self-auto shadow-sm"
            title="Refresh archive"
          >
            <RotateCw className={`w-3.5 h-3.5 ${archiveLoading ? 'animate-spin text-[#c6613f]' : 'text-[#87867f]'}`} />
            <span>Refresh</span>
          </button>
        </div>

        {/* Topic Taxonomy Pills */}
        <div>
          <div className="flex items-center gap-1.5 mb-2.5 text-xs font-medium text-[#87867f]">
            <Tag className="w-3.5 h-3.5 text-[#c6613f]" />
            <span>Filter by Content Topic Taxonomy:</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {availableTopics.map((topic) => {
              const active = archiveTopic === topic
              return (
                <button
                  key={topic}
                  type="button"
                  onClick={() => setArchiveTopic(topic)}
                  className={`text-xs px-3.5 py-1.5 rounded-full border transition flex items-center gap-1.5 ${
                    active
                      ? 'bg-[#141413] text-[#faf9f5] border-[#141413] shadow-sm font-medium'
                      : 'bg-[#faf9f5] text-[#87867f] border-[#e3dacc] hover:border-[#b0aea5] hover:text-[#141413]'
                  }`}
                >
                  <span>{topic}</span>
                  {topic !== 'All' && (
                    <span className={`text-[10px] px-1.5 py-0.2 rounded-full font-mono ${active ? 'bg-[#252524] text-[#faf9f5]' : 'bg-[#f0eee6] text-[#87867f]'}`}>
                      {archiveItems.filter(i => i.topic_tag === topic).length}
                    </span>
                  )}
                </button>
              )
            })}
          </div>
        </div>
      </div>

      {/* Archive Results */}
      {archiveLoading ? (
        <div className="border border-[#e3dacc] rounded-2xl p-12 text-center text-[#87867f] space-y-3 bg-[#f0eee6]/50 shadow-anthropic">
          <RotateCw className="w-6 h-6 mx-auto animate-spin text-[#c6613f]" />
          <p className="text-sm font-medium text-[#141413]">Loading historical feed archive...</p>
        </div>
      ) : archiveItems.length === 0 ? (
        <div className="border border-dashed border-[#b0aea5] rounded-2xl p-12 text-center text-[#87867f] bg-[#f0eee6]/30">
          <Database className="w-8 h-8 mx-auto mb-3 stroke-1 text-[#b0aea5]" />
          <p className="text-sm font-medium text-[#141413]">No historical posts match your filters.</p>
          <p className="text-xs text-[#87867f] mt-1">Try resetting the topic or verdict filter above.</p>
        </div>
      ) : (
        <div className="space-y-3">
          <div className="flex items-center justify-between text-xs text-[#87867f] font-mono px-1">
            <span>Showing {archiveItems.length} of {archiveTotal} historical posts</span>
            <span>Instant retrieval &bull; 0 LLM tokens spent</span>
          </div>
          {archiveItems.map((item) => (
            <div
              key={item.id}
              className="bg-[#faf9f5] hover:bg-[#f0eee6]/40 transition border border-[#e3dacc] rounded-2xl p-5 flex flex-col justify-between gap-3 shadow-anthropic"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="space-y-1.5">
                  <h4 className="text-sm font-serif font-medium text-[#141413] leading-snug">{item.title}</h4>
                  <div className="flex items-center gap-2 text-[11px] text-[#87867f] font-mono flex-wrap">
                    <span className={`text-[10px] font-medium px-2.5 py-0.5 rounded-full border ${getTopicBadgeClass(item.topic_tag)}`}>
                      {item.topic_tag}
                    </span>
                    <span>{item.source}</span>
                    <span className="text-[#b0aea5]">&bull;</span>
                    <span className="text-[#87867f]">
                      {new Date(item.created_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                    </span>
                    {item.url && (
                      <>
                        <span className="text-[#b0aea5]">&bull;</span>
                        <a href={item.url} target="_blank" rel="noreferrer" className="hover:text-[#141413] flex items-center gap-1">
                          <span>source</span>
                          <ExternalLink className="w-2.5 h-2.5" />
                        </a>
                      </>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <span className={`text-xs font-mono font-semibold px-2.5 py-1 rounded-full border ${
                    item.verdict === 'pass'
                      ? 'bg-[#c6613f]/10 text-[#c6613f] border-[#c6613f]/30'
                      : item.verdict === 'review'
                      ? 'bg-[#d97757]/10 text-[#d97757] border-[#d97757]/30'
                      : 'bg-[#f0eee6] text-[#87867f] border-[#e3dacc]'
                  }`}>
                    {typeof item.score === 'number' ? item.score.toFixed(2) : item.score}
                  </span>
                  <span className="text-[10px] uppercase tracking-wider font-mono text-[#87867f]">
                    {item.verdict}
                  </span>
                </div>
              </div>

              <div className="flex justify-end pt-2 border-t border-[#e3dacc]">
                <button
                  onClick={() => onOpenInterview({ title: item.title, url: item.url, topic_tag: item.topic_tag })}
                  className="text-xs text-[#c6613f] hover:text-[#a54c2d] font-medium flex items-center gap-1.5 transition"
                >
                  <Sparkles className="w-3 h-3 text-[#d97757]" />
                  <span>Brief & Perspective</span>
                  <ArrowRight className="w-3 h-3" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
