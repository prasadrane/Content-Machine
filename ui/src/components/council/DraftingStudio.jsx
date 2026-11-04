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
    <form onSubmit={onSubmit} className="bg-[#f0eee6]/60 text-[#141413] p-6 rounded-2xl border border-[#e3dacc] shadow-anthropic space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h3 className="text-xs uppercase font-mono tracking-wider text-[#87867f] flex items-center gap-2">
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
            className="text-sm bg-[#faf9f5] border border-[#b0aea5] rounded-lg px-3 py-2 text-[#141413] w-40 placeholder-[#68675f]"
          />
        </div>
      </div>

      {/* Quick-select recent spikes */}
      {recentSpikes.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5 pt-1">
          <span className="text-[10px] font-mono text-[#87867f] uppercase mr-1">Recent:</span>
          {recentSpikes.slice(0, 4).map((spk) => (
            <button
              key={spk.spike_id}
              type="button"
              onClick={() => onSelectSpike(spk.spike_id)}
              className={`text-[11px] font-mono px-2.5 py-0.5 rounded-full border transition flex items-center gap-1 ${
                spikeId === spk.spike_id
                  ? 'bg-[#c6613f]/10 text-[#c6613f] border-[#c6613f]/30 font-semibold'
                  : 'bg-[#faf9f5] text-[#87867f] border-[#e3dacc] hover:border-[#b0aea5] hover:text-[#141413]'
              }`}
            >
              <span>{spk.spike_id}</span>
              <span className={spikeId === spk.spike_id ? 'text-[#c6613f]/80' : 'text-[#87867f]'}>
                ({spk.peak_score.toFixed(2)})
              </span>
            </button>
          ))}
        </div>
      )}

      {/* Iteration Mode Selector */}
      <div className="flex items-center justify-between gap-2 flex-wrap pt-0.5">
        <span className="text-[10px] font-mono text-[#87867f] uppercase">Mode:</span>
        <div className="flex items-center gap-1.5">
          <button
            type="button"
            aria-pressed={maxIterations === 1}
            onClick={() => onMaxIterationsChange && onMaxIterationsChange(1)}
            className={`text-[11px] font-mono px-2.5 py-0.5 rounded-full border transition ${
              maxIterations === 1
                ? 'bg-[#c6613f]/10 text-[#c6613f] border-[#c6613f]/30 font-semibold'
                : 'bg-[#faf9f5] text-[#87867f] border-[#e3dacc] hover:border-[#b0aea5]'
            }`}
          >
            ⚡ Single Pass (~30s)
          </button>
          <button
            type="button"
            aria-pressed={maxIterations === 3}
            onClick={() => onMaxIterationsChange && onMaxIterationsChange(3)}
            className={`text-[11px] font-mono px-2.5 py-0.5 rounded-full border transition ${
              maxIterations === 3
                ? 'bg-[#c6613f]/10 text-[#c6613f] border-[#c6613f]/30 font-semibold'
                : 'bg-[#faf9f5] text-[#87867f] border-[#e3dacc] hover:border-[#b0aea5]'
            }`}
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
        className="w-full text-base leading-relaxed bg-[#faf9f5] border border-[#b0aea5] rounded-xl p-4 text-[#141413] resize-y placeholder-[#68675f]"
      />

      <details className="rounded-xl border border-[#e3dacc] p-3">
        <summary className="cursor-pointer min-h-10 text-sm font-medium">Source and author notes (optional)</summary>
        <p className="text-sm text-[#58574f] my-3">Keep source claims, direct experience, and interpretation separate. These session notes are not automatically included in model requests.</p>
        {['What the source says', 'What I directly experienced', 'My interpretation'].map(label => (
          <label key={label} className="block text-sm space-y-1 mt-3">
            <span>{label}</span>
            <textarea rows={3} value={notes[label] || ''} onChange={event => updateNote(label, event.target.value)} className="w-full rounded-lg border border-[#b0aea5] bg-[#faf9f5] p-2 text-base" />
          </label>
        ))}
      </details>

      {error && (
        <div role="alert" className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-800 text-sm flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
          <span>{error}</span>
        </div>
      )}

      <button
        type="submit"
        disabled={loading}
        className="w-full py-2.5 px-4 bg-[#c6613f] hover:bg-[#b55535] disabled:opacity-50 text-[#faf9f5] rounded-full text-xs font-medium transition flex items-center justify-center gap-2 shadow-sm tracking-wide"
      >
        {loading ? <RotateCw className="w-3.5 h-3.5 animate-spin" /> : <Users className="w-3.5 h-3.5" />}
        <span>
          {loading ? 'Council Deliberating & Revising...' : (maxIterations === 1 ? 'Submit to Council (Single Pass ~30s)' : 'Submit to Council (Full Loop)')}
        </span>
      </button>
    </form>
  )
}
