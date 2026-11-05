import React, { useState } from 'react'
import { AlertCircle, RotateCw, Users } from 'lucide-react'

export default function DraftingStudio({
  draft,
  onDraftChange,
  spikeId,
  onSpikeChange,
  recentSpikes,
  onSelectSpike,
  maxIterations = 1,
  onMaxIterationsChange,
  loading,
  error,
  onSubmit,
}) {
  const [notesByStory, setNotesByStory] = useState({})
  const notes = notesByStory[spikeId] || {}
  const updateNote = (name, value) => setNotesByStory(previous => ({ ...previous, [spikeId]: { ...previous[spikeId], [name]: value } }))
  return (
    <form onSubmit={onSubmit} className="cm-panel space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h3 className="cm-panel-title flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-[#c6613f]" />
          <span>Draft Studio</span>
        </h3>
        <div className="flex items-center gap-2">
          <input
            aria-label="Story identifier"
            type="text"
            value={spikeId}
            onChange={(e) => onSpikeChange(e.target.value)}
            placeholder="Spike Slug"
            className="cm-input w-40"
          />
        </div>
      </div>

      {/* Quick-select recent spikes */}
      {recentSpikes.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5 pt-1">
          <span className="cm-muted mr-1">Recent:</span>
          {recentSpikes.slice(0, 4).map((spk) => (
            <button
              key={spk.spike_id}
              type="button"
              onClick={() => onSelectSpike(spk.spike_id)}
              className={`cm-chip ${spikeId === spk.spike_id ? 'cm-chip-active' : ''}`}
            >
              <span>{spk.spike_id}</span>
              <span >
                ({spk.peak_score.toFixed(2)})
              </span>
            </button>
          ))}
        </div>
      )}

      {/* Iteration Mode Selector */}
      <div className="flex items-center justify-between gap-2 flex-wrap pt-0.5">
        <span className="cm-muted">Mode:</span>
        <div className="flex items-center gap-1.5">
          <button
            type="button"
            aria-pressed={maxIterations === 1}
            onClick={() => onMaxIterationsChange && onMaxIterationsChange(1)}
            className={`cm-chip ${maxIterations === 1 ? 'cm-chip-active' : ''}`}
          >
            ⚡ Single Pass (~30s)
          </button>
          <button
            type="button"
            aria-pressed={maxIterations === 3}
            onClick={() => onMaxIterationsChange && onMaxIterationsChange(3)}
            className={`cm-chip ${maxIterations === 3 ? 'cm-chip-active' : ''}`}
          >
            🔄 Full Loop (3 Iters)
          </button>
        </div>
      </div>

      <textarea
        aria-label="Current draft"
        rows={18}
        value={draft}
        onChange={(e) => onDraftChange(e.target.value)}
        placeholder="Paste your rough draft or write directly here..."
        className="cm-textarea w-full resize-y"
      />

      <details className="cm-subpanel">
        <summary className="cm-label cursor-pointer">Source and author notes (optional)</summary>
        <p className="cm-muted my-3">Keep source claims, direct experience, and interpretation separate. These session notes are not automatically included in model requests.</p>
        {['What the source says', 'What I directly experienced', 'My interpretation'].map(label => (
          <label key={label} className="cm-label block space-y-1 mt-3">
            <span>{label}</span>
            <textarea rows={3} value={notes[label] || ''} onChange={event => updateNote(label, event.target.value)} className="cm-textarea w-full" />
          </label>
        ))}
      </details>

      {error && (
        <div role="alert" className="cm-status cm-status-error flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
          <span>{error}</span>
        </div>
      )}

      <button
        type="submit"
        disabled={loading}
        className="cm-button cm-button-primary w-full flex items-center justify-center gap-2"
      >
        {loading ? <RotateCw className="w-3.5 h-3.5 animate-spin" /> : <Users className="w-3.5 h-3.5" />}
        <span>
          {loading ? 'Council Deliberating & Revising...' : (maxIterations === 1 ? 'Submit to Council (Single Pass ~30s)' : 'Submit to Council (Full Loop)')}
        </span>
      </button>
    </form>
  )
}
