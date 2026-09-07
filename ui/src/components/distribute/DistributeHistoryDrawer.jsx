import React, { useState, useMemo } from 'react'
import { History, X, Search, RotateCw, ArrowRight, CheckCircle2, Layers } from 'lucide-react'

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

      <div className="relative bg-[#faf9f5] border-l border-[#e3dacc] w-full max-w-xl h-full shadow-2xl flex flex-col z-10">
        {/* Drawer Header */}
        <div className="p-5 border-b border-[#e3dacc] flex items-center justify-between shrink-0">
          <div>
            <h3 className="font-serif text-base font-semibold text-[#141413] flex items-center gap-2">
              <History className="w-4 h-4 text-[#c6613f]" />
              <span>Content History & Past Posts</span>
            </h3>
            <p className="text-xs text-[#87867f] mt-0.5">
              Browse past Council peak drafts and previously distributed platform bundles.
            </p>
          </div>
          <button
            type="button"
            aria-label="Close history drawer"
            onClick={onClose}
            className="p-1 rounded-full text-[#87867f] hover:text-[#141413] hover:bg-[#f0eee6] transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Search & Filter Controls */}
        <div className="p-4 border-b border-[#e3dacc] bg-[#f0eee6]/40 space-y-3 shrink-0">
          {/* Search bar */}
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-[#87867f]" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by slug or content keywords..."
              className="w-full text-xs font-mono bg-[#faf9f5] border border-[#e3dacc] rounded-xl pl-9 pr-3.5 py-2 text-[#141413] placeholder-[#b0aea5] focus:outline-none focus:border-[#141413]"
            />
            {search && (
              <button
                type="button"
                onClick={() => setSearch('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-[#87867f] hover:text-[#141413]"
              >
                <X className="w-3 h-3" />
              </button>
            )}
          </div>

          {/* Filter Tabs */}
          <div className="flex items-center gap-1.5 text-xs font-mono">
            <button
              type="button"
              onClick={() => setFilter('all')}
              className={`px-3 py-1 rounded-full border transition ${
                filter === 'all'
                  ? 'bg-[#141413] text-[#faf9f5] border-[#141413] font-medium'
                  : 'bg-[#faf9f5] text-[#87867f] border-[#e3dacc] hover:border-[#b0aea5]'
              }`}
            >
              All ({items.length})
            </button>
            <button
              type="button"
              onClick={() => setFilter('distributed')}
              className={`px-3 py-1 rounded-full border transition ${
                filter === 'distributed'
                  ? 'bg-[#141413] text-[#faf9f5] border-[#141413] font-medium'
                  : 'bg-[#faf9f5] text-[#87867f] border-[#e3dacc] hover:border-[#b0aea5]'
              }`}
            >
              Distributed ({distributedCount})
            </button>
            <button
              type="button"
              onClick={() => setFilter('council')}
              className={`px-3 py-1 rounded-full border transition ${
                filter === 'council'
                  ? 'bg-[#141413] text-[#faf9f5] border-[#141413] font-medium'
                  : 'bg-[#faf9f5] text-[#87867f] border-[#e3dacc] hover:border-[#b0aea5]'
              }`}
            >
              Council Drafts ({councilCount})
            </button>
          </div>
        </div>

        {/* History Items Scrollable List */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {loading && (
            <div className="p-12 text-center text-[#87867f] space-y-2">
              <RotateCw className="w-5 h-5 mx-auto animate-spin text-[#c6613f]" />
              <p className="text-xs font-mono">Loading past posts...</p>
            </div>
          )}

          {!loading && filteredItems.length === 0 && (
            <div className="border border-dashed border-[#b0aea5] rounded-2xl p-10 text-center text-[#87867f] bg-[#f0eee6]/30">
              <Layers className="w-8 h-8 mx-auto mb-2.5 text-[#b0aea5] stroke-1" />
              <p className="text-xs font-medium text-[#141413]">No matching posts found.</p>
              <p className="text-[11px] text-[#87867f] mt-0.5">
                {search ? 'Try adjusting your search keywords.' : 'Run Council iterations or distribution to build history.'}
              </p>
            </div>
          )}

          {!loading &&
            filteredItems.map((item) => {
              const hasScore = item.peak_score !== null && item.peak_score !== undefined
              const isPass = hasScore && item.peak_score >= 8.0

              return (
                <div
                  key={item.slug}
                  onClick={() => onSelect(item)}
                  className="bg-[#f0eee6]/60 hover:bg-[#f0eee6] border border-[#e3dacc] hover:border-[#b0aea5] rounded-xl p-4 transition cursor-pointer space-y-2 shadow-xs group"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-mono text-xs font-semibold text-[#141413] truncate">
                      {item.slug}
                    </span>
                    <div className="flex items-center gap-1.5 shrink-0">
                      {hasScore && (
                        <span
                          className={`text-[10px] font-mono px-2 py-0.5 rounded-full border ${
                            isPass
                              ? 'bg-emerald-50 text-emerald-800 border-emerald-200 font-semibold'
                              : 'bg-[#c6613f]/10 text-[#c6613f] border-[#c6613f]/30'
                          }`}
                        >
                          Peak: {item.peak_score.toFixed(2)}
                        </span>
                      )}
                      {item.has_bundle && (
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-[#141413] text-[#faf9f5]">
                          Bundled
                        </span>
                      )}
                    </div>
                  </div>

                  {item.title && (
                    <h4 className="text-xs font-serif font-medium text-[#141413] line-clamp-1">
                      {item.title}
                    </h4>
                  )}

                  {item.anchor_text && (
                    <p className="text-[11px] text-[#87867f] font-mono line-clamp-2 bg-[#faf9f5] p-2 rounded-lg border border-[#e3dacc]/70 leading-relaxed">
                      {item.anchor_text}
                    </p>
                  )}

                  <div className="flex items-center justify-between pt-1 text-[10px] font-mono text-[#87867f]">
                    {/* Formats badges */}
                    <div className="flex items-center gap-1 flex-wrap">
                      {item.available_formats?.map((fmt) => (
                        <span
                          key={fmt}
                          className="px-1.5 py-0.5 rounded bg-[#faf9f5] border border-[#e3dacc] text-[#141413]"
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
                </div>
              )
            })}
        </div>
      </div>
    </div>
  )
}
