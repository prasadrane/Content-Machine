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
    <div className="cm-panel space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h3 className="cm-panel-title">
          Technical Domains &amp; Competencies
        </h3>
        <span className="cm-muted">
          {domains.length} domains
        </span>
      </div>
      <p className="cm-muted">
        Display and manage authoritative technical domains applied across drafts:
      </p>

      {/* Tags list */}
      <div className="flex flex-wrap gap-2 pt-1">
        {domains.map((domain, idx) => (
          <span
            key={idx}
            className="cm-badge inline-flex items-center gap-1"
          >
            <span>{domain}</span>
            <button
              type="button"
              onClick={() => onRemove(domain)}
              className="cm-icon-button"
              title={`Remove ${domain}`}
              aria-label={`Remove ${domain}`}
            >
              <X className="w-3 h-3" />
            </button>
          </span>
        ))}
        {domains.length === 0 && (
          <span className="cm-muted">No domains configured.</span>
        )}
      </div>

      {/* Add Domain Input */}
      <div className="flex items-center gap-2 pt-2">
        <input
          aria-label="Add technical domain"
          type="text"
          value={newDomainInput}
          onChange={(e) => onInputChange(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder="Add domain (e.g., Event-Driven Architecture) and press Enter..."
          className="cm-input min-w-0 flex-1"
        />
        <button
          type="button"
          onClick={onAdd}
          disabled={!newDomainInput.trim()}
          className="cm-button cm-button-secondary shrink-0"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>Add</span>
        </button>
      </div>
    </div>
  )
}
