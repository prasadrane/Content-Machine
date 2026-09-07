import React from 'react'
import { Search, Sliders, Tag, X } from 'lucide-react'
import { formatTopicLabel } from '../../lib/topics'

export default function TriageToolbar({
  batchSearch,
  setBatchSearch,
  batchSort,
  setBatchSort,
  batchTopic,
  setBatchTopic,
  batchTopics,
  candidates,
}) {
  return (
    <div className="bg-[#f0eee6]/60 p-3.5 rounded-2xl border border-[#e3dacc] space-y-3 shadow-anthropic animate-fadeIn">
      {/* Search & Sort Controls Row */}
      <div className="flex flex-col sm:flex-row gap-2.5 items-stretch sm:items-center justify-between">
        {/* Live Search Input */}
        <div className="relative flex-1">
          <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-[#87867f]" />
          <input
            type="text"
            value={batchSearch}
            onChange={(e) => setBatchSearch(e.target.value)}
            placeholder="Filter active batch by title, source, or excerpt..."
            className="w-full pl-9 pr-8 py-1.5 bg-[#faf9f5] border border-[#e3dacc] rounded-full text-xs text-[#141413] placeholder-[#b0aea5] focus:outline-none focus:border-[#141413] transition"
          />
          {batchSearch && (
            <button
              type="button"
              onClick={() => setBatchSearch('')}
              className="absolute right-3 top-2 text-[#87867f] hover:text-[#141413]"
              title="Clear search"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        {/* Sort Controls */}
        <div className="flex items-center gap-1 bg-[#faf9f5] p-1 rounded-full border border-[#e3dacc] shrink-0 shadow-2xs">
          <span className="text-[10px] font-mono text-[#87867f] px-2 flex items-center gap-1">
            <Sliders className="w-3 h-3 text-[#b0aea5]" />
            <span>Sort:</span>
          </span>
          <button
            type="button"
            onClick={() => setBatchSort('score')}
            className={`px-3 py-1 rounded-full text-xs font-mono transition ${
              batchSort === 'score'
                ? 'bg-[#141413] text-[#faf9f5] font-medium shadow-sm'
                : 'text-[#87867f] hover:text-[#141413]'
            }`}
          >
            <span>Score &darr;</span>
          </button>
          <button
            type="button"
            onClick={() => setBatchSort('recency')}
            className={`px-3 py-1 rounded-full text-xs font-mono transition ${
              batchSort === 'recency'
                ? 'bg-[#141413] text-[#faf9f5] font-medium shadow-sm'
                : 'text-[#87867f] hover:text-[#141413]'
            }`}
          >
            <span>Recency &darr;</span>
          </button>
        </div>
      </div>

      {/* Topic Filter Chips */}
      <div className="flex items-center gap-1.5 flex-wrap pt-0.5">
        <span className="text-[10px] font-mono text-[#87867f] uppercase tracking-wider shrink-0 flex items-center gap-1 mr-1">
          <Tag className="w-3 h-3 text-[#d97757]" />
          <span>Topics:</span>
        </span>
        {batchTopics.map((topic) => {
          const active = batchTopic === topic
          const count = topic === 'All'
            ? candidates.length
            : candidates.filter(c => c.topic_tag === topic).length

          return (
            <button
              key={topic}
              type="button"
              onClick={() => setBatchTopic(topic)}
              className={`text-xs px-3 py-1 rounded-full border transition flex items-center gap-1.5 ${
                active
                  ? 'bg-[#141413] text-[#faf9f5] border-[#141413] shadow-sm font-medium'
                  : 'bg-[#faf9f5] text-[#87867f] border-[#e3dacc] hover:border-[#b0aea5] hover:text-[#141413]'
              }`}
            >
              <span>{formatTopicLabel(topic)}</span>
              <span className={`text-[10px] px-1.5 py-0.2 rounded-full font-mono ${
                active ? 'bg-[#2a2a28] text-[#faf9f5]' : 'bg-[#f0eee6] text-[#87867f]'
              }`}>
                {count}
              </span>
            </button>
          )
        })}
      </div>
    </div>
  )
}
