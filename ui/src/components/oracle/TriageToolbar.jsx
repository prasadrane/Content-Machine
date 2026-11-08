import React from 'react'
import { Search, Sliders, Tag, X } from 'lucide-react'
import { formatTopicLabel } from '../../lib/topics'
import TopicIcon from './TopicIcon'

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
    <div className="cm-subpanel space-y-3 animate-fadeIn">
      {/* Search & Sort Controls Row */}
      <div className="flex flex-col sm:flex-row gap-2.5 items-stretch sm:items-center justify-between">
        {/* Live Search Input */}
        <div className="relative flex-1">
          <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-anthropic-cloud-dark" />
          <input
            type="text"
            value={batchSearch}
            onChange={(e) => setBatchSearch(e.target.value)}
            placeholder="Filter active batch by title, source, or excerpt..."
            className="cm-input w-full pl-10 pr-12"
          />
          {batchSearch && (
            <button
              type="button"
              onClick={() => setBatchSearch('')}
              className="cm-icon-button absolute right-1 top-1"
              title="Clear search"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        {/* Sort Controls */}
        <div className="cm-subpanel flex items-center gap-1 shrink-0">
          <span className="text-sm text-anthropic-cloud-dark px-2 flex items-center gap-1">
            <Sliders className="w-3 h-3 text-anthropic-cloud-medium" />
            <span>Sort:</span>
          </span>
          <button
            type="button"
            onClick={() => setBatchSort('score')}
            className={` cm-chip  ${
              batchSort === 'score'
                ? "cm-chip-active"
                : ""
            }  `}
          >
            <span>Score &darr;</span>
          </button>
          <button
            type="button"
            onClick={() => setBatchSort('recency')}
            className={` cm-chip  ${
              batchSort === 'recency'
                ? "cm-chip-active"
                : ""
            }  `}
          >
            <span>Recency &darr;</span>
          </button>
        </div>
      </div>

      {/* Topic Filter Chips */}
      <div className="flex items-center gap-1.5 flex-wrap pt-0.5">
        <span className="text-sm text-anthropic-cloud-dark uppercase tracking-wider shrink-0 flex items-center gap-1 mr-1">
          <Tag className="w-3 h-3 text-anthropic-clay" />
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
              className={` cm-chip flex items-center gap-1.5 ${
                active
                  ? "cm-chip-active"
                  : ""
              }  `}
            >
              <TopicIcon topic={topic} />
              <span>{formatTopicLabel(topic)}</span>
              <span className={` text-sm px-1.5 py-0.2 rounded-full ${
                active ? "bg-anthropic-slate-dark text-anthropic-ivory-light" : "bg-anthropic-ivory-medium text-anthropic-cloud-dark"
              }  `}>
                {count}
              </span>
            </button>
          )
        })}
      </div>
    </div>
  )
}
