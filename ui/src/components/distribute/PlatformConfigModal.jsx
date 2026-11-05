import React from 'react'
import { Sliders, X } from 'lucide-react'
import { DISTRIBUTION_FORMATS } from '../../lib/constants'
import { useDialogFocus } from './useDialogFocus'

export default function PlatformConfigModal({
  show,
  onClose,
  enabledFormats,
  onToggleFormat,
  onSelectAll,
  onResetDefaults,
}) {
  const dialogRef = useDialogFocus(show, onClose)
  if (!show) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#141413]/60 backdrop-blur-sm animate-fadeIn">
      <div ref={dialogRef} role="dialog" aria-modal="true" aria-label="Platform Distribution Formats" className="cm-dialog w-full max-w-lg space-y-0">
        {/* Modal Header */}
        <div className="cm-page-header p-5">
          <div>
            <h3 className="cm-panel-title flex items-center gap-2">
              <Sliders className="w-4 h-4 text-[#c6613f]" />
              <span>Platform Distribution Formats</span>
            </h3>
            <p className="cm-muted mt-0.5">
              Select which platforms to generate. LinkedIn is set as default.
            </p>
          </div>
          <button
            type="button"
            aria-label="Close platform settings"
            onClick={onClose}
            className="cm-icon-button"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Platform Options List */}
        <div className="p-5 space-y-3 max-h-[60vh] overflow-y-auto">
          {DISTRIBUTION_FORMATS.map(fmt => {
            const isEnabled = enabledFormats[fmt.id]
            return (
              <label
                key={fmt.id}
                className="cm-subpanel cursor-pointer flex items-start gap-3"
              >
                <input
                  type="checkbox"
                  checked={Boolean(isEnabled)}
                  aria-label={fmt.label}
                  onChange={() => onToggleFormat(fmt.id)}
                  className="mt-1"
                />
                <div className="flex-1 space-y-1">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="cm-label">
                      {fmt.label}
                    </span>
                    <span className="cm-badge">
                      {fmt.tag}
                    </span>
                  </div>
                  <p className="cm-muted">
                    {fmt.desc}
                  </p>
                </div>
              </label>
            )
          })}
        </div>

        {/* Modal Footer */}
        <div className="cm-divider p-4 flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={onSelectAll}
              className="cm-button cm-button-secondary"
            >
              Select All
            </button>
            <span className="text-[#b0aea5]">•</span>
            <button
              type="button"
              onClick={onResetDefaults}
              className="cm-button cm-button-secondary"
            >
              Reset Defaults
            </button>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="cm-button cm-button-primary"
          >
            Apply & Close
          </button>
        </div>
      </div>
    </div>
  )
}
