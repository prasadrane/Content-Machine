import React from 'react'
import { Search, X, RotateCw, Tag, Database, ExternalLink, Sparkles, ArrowRight } from 'lucide-react'
import { formatTopicLabel } from '../../lib/topics'
import TopicIcon from './TopicIcon'

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
      <div className="cm-panel space-y-4">
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="w-4 h-4 absolute left-3.5 top-3 text-anthropic-cloud-dark" />
            <input
              aria-label="Search saved signals"
              type="text"
              value={archiveSearch}
              onChange={(e) => setArchiveSearch(e.target.value)}
              placeholder="Search past scanned posts by title or source..."
              className="cm-input w-full pl-10 pr-12"
            />
            {archiveSearch && (
              <button 
                type="button"
                aria-label="Clear signal search"
                onClick={() => setArchiveSearch('')}
                className="cm-icon-button absolute right-1 top-1"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          {/* Verdict Filter Buttons */}
          <div className="flex flex-wrap items-center gap-2">
            {[
              { key: 'All', label: 'All' },
              { key: 'pass', label: 'Pass (≥8.0)' },
              { key: 'review', label: 'Review (7.5-8.0)' },
              { key: 'reject', label: 'Rejected' },
            ].map((v) => (
              <button
                key={v.key}
                type="button"
                aria-pressed={archiveVerdict === v.key}
                onClick={() => setArchiveVerdict(v.key)}
                className={` cm-chip shrink-0 ${
                  archiveVerdict === v.key
                    ? "cm-chip-active"
                    : ""
                }  `}
              >
                {v.label}
              </button>
            ))}
          </div>

          {/* Refresh Archive Button */}
          <button
            type="button"
            onClick={fetchArchive}
            className="cm-button cm-button-secondary flex items-center gap-1.5 shrink-0 self-start sm:self-auto"
            title="Refresh archive"
          >
            <RotateCw className={` w-3.5 h-3.5 ${archiveLoading ? "animate-spin text-anthropic-accent" : "text-anthropic-cloud-dark"}  `} />
            <span>Refresh</span>
          </button>
        </div>

        {/* Topic Taxonomy Pills */}
        <div>
          <div className="flex items-center gap-1.5 mb-2.5 text-sm font-medium text-anthropic-cloud-dark">
            <Tag className="w-3.5 h-3.5 text-anthropic-accent" />
            <span>Filter by Content Topic Taxonomy:</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {availableTopics.map((topic) => {
              const active = archiveTopic === topic
              return (
                <button
                  key={topic}
                  aria-pressed={active}
                  type="button"
                  onClick={() => setArchiveTopic(topic)}
                  className={` cm-chip flex items-center gap-1.5 ${
                    active
                      ? "cm-chip-active"
                      : ""
                  }  `}
                >
                  <TopicIcon topic={topic} />
                  <span>{formatTopicLabel(topic)}</span>
                  {topic !== 'All' && (
                    <span className={` text-sm px-1.5 py-0.2 rounded-full ${active ? "bg-anthropic-slate-dark text-anthropic-ivory-light" : "bg-anthropic-ivory-medium text-anthropic-cloud-dark"}  `}>
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
        <div className="cm-panel space-y-3">
          <RotateCw className="w-6 h-6 mx-auto animate-spin text-anthropic-accent" />
          <p className="cm-prose">Loading historical feed archive...</p>
        </div>
      ) : archiveItems.length === 0 ? (
        <div className="cm-empty">
          <Database className="w-8 h-8 mx-auto mb-3 stroke-1 text-anthropic-cloud-medium" />
          <p className="cm-prose">No historical posts match your filters.</p>
          <p className="cm-prose mt-1">Try resetting the topic or verdict filter above.</p>
        </div>
      ) : (
        <div className="space-y-3">
          <div className="cm-muted flex flex-wrap items-center justify-between gap-2">
            <span>Showing {archiveItems.length} of {archiveTotal} historical posts</span>
            <span>Instant retrieval &bull; 0 LLM tokens spent</span>
          </div>
          {archiveItems.map((item) => (
            <div
              key={item.id || item.url || item.title}
              className="cm-panel flex flex-col justify-between gap-3"
            >
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div className="space-y-1.5 min-w-0 break-words">
                  <h4 className="cm-panel-title leading-snug">{item.title}</h4>
                  <div className="flex items-center gap-2 text-sm text-anthropic-cloud-dark flex-wrap">
                    <span className="cm-badge">
                      {formatTopicLabel(item.topic_tag)}
                    </span>
                    <span>{item.source}</span>
                    <span className="text-anthropic-cloud-medium">&bull;</span>
                    {item.created_at && <span className="text-anthropic-cloud-dark">
                      {new Date(item.created_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                    </span>}
                    {item.url && (
                      <>
                        <span className="text-anthropic-cloud-medium">&bull;</span>
                        <a href={item.url} target="_blank" rel="noreferrer" className="cm-link flex items-center gap-1">
                          <span>source</span>
                          <ExternalLink className="w-2.5 h-2.5" />
                        </a>
                      </>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <span className={` cm-badge  ${
                    item.verdict === 'pass'
                      ? ""
                      : item.verdict === 'review'
                      ? ""
                      : ""
                  }  `}>
                    {typeof item.score === 'number' ? item.score.toFixed(2) : item.score}
                  </span>
                  <span className="text-sm uppercase tracking-wider text-anthropic-cloud-dark">
                    {item.verdict}
                  </span>
                </div>
              </div>

              {item.body_snippet && <p className="cm-prose leading-relaxed">{item.body_snippet}</p>}
              <div className="flex justify-end pt-2 border-t border-anthropic-oat">
                <button
                  type="button"
                  onClick={() => onOpenInterview(item)}
                  className="cm-button cm-button-quiet flex items-center gap-1.5"
                >
                  <Sparkles className="w-3 h-3 text-anthropic-clay" />
                  <span>Add my perspective</span>
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
