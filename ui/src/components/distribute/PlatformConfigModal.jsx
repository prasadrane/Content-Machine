import React from 'react'
import { Sliders, X } from 'lucide-react'
import { DISTRIBUTION_FORMATS } from '../../lib/constants'

export default function PlatformConfigModal({
  show,
  onClose,
  enabledFormats,
  onToggleFormat,
  onSelectAll,
  onResetDefaults,
}) {
  if (!show) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#141413]/60 backdrop-blur-sm animate-fadeIn">
      <div className="bg-[#faf9f5] border border-[#e3dacc] rounded-2xl w-full max-w-lg overflow-hidden shadow-2xl space-y-0">
        {/* Modal Header */}
        <div className="p-5 border-b border-[#e3dacc] flex items-center justify-between">
          <div>
            <h3 className="font-serif text-base font-semibold text-[#141413] flex items-center gap-2">
              <Sliders className="w-4 h-4 text-[#c6613f]" />
              <span>Platform Distribution Formats</span>
            </h3>
            <p className="text-xs text-[#87867f] mt-0.5">
              Select which platforms to generate. LinkedIn is set as default.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded-full text-[#87867f] hover:text-[#141413] hover:bg-[#f0eee6] transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Platform Options List */}
        <div className="p-5 space-y-3 max-h-[60vh] overflow-y-auto">
          {DISTRIBUTION_FORMATS.map(fmt => {
            const isEnabled = enabledFormats[fmt.id]
            return (
              <div
                key={fmt.id}
                onClick={() => onToggleFormat(fmt.id)}
                className={`p-4 rounded-xl border transition cursor-pointer flex items-start gap-3.5 ${
                  isEnabled
                    ? 'bg-[#f0eee6] border-[#b0aea5]'
                    : 'bg-[#faf9f5] border-[#e3dacc] opacity-60'
                }`}
              >
                <input
                  type="checkbox"
                  checked={isEnabled}
                  onChange={() => {}}
                  className="mt-1 rounded text-[#141413] focus:ring-0 focus:outline-none"
                />
                <div className="flex-1 space-y-1">
                  <div className="flex items-center justify-between">
                    <span className={`text-xs font-medium ${isEnabled ? 'text-[#141413]' : 'text-[#87867f]'}`}>
                      {fmt.label}
                    </span>
                    <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full border ${fmt.tagColor}`}>
                      {fmt.tag}
                    </span>
                  </div>
                  <p className="text-[11px] text-[#87867f] leading-normal">
                    {fmt.desc}
                  </p>
                </div>
              </div>
            )
          })}
        </div>

        {/* Modal Footer */}
        <div className="p-4 bg-[#f0eee6] border-t border-[#e3dacc] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onSelectAll}
              className="text-[11px] font-mono text-[#87867f] hover:text-[#141413] px-2 py-1 rounded hover:bg-[#e3dacc]/50 transition"
            >
              Select All
            </button>
            <span className="text-[#b0aea5]">•</span>
            <button
              type="button"
              onClick={onResetDefaults}
              className="text-[11px] font-mono text-[#87867f] hover:text-[#141413] px-2 py-1 rounded hover:bg-[#e3dacc]/50 transition"
            >
              Reset Defaults
            </button>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="px-5 py-2 bg-[#141413] hover:bg-[#252524] text-[#faf9f5] rounded-full text-xs font-medium transition shadow-sm"
          >
            Apply & Close
          </button>
        </div>
      </div>
    </div>
  )
}
