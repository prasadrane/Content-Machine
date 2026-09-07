import React from 'react'
import { Share2, RotateCw, Check, Copy } from 'lucide-react'

export default function OutputPreviews({
  bundle,
  loading,
  slug,
  availableFormats,
  activeFormat,
  onFormatChange,
  copied,
  onCopy,
  getFormatContent,
}) {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between pb-2 border-b border-[#e3dacc]">
        <h3 className="text-xs uppercase font-mono tracking-wider text-[#87867f]">Derivative Formats</h3>
        {bundle && (
          <span className="text-[11px] font-mono text-[#c6613f]">Saved to /projects/{slug}/distribution/</span>
        )}
      </div>

      {!bundle && !loading && (
        <div className="border border-dashed border-[#b0aea5] rounded-2xl p-12 text-center text-[#87867f] bg-[#f0eee6]/30">
          <Share2 className="w-8 h-8 mx-auto mb-3 stroke-1 text-[#b0aea5]" />
          <p className="text-sm font-medium text-[#141413]">No derivatives generated yet.</p>
          <p className="text-xs text-[#87867f] mt-1">Submit anchor text to generate LinkedIn post, X thread, video scripts, and newsletter.</p>
        </div>
      )}

      {loading && (
        <div className="border border-[#e3dacc] rounded-2xl p-12 text-center text-[#87867f] space-y-3 bg-[#f0eee6]/50 shadow-anthropic">
          <RotateCw className="w-6 h-6 mx-auto animate-spin text-[#c6613f]" />
          <p className="text-sm font-medium text-[#141413]">Generating Enabled Platform Derivatives...</p>
          <p className="text-xs text-[#87867f] font-mono">Enforcing strict groundedness (zero new facts)</p>
        </div>
      )}

      {bundle && (
        <div className="space-y-4">
          {/* Channel Switcher */}
          <div className="flex items-center justify-between bg-[#f0eee6] p-1 rounded-full border border-[#e3dacc] overflow-x-auto shadow-anthropic">
            <div className="flex items-center gap-1">
              {availableFormats.map(fmt => {
                const isActive = activeFormat === fmt.id || (fmt.id === 'video_script_short' && activeFormat === 'video_script')
                const isLinkedIn = fmt.id === 'linkedin'
                return (
                  <button
                    key={fmt.id}
                    type="button"
                    onClick={() => onFormatChange(fmt.id)}
                    className={`px-3.5 py-1.5 rounded-full text-xs font-mono transition flex items-center gap-1.5 whitespace-nowrap ${
                      isActive
                        ? 'bg-[#141413] text-[#faf9f5] shadow-sm'
                        : 'text-[#87867f] hover:text-[#141413]'
                    }`}
                  >
                    {isLinkedIn && <span className="w-1.5 h-1.5 rounded-full bg-[#d97757]" />}
                    <span>{fmt.shortLabel}</span>
                  </button>
                )
              })}
            </div>

            <button
              type="button"
              onClick={() => onCopy(getFormatContent(activeFormat))}
              className="flex items-center gap-1.5 px-3 py-1 text-xs font-mono bg-[#faf9f5] hover:bg-[#e3dacc]/50 text-[#141413] rounded-full border border-[#e3dacc] transition shrink-0 ml-2"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5 text-[#87867f]" />}
              <span>{copied ? 'Copied!' : 'Copy'}</span>
            </button>
          </div>

          {/* Text Preview Box */}
          <div className="bg-[#faf9f5] border border-[#e3dacc] rounded-2xl p-6 font-mono text-xs text-[#141413] leading-relaxed max-h-[480px] overflow-y-auto whitespace-pre-wrap shadow-anthropic">
            {getFormatContent(activeFormat) || 'No content available for this format.'}
          </div>
        </div>
      )}
    </div>
  )
}
