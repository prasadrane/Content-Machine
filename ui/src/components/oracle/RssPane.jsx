import React, { useMemo } from 'react'
import { Flame } from 'lucide-react'
import { PresetChipGroup, selectedSetFrom } from './PresetEditorPane'

const GROUP_LABEL_CLASS = 'cm-label block mb-2'

export default function RssPane({
  rssUrls,
  setRssUrls,
  rssCount,
  sourceError = '',
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
        className="cm-button cm-button-secondary w-full flex items-center justify-center gap-2 duration-150 group"
        title="Populate top viral newsletters, Reddit communities, and Techmeme"
      >
        <Flame className="w-3.5 h-3.5 text-anthropic-ivory-light group-hover:scale-110 transition-transform" />
        <span>Load Viral Tech Radar (8 Signals)</span>
      </button>

      <div className="flex items-center justify-between">
        <label htmlFor="oracle-rss-feeds" className="cm-label block">RSS / Atom Feeds</label>
        <div className="flex items-center gap-2">
          <span className="text-sm text-anthropic-cloud-dark">{rssCount} configured</span>
          {rssCount > 0 && (
            <button
              type="button"
              onClick={() => setRssUrls('')}
              className="cm-button cm-button-quiet hover:underline"
            >
              Clear
            </button>
          )}
        </div>
      </div>
      <textarea
        id="oracle-rss-feeds"
        aria-invalid={Boolean(sourceError)}
        aria-describedby={sourceError ? 'oracle-source-error' : undefined}
        rows={4}
        value={rssUrls}
        onChange={(e) => setRssUrls(e.target.value)}
        placeholder="https://example.com/feed.xml"
        className="cm-textarea w-full font-mono"
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
