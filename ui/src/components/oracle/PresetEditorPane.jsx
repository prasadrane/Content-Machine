import React from 'react'
import { parseSources } from './sourceInputs'

// Derive the selected-value Set from a newline-delimited textarea string.
// Shared list-edit logic for the oracle preset-editor panes.
export function selectedSetFrom(text) {
  return new Set(parseSources(text || ''))
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
              aria-pressed={isSelected}
              onClick={() => onAdd(value)}
              className={` cm-chip duration-150 flex items-center gap-1 ${
                isSelected
                  ? "cm-chip-active"
                  : ""
              }  `}
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
