import React from 'react'
import { AlertCircle, RotateCw, Users } from 'lucide-react'

export default function DraftingStudio({
  draft,
  onDraftChange,
  spikeId,
  onSpikeChange,
  recentSpikes,
  onSelectSpike,
  loading,
  error,
  onSubmit,
}) {
  return (
    <form onSubmit={onSubmit} className="bg-[#141413] text-[#faf9f5] p-6 rounded-2xl border border-[#252524] shadow-xl space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-xs uppercase font-mono tracking-wider text-[#b0aea5] flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-[#d97757]" />
          <span>Draft Studio</span>
        </h3>
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={spikeId}
            onChange={(e) => onSpikeChange(e.target.value)}
            placeholder="Spike Slug"
            className="text-xs font-mono bg-[#1c1c1b] border border-[#333331] rounded-lg px-2.5 py-1 text-[#faf9f5] w-40 focus:outline-none focus:border-[#d97757]"
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
                  ? 'bg-[#c6613f]/30 text-[#faf9f5] border-[#c6613f]'
                  : 'bg-[#1c1c1b] text-[#b0aea5] border-[#333331] hover:text-[#faf9f5]'
              }`}
            >
              <span>{spk.spike_id}</span>
              <span className="text-[#87867f]">({spk.peak_score.toFixed(2)})</span>
            </button>
          ))}
        </div>
      )}

      <textarea
        rows={18}
        value={draft}
        onChange={(e) => onDraftChange(e.target.value)}
        placeholder="Paste your rough draft or write directly here..."
        className="w-full text-xs font-mono leading-relaxed bg-[#1c1c1b] border border-[#333331] rounded-xl p-4 text-[#faf9f5] focus:outline-none focus:border-[#d97757] resize-none placeholder-[#87867f]"
      />

      {error && (
        <div className="p-3 bg-rose-950/40 border border-rose-800 rounded-xl text-rose-300 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
          <span>{error}</span>
        </div>
      )}

      <button
        type="submit"
        disabled={loading}
        className="w-full py-2.5 px-4 bg-[#c6613f] hover:bg-[#b55535] disabled:opacity-50 text-[#faf9f5] rounded-full text-xs font-medium transition flex items-center justify-center gap-2 shadow-sm tracking-wide"
      >
        {loading ? <RotateCw className="w-3.5 h-3.5 animate-spin" /> : <Users className="w-3.5 h-3.5" />}
        <span>{loading ? 'Council Deliberating & Revising...' : 'Submit to Council'}</span>
      </button>
    </form>
  )
}
