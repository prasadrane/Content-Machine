import React from 'react'

export default function GithubPane({
  githubRepos,
  setGithubRepos,
  ghCount,
  githubPresets,
  onAddGithubPreset,
}) {
  return (
    <div className="space-y-3 animate-fadeIn">
      <div className="flex items-center justify-between">
        <label className="block text-xs font-medium text-[#141413]">GitHub Repositories</label>
        <span className="text-[10px] font-mono text-[#87867f]">{ghCount} configured</span>
      </div>
      <textarea
        rows={4}
        value={githubRepos}
        onChange={(e) => setGithubRepos(e.target.value)}
        placeholder="owner/repo (one per line)"
        className="w-full text-xs font-mono bg-[#faf9f5] border border-[#e3dacc] rounded-xl p-2.5 text-[#141413] focus:outline-none focus:border-[#141413] focus:ring-1 focus:ring-[#141413] placeholder-[#b0aea5]"
      />
      <span className="text-[11px] text-[#87867f] block">e.g. facebook/react or rust-lang/rust</span>

      <div className="space-y-2 pt-1">
        <span className="text-[10px] text-[#87867f] font-mono block mb-1">Quick Presets:</span>
        <div className="flex flex-wrap gap-1.5">
          {githubPresets.map((p) => (
            <button
              key={p.repo}
              type="button"
              onClick={() => onAddGithubPreset(p.repo)}
              className="text-[10px] font-mono px-2.5 py-0.5 rounded-full bg-[#faf9f5] hover:bg-[#141413] text-[#141413] hover:text-[#faf9f5] border border-[#e3dacc] transition duration-150"
              title={`Add ${p.repo}`}
            >
              + {p.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
