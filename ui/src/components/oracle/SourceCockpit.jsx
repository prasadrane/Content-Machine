import React from 'react'
import { RotateCw, Sparkles, AlertCircle } from 'lucide-react'
import RssPane from './RssPane'
import GithubPane from './GithubPane'
import LinkedinPane from './LinkedinPane'
import { toggleSource } from './sourceInputs'
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
  compact = false,
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

  const handleTogglePreset = (url) => {
    setRssUrls(toggleSource(rssUrls, url))
  }

  const handleToggleGithubPreset = (repo) => {
    setGithubRepos(toggleSource(githubRepos, repo))
  }

  const handleToggleLinkedInPreset = (handle) => {
    setLinkedInProfiles(toggleSource(linkedInProfiles, handle))
  }

  return (
    <form 
      onSubmit={onRun} 
      className="cm-panel min-w-0 space-y-4"
    >
      <details open={!compact}>
        <summary className="cm-label cursor-pointer min-h-10 flex flex-wrap items-center gap-2">
          Edit sources and limits <span className="font-normal text-anthropic-cloud-dark">({totalSources} sources configured)</span>
        </summary>
      {/* Cockpit Header & Sub-Tab Navigation */}
      <div className="pb-4 border-b border-anthropic-oat shrink-0 space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="cm-panel-title">Source Cockpit</h3>
          <span className="cm-badge">
            {totalSources} Active
          </span>
        </div>

        {/* Sub-Tab Navigation Header with item counts */}
        <div className="cm-subpanel grid grid-cols-3 gap-1">
          <button
            type="button"
            aria-pressed={sourceSubTab === 'rss'}
            onClick={() => onSubTabChange('rss')}
            className={` cm-chip flex items-center justify-center gap-1.5 ${
              sourceSubTab === 'rss'
                ? "cm-chip-active"
                : ""
            }  `}
          >
            <span>RSS Feeds</span>
            <span className={` text-sm px-1.5 py-0.2 rounded-full ${
              sourceSubTab === 'rss' ? "bg-anthropic-slate-dark text-anthropic-ivory-light" : "bg-anthropic-ivory-medium text-anthropic-cloud-dark"
            }  `}>
              {rssCount}
            </span>
          </button>

          <button
            type="button"
            aria-pressed={sourceSubTab === 'github'}
            onClick={() => onSubTabChange('github')}
            className={` cm-chip flex items-center justify-center gap-1.5 ${
              sourceSubTab === 'github'
                ? "cm-chip-active"
                : ""
            }  `}
          >
            <span>GitHub</span>
            <span className={` text-sm px-1.5 py-0.2 rounded-full ${
              sourceSubTab === 'github' ? "bg-anthropic-slate-dark text-anthropic-ivory-light" : "bg-anthropic-ivory-medium text-anthropic-cloud-dark"
            }  `}>
              {ghCount}
            </span>
          </button>

          <button
            type="button"
            aria-pressed={sourceSubTab === 'linkedin'}
            onClick={() => onSubTabChange('linkedin')}
            className={` cm-chip flex items-center justify-center gap-1.5 ${
              sourceSubTab === 'linkedin'
                ? "cm-chip-active"
                : ""
            }  `}
          >
            <span>LinkedIn</span>
            <span className={` text-sm px-1.5 py-0.2 rounded-full ${
              sourceSubTab === 'linkedin' ? "bg-anthropic-slate-dark text-anthropic-ivory-light" : "bg-anthropic-ivory-medium text-anthropic-cloud-dark"
            }  `}>
              {liCount}
            </span>
          </button>
        </div>
      </div>

      {/* Scrollable Sub-Tab Body */}
      <div className="space-y-4 overflow-y-auto flex-1">
        {sourceSubTab === 'rss' && (
          <RssPane
            rssUrls={rssUrls}
            setRssUrls={setRssUrls}
            rssCount={rssCount}
            sourceError={error?.startsWith('RSS feed') ? error : ''}
            onLoadViralRadar={handleLoadViralRadar}
            onAddPreset={handleTogglePreset}
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
            sourceError={error?.startsWith('GitHub repository') ? error : ''}
            githubPresets={githubPresets}
            onAddGithubPreset={handleToggleGithubPreset}
          />
        )}

        {sourceSubTab === 'linkedin' && (
          <LinkedinPane
            linkedInProfiles={linkedInProfiles}
            sourceError={error?.startsWith('LinkedIn profile') ? error : ''}
            setLinkedInProfiles={setLinkedInProfiles}
            linkedInLiAt={linkedInLiAt}
            setLinkedInLiAt={setLinkedInLiAt}
            linkedInStatus={linkedInStatus}
            syncingLinkedIn={syncingLinkedIn}
            syncMsg={syncMsg}
            onSyncLinkedIn={onSyncLinkedIn}
            linkedInPresets={linkedInPresets}
            onAddLinkedInPreset={handleToggleLinkedInPreset}
          />
        )}
      </div>
      </details>
      {/* Sticky Footer: Freshness, Limits & Trigger Bar */}
      <div className="pt-4 border-t border-anthropic-oat space-y-3">
        <div className="grid grid-cols-2 gap-2.5 max-w-md">
          <div>
            <label className="cm-label block mb-1">Max Age</label>
            <div className="relative">
              <input
                type="number"
                aria-label="Maximum source age in days"
                min="1"
                max="90"
                value={maxAgeDays}
                onChange={(e) => setMaxAgeDays(e.target.value)}
                placeholder="10"
                className="cm-input w-full pr-10"
              />
              <span className="absolute right-2.5 top-2 text-sm text-anthropic-cloud-dark">days</span>
            </div>
          </div>
          <div>
            <label className="cm-label block mb-1">Cap / Feed</label>
            <div className="relative">
              <input
                type="number"
                aria-label="Maximum posts per feed"
                min="1"
                max="100"
                value={maxItemsPerFeed}
                onChange={(e) => setMaxItemsPerFeed(e.target.value)}
                placeholder="25"
                className="cm-input w-full pr-11"
              />
              <span className="absolute right-2.5 top-2 text-sm text-anthropic-cloud-dark">posts</span>
            </div>
          </div>
        </div>

        <div className="flex items-center justify-between pt-0.5">
          <span className="cm-badge inline-flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-anthropic-accent"></span>
            <span>{totalSources} sources configured</span>
          </span>
          <span className="text-sm text-anthropic-cloud-dark">
            {loading ? 'Evaluating...' : 'Ready'}
          </span>
        </div>

        {error && (
          <div role="alert" id="oracle-source-error" className="cm-status cm-status-error flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
            <span className="text-sm leading-tight">{error}</span>
          </div>
        )}

        <button
          type="submit"
          disabled={loading}
          className="cm-button cm-button-primary w-full disabled:opacity-50 flex items-center justify-center gap-2"
        >
          {loading ? (
            <>
              <RotateCw className="w-3.5 h-3.5 animate-spin text-anthropic-ivory-light" />
              <span>Evaluating Samples...</span>
            </>
          ) : (
            <>
              <Sparkles className="w-3.5 h-3.5 text-anthropic-clay" />
              <span>Scan & Score Candidates</span>
            </>
          )}
        </button>
      </div>
    </form>
  )
}
