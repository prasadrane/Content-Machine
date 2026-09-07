import React from 'react'
import { RotateCw, Sparkles, AlertCircle } from 'lucide-react'
import RssPane from './RssPane'
import GithubPane from './GithubPane'
import LinkedinPane from './LinkedinPane'
import {
  devFeedPresets,
  companyBlogPresets,
  newsletterPresets,
  podcastPresets,
  redditPresets,
  industryRadarPresets,
  viralRadarAllUrls,
  githubPresets,
  linkedInPresets,
} from './presets'

export default function SourceCockpit({
  sourceSubTab,
  onSubTabChange,
  rssUrls,
  setRssUrls,
  githubRepos,
  setGithubRepos,
  linkedInProfiles,
  setLinkedInProfiles,
  linkedInLiAt,
  setLinkedInLiAt,
  maxAgeDays,
  setMaxAgeDays,
  maxItemsPerFeed,
  setMaxItemsPerFeed,
  rssCount,
  ghCount,
  liCount,
  totalSources,
  onRun,
  loading,
  error,
  linkedInStatus,
  syncingLinkedIn,
  syncMsg,
  onSyncLinkedIn,
}) {
  const handleLoadViralRadar = () => {
    setRssUrls(viralRadarAllUrls.join('\n'))
  }

  const handleAddPreset = (url) => {
    const current = rssUrls.split('\n').map(s => s.trim()).filter(Boolean)
    if (!current.includes(url)) {
      setRssUrls(prev => prev.trim() ? `${prev.trim()}\n${url}` : url)
    }
  }

  const handleAddGithubPreset = (repo) => {
    const current = githubRepos.split('\n').map(s => s.trim()).filter(Boolean)
    if (!current.includes(repo)) {
      setGithubRepos(prev => prev.trim() ? `${prev.trim()}\n${repo}` : repo)
    }
  }

  const handleAddLinkedInPreset = (handle) => {
    const current = linkedInProfiles.split('\n').map(s => s.trim()).filter(Boolean)
    if (!current.includes(handle)) {
      setLinkedInProfiles(prev => prev.trim() ? `${prev.trim()}\n${handle}` : handle)
    }
  }

  return (
    <form 
      onSubmit={onRun} 
      className="md:col-span-1 bg-[#f0eee6]/60 rounded-2xl border border-[#e3dacc] shadow-anthropic flex flex-col md:sticky md:top-24 md:max-h-[calc(100vh-7.5rem)] overflow-hidden"
    >
      {/* Cockpit Header & Sub-Tab Navigation */}
      <div className="p-4 pb-3 border-b border-[#e3dacc] shrink-0 space-y-3 bg-[#f0eee6]/80">
        <div className="flex items-center justify-between">
          <h3 className="text-xs uppercase font-mono tracking-wider text-[#87867f]">Source Cockpit</h3>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-[#faf9f5] text-[#87867f] border border-[#e3dacc]">
            {totalSources} Active
          </span>
        </div>

        {/* Sub-Tab Navigation Header with item counts */}
        <div className="grid grid-cols-3 gap-1 bg-[#faf9f5] p-1 rounded-xl border border-[#e3dacc]">
          <button
            type="button"
            onClick={() => onSubTabChange('rss')}
            className={`py-1.5 px-2 rounded-lg text-xs font-medium transition flex items-center justify-center gap-1.5 ${
              sourceSubTab === 'rss'
                ? 'bg-[#141413] text-[#faf9f5] shadow-xs'
                : 'text-[#87867f] hover:text-[#141413] hover:bg-[#e3dacc]/40'
            }`}
          >
            <span>RSS Feeds</span>
            <span className={`font-mono text-[10px] px-1.5 py-0.2 rounded-full ${
              sourceSubTab === 'rss' ? 'bg-[#2a2a28] text-[#faf9f5]' : 'bg-[#f0eee6] text-[#87867f]'
            }`}>
              {rssCount}
            </span>
          </button>

          <button
            type="button"
            onClick={() => onSubTabChange('github')}
            className={`py-1.5 px-2 rounded-lg text-xs font-medium transition flex items-center justify-center gap-1.5 ${
              sourceSubTab === 'github'
                ? 'bg-[#141413] text-[#faf9f5] shadow-xs'
                : 'text-[#87867f] hover:text-[#141413] hover:bg-[#e3dacc]/40'
            }`}
          >
            <span>GitHub</span>
            <span className={`font-mono text-[10px] px-1.5 py-0.2 rounded-full ${
              sourceSubTab === 'github' ? 'bg-[#2a2a28] text-[#faf9f5]' : 'bg-[#f0eee6] text-[#87867f]'
            }`}>
              {ghCount}
            </span>
          </button>

          <button
            type="button"
            onClick={() => onSubTabChange('linkedin')}
            className={`py-1.5 px-2 rounded-lg text-xs font-medium transition flex items-center justify-center gap-1.5 ${
              sourceSubTab === 'linkedin'
                ? 'bg-[#141413] text-[#faf9f5] shadow-xs'
                : 'text-[#87867f] hover:text-[#141413] hover:bg-[#e3dacc]/40'
            }`}
          >
            <span>LinkedIn</span>
            <span className={`font-mono text-[10px] px-1.5 py-0.2 rounded-full ${
              sourceSubTab === 'linkedin' ? 'bg-[#2a2a28] text-[#faf9f5]' : 'bg-[#f0eee6] text-[#87867f]'
            }`}>
              {liCount}
            </span>
          </button>
        </div>
      </div>

      {/* Scrollable Sub-Tab Body */}
      <div className="p-4 space-y-4 overflow-y-auto flex-1">
        {sourceSubTab === 'rss' && (
          <RssPane
            rssUrls={rssUrls}
            setRssUrls={setRssUrls}
            rssCount={rssCount}
            onLoadViralRadar={handleLoadViralRadar}
            onAddPreset={handleAddPreset}
            redditPresets={redditPresets}
            newsletterPresets={newsletterPresets}
            devFeedPresets={devFeedPresets}
            companyBlogPresets={companyBlogPresets}
            industryRadarPresets={industryRadarPresets}
            podcastPresets={podcastPresets}
          />
        )}

        {sourceSubTab === 'github' && (
          <GithubPane
            githubRepos={githubRepos}
            setGithubRepos={setGithubRepos}
            ghCount={ghCount}
            githubPresets={githubPresets}
            onAddGithubPreset={handleAddGithubPreset}
          />
        )}

        {sourceSubTab === 'linkedin' && (
          <LinkedinPane
            linkedInProfiles={linkedInProfiles}
            setLinkedInProfiles={setLinkedInProfiles}
            linkedInLiAt={linkedInLiAt}
            setLinkedInLiAt={setLinkedInLiAt}
            linkedInStatus={linkedInStatus}
            syncingLinkedIn={syncingLinkedIn}
            syncMsg={syncMsg}
            onSyncLinkedIn={onSyncLinkedIn}
            linkedInPresets={linkedInPresets}
            onAddLinkedInPreset={handleAddLinkedInPreset}
          />
        )}
      </div>

      {/* Sticky Footer: Freshness, Limits & Trigger Bar */}
      <div className="p-4 bg-[#f0eee6] border-t border-[#e3dacc] space-y-3 shrink-0">
        <div className="grid grid-cols-2 gap-2.5">
          <div>
            <label className="block text-[11px] font-medium text-[#141413] mb-1">Max Age</label>
            <div className="relative">
              <input
                type="number"
                min="1"
                max="90"
                value={maxAgeDays}
                onChange={(e) => setMaxAgeDays(e.target.value)}
                placeholder="10"
                className="w-full text-xs font-mono bg-[#faf9f5] border border-[#e3dacc] rounded-xl p-2 pr-10 text-[#141413] focus:outline-none focus:border-[#141413]"
              />
              <span className="absolute right-2.5 top-2 text-[10px] text-[#87867f] font-mono">days</span>
            </div>
          </div>
          <div>
            <label className="block text-[11px] font-medium text-[#141413] mb-1">Cap / Feed</label>
            <div className="relative">
              <input
                type="number"
                min="1"
                max="100"
                value={maxItemsPerFeed}
                onChange={(e) => setMaxItemsPerFeed(e.target.value)}
                placeholder="25"
                className="w-full text-xs font-mono bg-[#faf9f5] border border-[#e3dacc] rounded-xl p-2 pr-11 text-[#141413] focus:outline-none focus:border-[#141413]"
              />
              <span className="absolute right-2.5 top-2 text-[10px] text-[#87867f] font-mono">posts</span>
            </div>
          </div>
        </div>

        <div className="flex items-center justify-between pt-0.5">
          <span className="inline-flex items-center gap-1.5 text-[11px] font-mono px-2.5 py-1 rounded-full bg-[#faf9f5] text-[#87867f] border border-[#e3dacc]">
            <span className="w-1.5 h-1.5 rounded-full bg-[#c6613f]"></span>
            <span>{totalSources} sources configured</span>
          </span>
          <span className="text-[10px] font-mono text-[#87867f]">
            {loading ? 'Evaluating...' : 'Ready'}
          </span>
        </div>

        {error && (
          <div className="p-2.5 bg-rose-50 border border-rose-200 rounded-xl text-rose-800 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
            <span className="text-[11px] leading-tight">{error}</span>
          </div>
        )}

        <button
          type="submit"
          disabled={loading}
          className="w-full py-2.5 px-4 bg-[#141413] hover:bg-[#252524] disabled:opacity-50 text-[#faf9f5] rounded-full text-xs font-medium transition flex items-center justify-center gap-2 shadow-sm"
        >
          {loading ? (
            <>
              <RotateCw className="w-3.5 h-3.5 animate-spin text-[#faf9f5]" />
              <span>Evaluating Samples...</span>
            </>
          ) : (
            <>
              <Sparkles className="w-3.5 h-3.5 text-[#d97757]" />
              <span>Scan & Score Candidates</span>
            </>
          )}
        </button>
      </div>
    </form>
  )
}
