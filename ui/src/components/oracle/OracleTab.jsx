import React, { useState, useEffect } from 'react'
import { Compass, Database } from 'lucide-react'
import { runOracleScan, getOracleHistory } from '../../api/oracle'
import { getLinkedInStatus, syncLinkedIn } from '../../api/linkedin'
import { DEFAULT_AVAILABLE_TOPICS } from './presets'
import SourceCockpit from './SourceCockpit'
import CandidateStream from './CandidateStream'
import ArchiveView from './ArchiveView'
import InterviewModal from './InterviewModal'

export default function OracleTab({ onSendToCouncil, onSendToCouncilWithDraft }) {
  const [selectedInterviewItem, setSelectedInterviewItem] = useState(null)
  const [oracleView, setOracleView] = useState('active') // 'active' | 'archive'
  const [sourceSubTab, setSourceSubTab] = useState('rss') // 'rss' | 'github' | 'linkedin'
  const [rssUrls, setRssUrls] = useState('https://dev.to/feed\\nhttps://news.ycombinator.com/rss')
  const [githubRepos, setGithubRepos] = useState('')
  const [linkedInProfiles, setLinkedInProfiles] = useState('')
  const [linkedInLiAt, setLinkedInLiAt] = useState('')
  const [maxAgeDays, setMaxAgeDays] = useState('10')
  const [maxItemsPerFeed, setMaxItemsPerFeed] = useState('5')
  const [loading, setLoading] = useState(false)
  const [candidates, setCandidates] = useState([])
  const [error, setError] = useState('')
  const [scanProgress, setScanProgress] = useState(null)

  const handleDismissCandidate = (candidate) => {
    setCandidates(prev => prev.filter(c => (candidate.url && c.url ? c.url !== candidate.url : c.title !== candidate.title)))
  }

  // LinkedIn Session & Public Bridge State
  const [linkedInStatus, setLinkedInStatus] = useState(null)
  const [syncingLinkedIn, setSyncingLinkedIn] = useState(false)
  const [syncMsg, setSyncMsg] = useState('')

  const fetchLinkedInStatus = async () => {
    try {
      const data = await getLinkedInStatus()
      setLinkedInStatus(data)
    } catch (err) {
      console.error('Failed to fetch LinkedIn status', err)
    }
  }

  const handleSyncLinkedIn = async () => {
    setSyncingLinkedIn(true)
    setSyncMsg('')
    try {
      const data = await syncLinkedIn({ headless: true })
      setSyncMsg(data.message || (data.success ? 'Session synced successfully.' : 'Sync finished.'))
      await fetchLinkedInStatus()
    } catch (err) {
      setSyncMsg('Sync error: ' + err.message)
    } finally {
      setSyncingLinkedIn(false)
    }
  }

  useEffect(() => {
    fetchLinkedInStatus()
  }, [])

  // Feed Archive State
  const [archiveItems, setArchiveItems] = useState([])
  const [archiveTotal, setArchiveTotal] = useState(0)
  const [archiveLoading, setArchiveLoading] = useState(false)
  const [archiveTopic, setArchiveTopic] = useState('All')
  const [archiveVerdict, setArchiveVerdict] = useState('All')
  const [archiveSearch, setArchiveSearch] = useState('')
  const [availableTopics, setAvailableTopics] = useState(DEFAULT_AVAILABLE_TOPICS)

  const fetchArchive = async () => {
    setArchiveLoading(true)
    try {
      const params = {}
      if (archiveTopic && archiveTopic !== 'All') params.topic = archiveTopic
      if (archiveVerdict && archiveVerdict !== 'All') params.verdict = archiveVerdict
      if (archiveSearch.trim()) params.search = archiveSearch.trim()
      const data = await getOracleHistory(params)
      setArchiveItems(data.items || [])
      setArchiveTotal(data.total || 0)
      if (data.topics && data.topics.length > 0) {
        setAvailableTopics(['All', ...data.topics])
      }
    } catch (e) {
      console.error('Failed to fetch oracle history', e)
    } finally {
      setArchiveLoading(false)
    }
  }

  useEffect(() => {
    fetchArchive()
  }, [archiveTopic, archiveVerdict, archiveSearch])

  const rssCount = rssUrls.split('\\n').map(s => s.trim()).filter(Boolean).length
  const ghCount = githubRepos.split('\\n').map(s => s.trim()).filter(Boolean).length
  const liCount = linkedInProfiles.split('\\n').map(s => s.trim()).filter(Boolean).length
  const totalSources = rssCount + ghCount + liCount

  const handleRun = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    setCandidates([])

    const rssList = rssUrls.split('\\n').map(s => s.trim()).filter(Boolean)
    const ghList = githubRepos.split('\\n').map(s => s.trim()).filter(Boolean)
    const liProfiles = linkedInProfiles.split('\\n').map(s => s.trim()).filter(Boolean)

    if (rssList.length === 0 && ghList.length === 0 && liProfiles.length === 0 && !linkedInLiAt.trim()) {
      setError('Please provide at least one source (RSS, GitHub, or LinkedIn).')
      setLoading(false)
      return
    }

    setScanProgress({
      phase: 'fetching',
      message: 'Initializing signal stream across registered sources...',
      sourcesFetched: 0,
      sourcesTotal: totalSources,
      cachedSkipped: 0,
      newSignals: 0,
      current: 0,
      total: 0,
      currentItemTitle: '',
      passed: 0,
      elapsedSec: 0,
    })

    const dispatchSSE = (eventName, data) => {
      if (!eventName || !data) return
      if (eventName === 'phase') {
        setScanProgress(prev => ({
          ...(prev || {}),
          phase: data.phase || prev?.phase || 'fetching',
          message: data.message || prev?.message || '',
        }))
      } else if (eventName === 'source_fetched') {
        setScanProgress(prev => ({
          ...(prev || {}),
          sourcesFetched: (prev?.sourcesFetched || 0) + 1,
          message: `Fetched source: ${data.source}`,
        }))
      } else if (eventName === 'dedup') {
        setScanProgress(prev => ({
          ...(prev || {}),
          phase: 'deduplicating',
          cachedSkipped: data.cached_skipped ?? prev?.cachedSkipped ?? 0,
          newSignals: data.new_signals ?? prev?.newSignals ?? 0,
          message: data.message || `Zero token waste: ${data.cached_skipped ?? 0} cached posts skipped`,
        }))
      } else if (eventName === 'scoring_progress') {
        setScanProgress(prev => ({
          ...(prev || {}),
          phase: 'scoring',
          current: data.current ?? prev?.current ?? 0,
          total: data.total ?? prev?.total ?? 0,
          currentItemTitle: data.item_title || prev?.currentItemTitle || '',
          message: data.item_title ? `Evaluating: ${data.item_title}` : 'Evaluating signals consensus...',
        }))
      } else if (eventName === 'candidate') {
        if (data.candidate) {
          setCandidates(prev => [...prev, data.candidate])
          if (data.candidate.verdict !== 'reject') {
            setScanProgress(prev => ({
              ...(prev || {}),
              passed: (prev?.passed || 0) + 1,
            }))
          }
        }
      } else if (eventName === 'complete') {
        setScanProgress(prev => ({
          ...(prev || {}),
          phase: 'complete',
          total: data.total_scanned ?? prev?.total ?? 0,
          cachedSkipped: data.cached_skipped ?? prev?.cachedSkipped ?? 0,
          passed: data.passed ?? prev?.passed ?? 0,
          elapsedSec: data.elapsed_sec ?? 0,
          message: `Scan complete: ${data.passed ?? 0} passed from ${data.total_scanned ?? 0} scanned in ${data.elapsed_sec ?? 0}s`,
        }))
        setLoading(false)
        fetchArchive()
      }
    }

    const payload = {
      rss_urls: rssList,
      github_repos: ghList,
      linkedin_profiles: liProfiles,
      linkedin_li_at: linkedInLiAt.trim() || undefined,
      max_age_days: maxAgeDays ? parseInt(maxAgeDays, 10) : undefined,
      max_items_per_feed: maxItemsPerFeed ? parseInt(maxItemsPerFeed, 10) : 5,
      limit: 15,
      no_persist: false,
    }

    try {
      await runOracleScan(payload, dispatchSSE)
      fetchArchive()
    } catch (err) {
      setError(err.message || 'Failed to scan and score ideas.')
      setScanProgress(prev => prev ? ({ ...prev, phase: 'error', message: err.message }) : null)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Header & View Switcher */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#e3dacc] pb-5">
        <div>
          <h2 className="font-serif text-2xl font-medium tracking-tight text-[#141413]">The Oracle</h2>
          <p className="text-sm text-[#87867f] mt-1 font-sans">
            Discover, filter, and score engineering topics from your feeds.
          </p>
        </div>

        {/* View Switcher Tabs */}
        <div className="flex items-center gap-1 bg-[#f0eee6] p-1 rounded-full border border-[#e3dacc] shrink-0 self-start sm:self-auto shadow-anthropic">
          <button
            type="button"
            onClick={() => setOracleView('active')}
            className={`flex items-center gap-2 px-4 py-1.5 rounded-full text-xs font-medium transition ${
              oracleView === 'active'
                ? 'bg-[#141413] text-[#faf9f5] shadow-sm'
                : 'text-[#87867f] hover:text-[#141413] hover:bg-[#e3dacc]/50'
            }`}
          >
            <Compass className="w-3.5 h-3.5" />
            <span>Active Scanner</span>
          </button>
          <button
            type="button"
            onClick={() => {
              setOracleView('archive')
              fetchArchive()
            }}
            className={`flex items-center gap-2 px-4 py-1.5 rounded-full text-xs font-medium transition ${
              oracleView === 'archive'
                ? 'bg-[#141413] text-[#faf9f5] shadow-sm'
                : 'text-[#87867f] hover:text-[#141413] hover:bg-[#e3dacc]/50'
            }`}
          >
            <Database className="w-3.5 h-3.5" />
            <span>Feed Archive ({archiveTotal})</span>
          </button>
        </div>
      </div>

      {/* Sub-View 1: Active Scanner */}
      {oracleView === 'active' && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 items-start">
          <SourceCockpit
            sourceSubTab={sourceSubTab}
            onSubTabChange={setSourceSubTab}
            rssUrls={rssUrls}
            setRssUrls={setRssUrls}
            githubRepos={githubRepos}
            setGithubRepos={setGithubRepos}
            linkedInProfiles={linkedInProfiles}
            setLinkedInProfiles={setLinkedInProfiles}
            linkedInLiAt={linkedInLiAt}
            setLinkedInLiAt={setLinkedInLiAt}
            maxAgeDays={maxAgeDays}
            setMaxAgeDays={setMaxAgeDays}
            maxItemsPerFeed={maxItemsPerFeed}
            setMaxItemsPerFeed={setMaxItemsPerFeed}
            rssCount={rssCount}
            ghCount={ghCount}
            liCount={liCount}
            totalSources={totalSources}
            onRun={handleRun}
            loading={loading}
            error={error}
            linkedInStatus={linkedInStatus}
            syncingLinkedIn={syncingLinkedIn}
            syncMsg={syncMsg}
            onSyncLinkedIn={handleSyncLinkedIn}
          />

          <CandidateStream
            candidates={candidates}
            loading={loading}
            scanProgress={scanProgress}
            onDismissScanProgress={() => setScanProgress(null)}
            onSendToCouncil={onSendToCouncil}
            onOpenInterview={(c) => setSelectedInterviewItem(c)}
            onDismissCandidate={handleDismissCandidate}
          />
        </div>
      )}

      {/* Sub-View 2: Feed Archive & Topic Explorer */}
      {oracleView === 'archive' && (
        <ArchiveView
          archiveSearch={archiveSearch}
          setArchiveSearch={setArchiveSearch}
          archiveVerdict={archiveVerdict}
          setArchiveVerdict={setArchiveVerdict}
          archiveTopic={archiveTopic}
          setArchiveTopic={setArchiveTopic}
          availableTopics={availableTopics}
          archiveItems={archiveItems}
          archiveTotal={archiveTotal}
          archiveLoading={archiveLoading}
          fetchArchive={fetchArchive}
          onOpenInterview={(item) => setSelectedInterviewItem(item)}
        />
      )}

      {/* Topic Briefing & Perspective Intake Modal (Subsystem 2) */}
      {selectedInterviewItem && (
        <InterviewModal
          item={selectedInterviewItem}
          onClose={() => setSelectedInterviewItem(null)}
          onSynthesizeComplete={(draft, slug) => {
            setSelectedInterviewItem(null)
            if (onSendToCouncilWithDraft) {
              onSendToCouncilWithDraft(draft, slug)
            } else {
              onSendToCouncil({ title: slug })
            }
          }}
          onSkipToCouncil={(item) => {
            setSelectedInterviewItem(null)
            onSendToCouncil(item)
          }}
        />
      )}
    </div>
  )
}
