import React from 'react'
import { X, Plus } from 'lucide-react'

/**
 * DomainsEditor — editable list of technical domain tags.
 * Props:
 *   domains        — string[]
 *   onAdd          — (e?) => void
 *   onRemove       — (domain: string) => void
 *   newDomainInput — string (controlled input value)
 *   onInputChange  — (value: string) => void
 *   onKeyDown      — KeyboardEvent handler
 */
export default function DomainsEditor({
  domains,
  onAdd,
  onRemove,
  newDomainInput,
  onInputChange,
  onKeyDown,
}) {
  return (
    <div className="bg-[#f0eee6]/60 border border-[#e3dacc] rounded-2xl p-5 sm:p-6 space-y-3.5 shadow-anthropic">
      <div className="flex items-center justify-between">
        <label className="text-xs uppercase font-mono tracking-wider text-[#87867f] font-semibold">
          Technical Domains &amp; Competencies
        </label>
        <span className="text-[10px] font-mono text-[#87867f]">
          {domains.length} domains
        </span>
      </div>
      <p className="text-xs text-[#87867f] font-sans">
        Display and manage authoritative technical domains applied across drafts:
      </p>

      {/* Tags list */}
      <div className="flex flex-wrap gap-2 pt-1">
        {domains.map((domain, idx) => (
          <span
            key={idx}
            className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono bg-[#faf9f5] border border-[#e3dacc] text-[#141413] shadow-xs group hover:border-[#b0aea5] transition"
          >
            <span>{domain}</span>
            <button
              type="button"
              onClick={() => onRemove(domain)}
              className="p-0.5 rounded-full text-[#87867f] hover:text-[#c6613f] transition"
              title={`Remove ${domain}`}
            >
              <X className="w-3 h-3" />
            </button>
          </span>
        ))}
        {domains.length === 0 && (
          <span className="text-xs text-[#87867f] italic">No domains configured.</span>
        )}
      </div>

      {/* Add Domain Input */}
      <div className="flex items-center gap-2 pt-2">
        <input
          type="text"
          value={newDomainInput}
          onChange={(e) => onInputChange(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder="Add domain (e.g., Event-Driven Architecture) and press Enter..."
          className="flex-1 text-xs font-mono bg-[#faf9f5] border border-[#e3dacc] rounded-xl px-3.5 py-2 text-[#141413] focus:outline-none focus:border-[#141413] placeholder-[#b0aea5] shadow-xs"
        />
        <button
          type="button"
          onClick={onAdd}
          disabled={!newDomainInput.trim()}
          className="px-4 py-2 bg-[#141413] hover:bg-[#252524] disabled:opacity-50 text-[#faf9f5] rounded-xl text-xs font-medium font-mono transition shrink-0 shadow-xs flex items-center gap-1.5"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>Add</span>
        </button>
      </div>
    </div>
  )
}
