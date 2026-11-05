import React, { useState, useMemo } from 'react'
import { History, X, Search, RotateCw, ArrowRight, CheckCircle2, Layers } from 'lucide-react'
import { useDialogFocus } from './useDialogFocus'

const FORMAT_LABELS = {
  linkedin: 'LinkedIn',
  x_thread: 'X Thread',
  video_script: 'Video',
  video_script_short: 'Short Video',
  video_script_long: 'Long Video',
  newsletter: 'Newsletter',
}

export default function DistributeHistoryDrawer({
  show,
  onClose,
  items = [],
  loading = false,
  onSelect,
}) {
  const dialogRef = useDialogFocus(show, onClose)
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState('all') // 'all' | 'distributed' | 'council'

  const filteredItems = useMemo(() => {
    return items.filter((item) => {
      // Category filter
      if (filter === 'distributed' && !item.has_bundle) return false
      if (filter === 'council' && item.has_bundle) return false

      // Search filter
      if (!search.trim()) return true
      const q = search.toLowerCase()
      const matchSlug = item.slug?.toLowerCase().includes(q)
      const matchTitle = item.title?.toLowerCase().includes(q)
      const matchText = item.anchor_text?.toLowerCase().includes(q)
      return matchSlug || matchTitle || matchText
    })
  }, [items, filter, search])

  if (!show) return null

  const distributedCount = items.filter((i) => i.has_bundle).length
  const councilCount = items.filter((i) => !i.has_bundle).length

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-[#141413]/50 backdrop-blur-xs animate-fadeIn">
      {/* Click outside backdrop to close */}
      <div className="absolute inset-0" onClick={onClose} />

      <div ref={dialogRef} role="dialog" aria-modal="true" aria-label="Content history" className="cm-dialog relative w-full max-w-xl h-full flex flex-col z-10">
        {/* Drawer Header */}
        <div className="cm-page-header p-5 shrink-0">
          <div>
            <h3 className="cm-panel-title flex items-center gap-2">
              <History className="w-4 h-4 text-[#c6613f]" />
              <span>Content History & Past Posts</span>
            </h3>
            <p className="cm-muted mt-0.5">
              Browse past Council peak drafts and previously distributed platform bundles.
            </p>
          </div>
          <button
            type="button"
            aria-label="Close history drawer"
            onClick={onClose}
            className="cm-icon-button"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Search & Filter Controls */}
        <div className="cm-subpanel space-y-3 shrink-0">
          {/* Search bar */}
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-[#87867f]" />
            <input
              type="text"
              aria-label="Search content history"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by slug or content keywords..."
              className="cm-input w-full pl-10 pr-12"
            />
            {search && (
              <button
                type="button"
                aria-label="Clear history search"
                onClick={() => setSearch('')}
                className="cm-icon-button absolute right-1 top-1/2 -translate-y-1/2"
              >
                <X className="w-3 h-3" />
              </button>
            )}
          </div>

          {/* Filter Tabs */}
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => setFilter('all')}
              className={`cm-chip ${filter === 'all' ? 'cm-chip-active' : ''}`}
            >
              All ({items.length})
            </button>
            <button
              type="button"
              onClick={() => setFilter('distributed')}
              className={`cm-chip ${filter === 'distributed' ? 'cm-chip-active' : ''}`}
            >
              Distributed ({distributedCount})
            </button>
            <button
              type="button"
              onClick={() => setFilter('council')}
              className={`cm-chip ${filter === 'council' ? 'cm-chip-active' : ''}`}
            >
              Council Drafts ({councilCount})
            </button>
          </div>
        </div>

        {/* History Items Scrollable List */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {loading && (
            <div className="cm-muted text-center space-y-2">
              <RotateCw className="w-5 h-5 mx-auto animate-spin text-[#c6613f]" />
              <p className="cm-prose">Loading past posts...</p>
            </div>
          )}

          {!loading && filteredItems.length === 0 && (
            <div className="cm-empty text-center">
              <Layers className="w-8 h-8 mx-auto mb-2.5 text-[#b0aea5] stroke-1" />
              <p className="cm-prose font-medium">No matching posts found.</p>
              <p className="cm-muted mt-0.5">
                {search ? 'Try adjusting your search keywords.' : 'Run Council iterations or distribution to build history.'}
              </p>
            </div>
          )}

          {!loading &&
            filteredItems.map((item) => {
              const hasScore = item.peak_score !== null && item.peak_score !== undefined
              const isPass = hasScore && item.peak_score >= 8.0

              return (
                <button
                  type="button"
                  aria-label={`Load ${item.slug}`}
                  key={item.slug}
                  onClick={() => onSelect(item)}
                  className="cm-subpanel block w-full text-left cursor-pointer space-y-3 group"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-sans text-sm font-semibold text-[#141413] truncate">
                      {item.slug}
                    </span>
                    <div className="flex items-center gap-1.5 shrink-0">
                      {hasScore && (
                        <span
                          className={`cm-badge ${isPass ? 'cm-status-success' : 'cm-status-warning'}`}
                        >
                          Peak: {item.peak_score.toFixed(2)}
                        </span>
                      )}
                      {item.has_bundle && (
                        <span className="cm-badge">
                          Bundled
                        </span>
                      )}
                    </div>
                  </div>

                  {item.title && (
                    <h4 className="cm-panel-title line-clamp-1">
                      {item.title}
                    </h4>
                  )}

                  {item.anchor_text && (
                    <p className="cm-subpanel line-clamp-2">
                      {item.anchor_text}
                    </p>
                  )}

                  <div className="cm-muted flex flex-wrap items-center justify-between gap-3">
                    {/* Formats badges */}
                    <div className="flex items-center gap-1 flex-wrap">
                      {item.available_formats?.map((fmt) => (
                        <span
                          key={fmt}
                          className="cm-badge"
                        >
                          {FORMAT_LABELS[fmt] || fmt}
                        </span>
                      ))}
                    </div>

                    <div className="flex items-center gap-1 text-[#c6613f] group-hover:translate-x-0.5 transition font-sans font-medium">
                      <span>{item.has_bundle ? 'Load Post & Derivatives' : 'Load Post'}</span>
                      <ArrowRight className="w-3 h-3" />
                    </div>
                  </div>
                </button>
              )
            })}
        </div>
      </div>
    </div>
  )
}
