import React, { useMemo } from 'react'
import { Flame } from 'lucide-react'
import { PresetChipGroup, selectedSetFrom } from './PresetEditorPane'

const GROUP_LABEL_CLASS = 'text-[10px] text-[#87867f] font-mono block mb-1'

export default function RssPane({
  rssUrls,
  setRssUrls,
  rssCount,
  onLoadViralRadar,
  onAddPreset,
  redditPresets,
  newsletterPresets,
  devFeedPresets,
  companyBlogPresets,
  industryRadarPresets,
  podcastPresets,
}) {
  const selectedUrls = useMemo(() => selectedSetFrom(rssUrls), [rssUrls])

  return (
    <div className="space-y-3 animate-fadeIn">
      {/* 1-Click Top Viral Tech Radar Button */}
      <button
        type="button"
        onClick={onLoadViralRadar}
        className="w-full py-2 px-3 rounded-xl bg-gradient-to-r from-[#c6613f] to-[#d97757] hover:from-[#b55535] hover:to-[#c6613f] text-[#faf9f5] text-xs font-medium flex items-center justify-center gap-2 shadow-xs transition duration-150 group"
        title="Populate top viral newsletters, Reddit communities, and Techmeme"
      >
        <Flame className="w-3.5 h-3.5 text-[#faf9f5] group-hover:scale-110 transition-transform" />
        <span>🔥 Load Viral Tech Radar (8 Signals)</span>
      </button>

      <div className="flex items-center justify-between">
        <label className="block text-xs font-medium text-[#141413]">RSS / Atom Feeds</label>
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-mono text-[#87867f]">{rssCount} configured</span>
          {rssCount > 0 && (
            <button
              type="button"
              onClick={() => setRssUrls('')}
              className="text-[10px] font-mono text-[#c6613f] hover:underline"
            >
              Clear
            </button>
          )}
        </div>
      </div>
      <textarea
        rows={4}
        value={rssUrls}
        onChange={(e) => setRssUrls(e.target.value)}
        placeholder="https://example.com/feed.xml"
        className="w-full text-xs font-mono bg-[#faf9f5] border border-[#e3dacc] rounded-xl p-3 text-[#141413] focus:outline-none focus:border-[#141413] focus:ring-1 focus:ring-[#141413] placeholder-[#b0aea5]"
      />

      {/* Quick Presets with Visual Selection State */}
      <div className="space-y-2 pt-1">
        <PresetChipGroup
          label="Reddit Communities:"
          labelClass={GROUP_LABEL_CLASS}
          presets={redditPresets}
          valueKey="url"
          selected={selectedUrls}
          onAdd={onAddPreset}
        />
        <PresetChipGroup
          label="Top Newsletters:"
          labelClass={GROUP_LABEL_CLASS}
          presets={newsletterPresets}
          valueKey="url"
          selected={selectedUrls}
          onAdd={onAddPreset}
        />
        <PresetChipGroup
          label="Dev Community:"
          labelClass={GROUP_LABEL_CLASS}
          presets={devFeedPresets}
          valueKey="url"
          selected={selectedUrls}
          onAdd={onAddPreset}
        />
        <PresetChipGroup
          label="Company TechBlogs:"
          labelClass={GROUP_LABEL_CLASS}
          presets={companyBlogPresets}
          valueKey="url"
          selected={selectedUrls}
          onAdd={onAddPreset}
        />
        <PresetChipGroup
          label="Industry Radar:"
          labelClass={GROUP_LABEL_CLASS}
          presets={industryRadarPresets}
          valueKey="url"
          selected={selectedUrls}
          onAdd={onAddPreset}
        />
        <PresetChipGroup
          label="Podcasts:"
          labelClass={GROUP_LABEL_CLASS}
          presets={podcastPresets}
          valueKey="url"
          selected={selectedUrls}
          onAdd={onAddPreset}
        />
      </div>
    </div>
  )
}
