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
    <form onSubmit={onSubmit} className="bg-[#f0eee6]/60 text-[#141413] p-6 rounded-2xl border border-[#e3dacc] shadow-anthropic space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-xs uppercase font-mono tracking-wider text-[#87867f] flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-[#c6613f]" />
          <span>Draft Studio</span>
        </h3>
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={spikeId}
            onChange={(e) => onSpikeChange(e.target.value)}
            placeholder="Spike Slug"
            className="text-xs font-mono bg-[#faf9f5] border border-[#e3dacc] rounded-lg px-2.5 py-1 text-[#141413] w-40 focus:outline-none focus:border-[#141413] placeholder-[#b0aea5]"
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

      <textarea
        rows={18}
        value={draft}
        onChange={(e) => onDraftChange(e.target.value)}
        placeholder="Paste your rough draft or write directly here..."
        className="w-full text-xs font-mono leading-relaxed bg-[#faf9f5] border border-[#e3dacc] rounded-xl p-4 text-[#141413] focus:outline-none focus:border-[#141413] resize-none placeholder-[#b0aea5]"
      />

      {error && (
        <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-800 text-xs flex items-center gap-2">
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
        <span>{loading ? 'Council Deliberating & Revising...' : 'Submit to Council'}</span>
      </button>
    </form>
  )
}
