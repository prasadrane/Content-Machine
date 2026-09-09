import React, { useMemo } from 'react'
import { PresetChipGroup, selectedSetFrom } from './PresetEditorPane'

export default function GithubPane({
  githubRepos,
  setGithubRepos,
  ghCount,
  githubPresets,
  onAddGithubPreset,
}) {
  const selectedRepos = useMemo(() => selectedSetFrom(githubRepos), [githubRepos])

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

      <PresetChipGroup
        label="Quick Presets:"
        labelClass="text-[10px] text-[#87867f] font-mono block mb-1"
        wrapClass="space-y-2 pt-1"
        presets={githubPresets}
        valueKey="repo"
        selected={selectedRepos}
        onAdd={onAddGithubPreset}
      />
    </div>
  )
}
