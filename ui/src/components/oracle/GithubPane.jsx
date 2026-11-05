import React, { useMemo } from 'react'
import { PresetChipGroup, selectedSetFrom } from './PresetEditorPane'

export default function GithubPane({
  githubRepos,
  setGithubRepos,
  ghCount,
  sourceError = '',
  githubPresets,
  onAddGithubPreset,
}) {
  const selectedRepos = useMemo(() => selectedSetFrom(githubRepos), [githubRepos])

  return (
    <div className="space-y-3 animate-fadeIn">
      <div className="flex items-center justify-between">
        <label htmlFor="oracle-github-repos" className="cm-label block">GitHub Repositories</label>
        <span className="text-sm text-anthropic-cloud-dark">{ghCount} configured</span>
      </div>
      <textarea
        id="oracle-github-repos"
        aria-invalid={Boolean(sourceError)}
        aria-describedby={sourceError ? 'oracle-source-error' : undefined}
        rows={4}
        value={githubRepos}
        onChange={(e) => setGithubRepos(e.target.value)}
        placeholder="owner/repo (one per line)"
        className="cm-textarea w-full font-mono"
      />
      <span className="text-sm text-anthropic-cloud-dark block">e.g. facebook/react or rust-lang/rust</span>

      <PresetChipGroup
        label="Quick Presets:"
        labelClass="cm-label block mb-2"
        wrapClass="space-y-2 pt-1"
        presets={githubPresets}
        valueKey="repo"
        selected={selectedRepos}
        onAdd={onAddGithubPreset}
      />
    </div>
  )
}
