import React from 'react'
import { Flame } from 'lucide-react'

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

      {/* Quick Presets */}
      <div className="space-y-2 pt-1">
        <div>
          <span className="text-[10px] text-[#87867f] font-mono block mb-1">Reddit Communities:</span>
          <div className="flex flex-wrap gap-1.5">
            {redditPresets.map((preset) => (
              <button
                key={preset.url}
                type="button"
                onClick={() => onAddPreset(preset.url)}
                className="text-[10px] font-mono px-2.5 py-0.5 rounded-full bg-[#faf9f5] hover:bg-[#141413] text-[#141413] hover:text-[#faf9f5] border border-[#e3dacc] transition duration-150"
                title={`Add ${preset.url}`}
              >
                + {preset.label}
              </button>
            ))}
          </div>
        </div>
        <div>
          <span className="text-[10px] text-[#87867f] font-mono block mb-1">Top Newsletters:</span>
          <div className="flex flex-wrap gap-1.5">
            {newsletterPresets.map((preset) => (
              <button
                key={preset.url}
                type="button"
                onClick={() => onAddPreset(preset.url)}
                className="text-[10px] font-mono px-2.5 py-0.5 rounded-full bg-[#faf9f5] hover:bg-[#141413] text-[#141413] hover:text-[#faf9f5] border border-[#e3dacc] transition duration-150"
                title={`Add ${preset.url}`}
              >
                + {preset.label}
              </button>
            ))}
          </div>
        </div>
        <div>
          <span className="text-[10px] text-[#87867f] font-mono block mb-1">Dev Community:</span>
          <div className="flex flex-wrap gap-1.5">
            {devFeedPresets.map((preset) => (
              <button
                key={preset.url}
                type="button"
                onClick={() => onAddPreset(preset.url)}
                className="text-[10px] font-mono px-2.5 py-0.5 rounded-full bg-[#faf9f5] hover:bg-[#141413] text-[#141413] hover:text-[#faf9f5] border border-[#e3dacc] transition duration-150"
                title={`Add ${preset.url}`}
              >
                + {preset.label}
              </button>
            ))}
          </div>
        </div>
        <div>
          <span className="text-[10px] text-[#87867f] font-mono block mb-1">Company TechBlogs:</span>
          <div className="flex flex-wrap gap-1.5">
            {companyBlogPresets.map((preset) => (
              <button
                key={preset.url}
                type="button"
                onClick={() => onAddPreset(preset.url)}
                className="text-[10px] font-mono px-2.5 py-0.5 rounded-full bg-[#faf9f5] hover:bg-[#141413] text-[#141413] hover:text-[#faf9f5] border border-[#e3dacc] transition duration-150"
                title={`Add ${preset.url}`}
              >
                + {preset.label}
              </button>
            ))}
          </div>
        </div>
        <div>
          <span className="text-[10px] text-[#87867f] font-mono block mb-1">Industry Radar:</span>
          <div className="flex flex-wrap gap-1.5">
            {industryRadarPresets.map((preset) => (
              <button
                key={preset.url}
                type="button"
                onClick={() => onAddPreset(preset.url)}
                className="text-[10px] font-mono px-2.5 py-0.5 rounded-full bg-[#faf9f5] hover:bg-[#141413] text-[#141413] hover:text-[#faf9f5] border border-[#e3dacc] transition duration-150"
                title={`Add ${preset.url}`}
              >
                + {preset.label}
              </button>
            ))}
          </div>
        </div>
        <div>
          <span className="text-[10px] text-[#87867f] font-mono block mb-1">Podcasts:</span>
          <div className="flex flex-wrap gap-1.5">
            {podcastPresets.map((preset) => (
              <button
                key={preset.url}
                type="button"
                onClick={() => onAddPreset(preset.url)}
                className="text-[10px] font-mono px-2.5 py-0.5 rounded-full bg-[#faf9f5] hover:bg-[#141413] text-[#141413] hover:text-[#faf9f5] border border-[#e3dacc] transition duration-150"
                title={`Add ${preset.url}`}
              >
                + {preset.label}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
