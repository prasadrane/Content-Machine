import React from 'react'

// Derive the selected-value Set from a newline-delimited textarea string.
// Shared list-edit logic for the oracle preset-editor panes.
export function selectedSetFrom(text) {
  return new Set((text || '').split('\n').map((s) => s.trim()).filter(Boolean))
}

// Render one labeled group of toggleable preset chips.
// Behavior-identical to the markup previously duplicated in Rss/Github/Linkedin panes.
export function PresetChipGroup({
  label,
  labelClass,
  wrapClass,
  presets,
  valueKey,
  selected,
  onAdd,
}) {
  return (
    <div className={wrapClass}>
      <span className={labelClass}>{label}</span>
      <div className="flex flex-wrap gap-1.5">
        {presets.map((preset) => {
          const value = preset[valueKey]
          const isSelected = selected.has(value)
          return (
            <button
              key={value}
              type="button"
              onClick={() => onAdd(value)}
              className={`text-[10px] font-mono px-2.5 py-0.5 rounded-full border transition duration-150 flex items-center gap-1 ${
                isSelected
                  ? 'bg-[#141413] text-[#faf9f5] border-[#141413] font-semibold shadow-xs'
                  : 'bg-[#faf9f5] text-[#87867f] hover:text-[#141413] border-[#e3dacc] hover:border-[#b0aea5]'
              }`}
              title={isSelected ? `Remove ${value}` : `Add ${value}`}
            >
              <span>{isSelected ? '✓' : '+'}</span>
              <span>{preset.label}</span>
            </button>
          )
        })}
      </div>
    </div>
  )
}
