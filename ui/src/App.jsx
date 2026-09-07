import React, { useState, useEffect, useRef } from 'react'
import { 
  Compass, 
  Users, 
  BookOpen, 
  Mic, 
  ArrowRight, 
  CheckCircle2, 
  AlertCircle, 
  XCircle, 
  ExternalLink, 
  RotateCw, 
  Sparkles,
  Layers,
  ChevronRight,
  ShieldAlert,
  ShieldCheck,
  Zap,
  FileText,
  Share2,
  Copy,
  Check,
  History,
  Trophy,
  Clock,
  Sliders,
  Settings,
  X,
  Search,
  Filter,
  Tag,
  Database,
  Globe,
  Flame,
  MessageSquare,
  ChevronDown,
  ChevronUp,
  User,
  Save,
  Plus
} from 'lucide-react'
import { getTopicBadgeClass, formatTopicLabel } from './lib/topics'
import { DIMENSION_LABELS, HUMANIZE_TONES, DISTRIBUTION_FORMATS, CORE_VOICE_INVARIANTS } from './lib/constants'
import { useServerHealth } from './app/useServerHealth'
import { runOracleScan, getOracleHistory } from './api/oracle'
import { getLinkedInStatus, syncLinkedIn } from './api/linkedin'
import CandidateCard from './components/oracle/CandidateCard'
import ScanProgressHUD from './components/oracle/ScanProgressHUD'
import InterviewModal from './components/oracle/InterviewModal'
import TabBtn from './components/ui/TabBtn'
import ProfileTab from './components/profile/ProfileTab'
import CommentingTab from './components/commenting/CommentingTab'
import AudioTab from './components/audio/AudioTab'
import LessonsTab from './components/lessons/LessonsTab'
import DistributeTab from './components/distribute/DistributeTab'
import CouncilTab from './components/council/CouncilTab'

export default function App() {
  const [activeTab, setActiveTab] = useState('oracle')
  const serverOnline = useServerHealth()

  // Shared state between Oracle, Council, and Distribute
  const [councilDraft, setCouncilDraft] = useState('')
  const [councilSpikeId, setCouncilSpikeId] = useState('spike-1')
  const [distributeText, setDistributeText] = useState('')
  const [distributeSlug, setDistributeSlug] = useState('post-1')

  const handleSendToCouncil = (item) => {
    setCouncilSpikeId(item.title.toLowerCase().replace(/[^a-z0-9]+/g, '-').slice(0, 30))
    const snippetBlock = item.body_snippet ? `> ${item.body_snippet}\n\n` : ''
    setCouncilDraft(`# ${item.title}\n\n${item.url ? `Source: ${item.url}\n\n` : ''}${snippetBlock}Draft content goes here...`)
    setActiveTab('council')
  }

  const handleSendToCouncilWithDraft = (draftText, slug) => {
    setCouncilSpikeId(slug || 'spike-1')
    setCouncilDraft(draftText)
    setActiveTab('council')
  }

  const handleSendToDistribute = (text, slug) => {
    setDistributeText(text)
    setDistributeSlug(slug || 'published-post')
    setActiveTab('distribute')
  }

  return (
    <div className="min-h-screen w-full bg-[#faf9f5] text-[#141413] flex flex-col font-sans selection:bg-[#c6613f]/20 selection:text-[#c6613f]">
      {/* Minimalist Editorial Navigation Header */}
      <header className="border-b border-[#e3dacc]/70 bg-[#faf9f5]/85 backdrop-blur-md sticky top-0 z-40 transition-colors w-full">
        <div className="max-w-7xl w-full mx-auto px-6 h-14 flex items-center justify-between">
          {/* Brand Logo & Title */}
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg flex items-center justify-center shrink-0">
              <svg width="24" height="24" viewBox="0 0 48 48" fill="none" className="shrink-0" aria-hidden="true">
                <rect x="6" y="16" width="24" height="24" rx="6" stroke="#141413" strokeWidth="2.5" />
                <rect x="18" y="8" width="24" height="24" rx="6" fill="#141413" />
              </svg>
            </div>
            <span className="font-serif font-semibold tracking-tight text-base text-[#141413]">
              Content Machine
            </span>
          </div>

          {/* Minimalist Navigation Bar */}
          <nav className="flex items-center gap-1 sm:gap-1.5" aria-label="Main Navigation">
            <TabBtn active={activeTab === 'oracle'} onClick={() => setActiveTab('oracle')} label="Oracle" />
            <TabBtn active={activeTab === 'council'} onClick={() => setActiveTab('council')} label="Council" />
            <TabBtn active={activeTab === 'distribute'} onClick={() => setActiveTab('distribute')} label="Distribute" />
            <TabBtn active={activeTab === 'lessons'} onClick={() => setActiveTab('lessons')} label="Lessons" />
            <TabBtn active={activeTab === 'audio'} onClick={() => setActiveTab('audio')} label="Audio" />
            <TabBtn active={activeTab === 'commenting'} onClick={() => setActiveTab('commenting')} label="Comments" />
            <TabBtn active={activeTab === 'profile'} onClick={() => setActiveTab('profile')} label="Profile" />
          </nav>

          {/* Minimal Live Status */}
          <div className="flex items-center gap-1.5 text-xs text-[#87867f] font-mono">
            <span className={`w-2 h-2 rounded-full ${serverOnline ? 'bg-emerald-600' : 'bg-[#c6613f]'}`} />
            <span className="text-[11px] hidden sm:inline">{serverOnline ? 'Online' : 'Offline'}</span>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-6 py-8">
        {activeTab === 'oracle' && (
          <OracleTab 
            onSendToCouncil={handleSendToCouncil} 
            onSendToCouncilWithDraft={handleSendToCouncilWithDraft} 
          />
        )}
        {activeTab === 'council' && (
          <CouncilTab 
            draft={councilDraft} 
            setDraft={setCouncilDraft} 
            spikeId={councilSpikeId} 
            setSpikeId={setCouncilSpikeId}
            onSendToDistribute={handleSendToDistribute}
          />
        )}
        {activeTab === 'distribute' && (
          <DistributeTab 
            initialText={distributeText} 
            initialSlug={distributeSlug} 
          />
        )}
        {activeTab === 'profile' && <ProfileTab />}
        {activeTab === 'commenting' && <CommentingTab />}
        {activeTab === 'lessons' && <LessonsTab />}
        {activeTab === 'audio' && <AudioTab />}
      </main>

      {/* Editorial Footer */}
      <footer className="border-t border-[#e3dacc]/60 py-6 text-center text-xs text-[#87867f] font-sans w-full bg-[#faf9f5]">
        <p>Content Machine</p>
      </footer>
    </div>
  )
}


// ==========================================
// 1. ORACLE TAB (Ingestion & Idea Scoring)
// ==========================================

function OracleTab({ onSendToCouncil, onSendToCouncilWithDraft }) {
  const [selectedInterviewItem, setSelectedInterviewItem] = useState(null)
  const [oracleView, setOracleView] = useState('active') // 'active' | 'archive'
  const [sourceSubTab, setSourceSubTab] = useState('rss') // 'rss' | 'github' | 'linkedin'
  const [rssUrls, setRssUrls] = useState('https://dev.to/feed\nhttps://news.ycombinator.com/rss')
  const [githubRepos, setGithubRepos] = useState('')
  const [linkedInProfiles, setLinkedInProfiles] = useState('')
  const [linkedInLiAt, setLinkedInLiAt] = useState('')
  const [maxAgeDays, setMaxAgeDays] = useState('10')
  const [maxItemsPerFeed, setMaxItemsPerFeed] = useState('5')
  const [loading, setLoading] = useState(false)
  const [candidates, setCandidates] = useState([])
  const [error, setError] = useState('')
  const [scanProgress, setScanProgress] = useState(null)

  useEffect(() => {
    window.__CM_SET_CANDIDATES__ = setCandidates
  }, [])

  // Active Batch Toolbar & Triage State
  const [batchSearch, setBatchSearch] = useState('')
  const [batchSort, setBatchSort] = useState('score') // 'score' | 'recency'
  const [batchTopic, setBatchTopic] = useState('All')

  const handleDismissCandidate = (candidate) => {
    setCandidates(prev => prev.filter(c => (candidate.url && c.url ? c.url !== candidate.url : c.title !== candidate.title)))
  }

  // Derive unique active batch topics from current candidates
  const batchTopics = ['All', ...Array.from(new Set(candidates.map(c => c.topic_tag).filter(Boolean)))]

  // Live filter and sort candidates in the active batch
  const filteredCandidates = candidates.filter((item) => {
    if (batchTopic !== 'All' && item.topic_tag !== batchTopic) {
      return false
    }
    if (batchSearch.trim()) {
      const q = batchSearch.trim().toLowerCase()
      const inTitle = (item.title || '').toLowerCase().includes(q)
      const inSource = (item.source || '').toLowerCase().includes(q)
      const inSnippet = (item.body_snippet || '').toLowerCase().includes(q)
      const inTopic = (item.topic_tag || '').toLowerCase().includes(q)
      if (!inTitle && !inSource && !inSnippet && !inTopic) return false
    }
    return true
  }).sort((a, b) => {
    if (batchSort === 'score') {
      const scoreA = typeof a.score === 'number' ? a.score : 0
      const scoreB = typeof b.score === 'number' ? b.score : 0
      return scoreB - scoreA
    } else if (batchSort === 'recency') {
      const dateA = a.published_at ? new Date(a.published_at).getTime() : 0
      const dateB = b.published_at ? new Date(b.published_at).getTime() : 0
      return dateB - dateA
    }
    return 0
  })

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

  const linkedInPresets = [
    { label: 'Satya Nadella', handle: 'in/satyanadella' },
    { label: 'Cloudflare', handle: 'company/cloudflare' },
    { label: 'Netflix Tech', handle: 'company/netflix' },
    { label: 'Sam Altman', handle: 'in/samaltman' },
  ]

  const handleAddLinkedInPreset = (handle) => {
    const current = linkedInProfiles.split('\n').map(s => s.trim()).filter(Boolean)
    if (!current.includes(handle)) {
      setLinkedInProfiles(prev => prev.trim() ? `${prev.trim()}\n${handle}` : handle)
    }
  }

  // Feed Archive State
  const [archiveItems, setArchiveItems] = useState([])
  const [archiveTotal, setArchiveTotal] = useState(0)
  const [archiveLoading, setArchiveLoading] = useState(false)
  const [archiveTopic, setArchiveTopic] = useState('All')
  const [archiveVerdict, setArchiveVerdict] = useState('All')
  const [archiveSearch, setArchiveSearch] = useState('')
  const [availableTopics, setAvailableTopics] = useState([
    'All',
    '⚡ Systems & Architecture',
    '📈 Engineering Leadership',
    '🤖 AI & Machine Learning',
    '☁️ Cloud & Infrastructure',
    '🔒 Security & Reliability',
    '🛠️ Developer Productivity',
    '💻 General Engineering',
  ])

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

  const devFeedPresets = [
    { label: 'dev.to', url: 'https://dev.to/feed' },
    { label: 'Hacker News', url: 'https://news.ycombinator.com/rss' },
    { label: 'Lobsters', url: 'https://lobste.rs/rss' },
    { label: 'GitHub Blog', url: 'https://github.blog/feed/' },
    { label: 'freeCodeCamp', url: 'https://www.freecodecamp.org/news/rss/' },
  ]

  const companyBlogPresets = [
    { label: 'Cloudflare', url: 'https://blog.cloudflare.com/rss/' },
    { label: 'Netflix Tech', url: 'https://netflixtechblog.com/feed' },
    { label: 'Stripe', url: 'https://stripe.com/blog/feed.rss' },
    { label: 'Spotify Eng', url: 'https://engineering.atspotify.com/feed/' },
    { label: 'Dropbox Tech', url: 'https://dropbox.tech/feed' },
  ]

  const newsletterPresets = [
    { label: 'Pragmatic Eng', url: 'https://newsletter.pragmaticengineer.com/feed' },
    { label: 'ByteByteGo', url: 'https://blog.bytebytego.com/feed' },
    { label: 'Refactoring', url: 'https://refactoring.fm/feed' },
    { label: 'Developing Dev', url: 'https://www.developing.dev/feed' },
    { label: 'Tidy First', url: 'https://tidyfirst.substack.com/feed' },
    { label: 'Latent Space', url: 'https://www.latent.space/feed' },
  ]

  const podcastPresets = [
    { label: 'Changelog', url: 'https://changelog.com/podcast/feed' },
  ]

  const redditPresets = [
    { label: 'r/ExperiencedDevs', url: 'https://www.reddit.com/r/ExperiencedDevs/top/.rss?t=week' },
    { label: 'r/LocalLLaMA', url: 'https://www.reddit.com/r/LocalLLaMA/top/.rss?t=week' },
    { label: 'r/systemdesign', url: 'https://www.reddit.com/r/systemdesign/top/.rss?t=week' },
  ]

  const industryRadarPresets = [
    { label: 'Techmeme', url: 'https://www.techmeme.com/feed.xml' },
  ]

  const viralRadarAllUrls = [
    'https://blog.bytebytego.com/feed',
    'https://newsletter.pragmaticengineer.com/feed',
    'https://www.latent.space/feed',
    'https://refactoring.fm/feed',
    'https://www.developing.dev/feed',
    'https://www.reddit.com/r/ExperiencedDevs/top/.rss?t=week',
    'https://www.reddit.com/r/LocalLLaMA/top/.rss?t=week',
    'https://www.techmeme.com/feed.xml',
  ]

  const handleLoadViralRadar = () => {
    setRssUrls(viralRadarAllUrls.join('\n'))
  }

  const handleAddPreset = (url) => {
    const current = rssUrls.split('\n').map(s => s.trim()).filter(Boolean)
    if (!current.includes(url)) {
      setRssUrls(prev => prev.trim() ? `${prev.trim()}\n${url}` : url)
    }
  }

  const githubPresets = [
    { label: 'facebook/react', repo: 'facebook/react' },
    { label: 'rust-lang/rust', repo: 'rust-lang/rust' },
    { label: 'tokio-rs/tokio', repo: 'tokio-rs/tokio' },
    { label: 'anthropics/anthropic-sdk-python', repo: 'anthropics/anthropic-sdk-python' },
  ]

  const handleAddGithubPreset = (repo) => {
    const current = githubRepos.split('\n').map(s => s.trim()).filter(Boolean)
    if (!current.includes(repo)) {
      setGithubRepos(prev => prev.trim() ? `${prev.trim()}\n${repo}` : repo)
    }
  }

  const rssCount = rssUrls.split('\n').map(s => s.trim()).filter(Boolean).length
  const ghCount = githubRepos.split('\n').map(s => s.trim()).filter(Boolean).length
  const liCount = linkedInProfiles.split('\n').map(s => s.trim()).filter(Boolean).length
  const totalSources = rssCount + ghCount + liCount

  const handleRun = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    setCandidates([])

    const rssList = rssUrls.split('\n').map(s => s.trim()).filter(Boolean)
    const ghList = githubRepos.split('\n').map(s => s.trim()).filter(Boolean)
    const liProfiles = linkedInProfiles.split('\n').map(s => s.trim()).filter(Boolean)

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
          {/* Modular Tabbed Source Cockpit */}
          <form 
            onSubmit={handleRun} 
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
                  onClick={() => setSourceSubTab('rss')}
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
                  onClick={() => setSourceSubTab('github')}
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
                  onClick={() => setSourceSubTab('linkedin')}
                  title="LinkedIn Engine"
                  className={`py-1.5 px-2 rounded-lg text-xs font-medium transition flex items-center justify-center gap-1.5 ${
                    sourceSubTab === 'linkedin'
                      ? 'bg-[#141413] text-[#faf9f5] shadow-xs'
                      : 'text-[#87867f] hover:text-[#141413] hover:bg-[#e3dacc]/40'
                  }`}
                >
                  <span className="truncate">LinkedIn Engine</span>
                  <span className={`font-mono text-[10px] px-1.5 py-0.2 rounded-full ${
                    sourceSubTab === 'linkedin' ? 'bg-[#2a2a28] text-[#faf9f5]' : 'bg-[#f0eee6] text-[#87867f]'
                  }`}>
                    {liCount}
                  </span>
                </button>
              </div>
            </div>

            {/* Scrollable Middle Tab Panes */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 min-h-[200px]">
              {/* Tab 1: RSS Feeds */}
              {sourceSubTab === 'rss' && (
                <div className="space-y-3 animate-fadeIn">
                  {/* 1-Click Top Viral Tech Radar Button */}
                  <button
                    type="button"
                    onClick={handleLoadViralRadar}
                    className="w-full py-2 px-3 rounded-xl bg-gradient-to-r from-[#c6613f] to-[#d97757] hover:from-[#b55535] hover:to-[#c6613f] text-[#faf9f5] text-xs font-medium flex items-center justify-center gap-2 shadow-xs transition duration-150 group"
                    title="Populate top viral newsletters, Reddit communities, and Techmeme"
                  >
                    <Flame className="w-3.5 h-3.5 text-[#faf9f5] group-hover:scale-110 transition-transform" />
                    <span>🔥 Load Viral Tech Radar (8 Signals)</span>
                  </button>

                  <div className="flex items-center justify-between">
                    <label className="block text-xs font-medium text-[#141413]">RSS / Atom Feeds</label>
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-mono text-[#87867f]">{rssCount} configured</span>
                      {rssCount > 0 && (
                        <button
                          type="button"
                          onClick={() => setRssUrls('')}
                          className="text-[10px] font-mono text-[#c6613f] hover:underline"
                        >
                          Clear
                        </button>
                      )}
                    </div>
                  </div>
                  <textarea
                    rows={4}
                    value={rssUrls}
                    onChange={(e) => setRssUrls(e.target.value)}
                    placeholder="https://example.com/feed.xml"
                    className="w-full text-xs font-mono bg-[#faf9f5] border border-[#e3dacc] rounded-xl p-3 text-[#141413] focus:outline-none focus:border-[#141413] focus:ring-1 focus:ring-[#141413] placeholder-[#b0aea5]"
                  />

                  {/* Quick Presets */}
                  <div className="space-y-2 pt-1">
                    <div>
                      <span className="text-[10px] text-[#87867f] font-mono block mb-1">Reddit Communities:</span>
                      <div className="flex flex-wrap gap-1.5">
                        {redditPresets.map((preset) => (
                          <button
                            key={preset.url}
                            type="button"
                            onClick={() => handleAddPreset(preset.url)}
                            className="text-[10px] font-mono px-2.5 py-0.5 rounded-full bg-[#faf9f5] hover:bg-[#141413] text-[#141413] hover:text-[#faf9f5] border border-[#e3dacc] transition duration-150"
                            title={`Add ${preset.url}`}
                          >
                            + {preset.label}
                          </button>
                        ))}
                      </div>
                    </div>
                    <div>
                      <span className="text-[10px] text-[#87867f] font-mono block mb-1">Top Newsletters:</span>
                      <div className="flex flex-wrap gap-1.5">
                        {newsletterPresets.map((preset) => (
                          <button
                            key={preset.url}
                            type="button"
                            onClick={() => handleAddPreset(preset.url)}
                            className="text-[10px] font-mono px-2.5 py-0.5 rounded-full bg-[#faf9f5] hover:bg-[#141413] text-[#141413] hover:text-[#faf9f5] border border-[#e3dacc] transition duration-150"
                            title={`Add ${preset.url}`}
                          >
                            + {preset.label}
                          </button>
                        ))}
                      </div>
                    </div>
                    <div>
                      <span className="text-[10px] text-[#87867f] font-mono block mb-1">Dev Community:</span>
                      <div className="flex flex-wrap gap-1.5">
                        {devFeedPresets.map((preset) => (
                          <button
                            key={preset.url}
                            type="button"
                            onClick={() => handleAddPreset(preset.url)}
                            className="text-[10px] font-mono px-2.5 py-0.5 rounded-full bg-[#faf9f5] hover:bg-[#141413] text-[#141413] hover:text-[#faf9f5] border border-[#e3dacc] transition duration-150"
                            title={`Add ${preset.url}`}
                          >
                            + {preset.label}
                          </button>
                        ))}
                      </div>
                    </div>
                    <div>
                      <span className="text-[10px] text-[#87867f] font-mono block mb-1">Company TechBlogs:</span>
                      <div className="flex flex-wrap gap-1.5">
                        {companyBlogPresets.map((preset) => (
                          <button
                            key={preset.url}
                            type="button"
                            onClick={() => handleAddPreset(preset.url)}
                            className="text-[10px] font-mono px-2.5 py-0.5 rounded-full bg-[#faf9f5] hover:bg-[#141413] text-[#141413] hover:text-[#faf9f5] border border-[#e3dacc] transition duration-150"
                            title={`Add ${preset.url}`}
                          >
                            + {preset.label}
                          </button>
                        ))}
                      </div>
                    </div>
                    <div>
                      <span className="text-[10px] text-[#87867f] font-mono block mb-1">Industry Radar:</span>
                      <div className="flex flex-wrap gap-1.5">
                        {industryRadarPresets.map((preset) => (
                          <button
                            key={preset.url}
                            type="button"
                            onClick={() => handleAddPreset(preset.url)}
                            className="text-[10px] font-mono px-2.5 py-0.5 rounded-full bg-[#faf9f5] hover:bg-[#141413] text-[#141413] hover:text-[#faf9f5] border border-[#e3dacc] transition duration-150"
                            title={`Add ${preset.url}`}
                          >
                            + {preset.label}
                          </button>
                        ))}
                      </div>
                    </div>
                    <div>
                      <span className="text-[10px] text-[#87867f] font-mono block mb-1">Podcasts:</span>
                      <div className="flex flex-wrap gap-1.5">
                        {podcastPresets.map((preset) => (
                          <button
                            key={preset.url}
                            type="button"
                            onClick={() => handleAddPreset(preset.url)}
                            className="text-[10px] font-mono px-2.5 py-0.5 rounded-full bg-[#faf9f5] hover:bg-[#141413] text-[#141413] hover:text-[#faf9f5] border border-[#e3dacc] transition duration-150"
                            title={`Add ${preset.url}`}
                          >
                            + {preset.label}
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Tab 2: GitHub Releases */}
              {sourceSubTab === 'github' && (
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
                          onClick={() => handleAddGithubPreset(p.repo)}
                          className="text-[10px] font-mono px-2.5 py-0.5 rounded-full bg-[#faf9f5] hover:bg-[#141413] text-[#141413] hover:text-[#faf9f5] border border-[#e3dacc] transition duration-150"
                          title={`Add ${p.repo}`}
                        >
                          + {p.label}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* Tab 3: LinkedIn Engine */}
              {sourceSubTab === 'linkedin' && (
                <div className="space-y-3 animate-fadeIn">
                  <div className="flex items-center justify-between">
                    <label className="block text-xs font-medium text-[#141413]">LinkedIn Engine</label>
                    {linkedInStatus?.session_valid ? (
                      <span className="flex items-center gap-1 text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
                        Active Session
                      </span>
                    ) : (
                      <span className="flex items-center gap-1 text-[10px] font-mono px-2 py-0.5 rounded-full bg-sky-50 text-sky-700 border border-sky-200">
                        <Globe className="w-2.5 h-2.5" />
                        Public Bridge Mode
                      </span>
                    )}
                  </div>

                  <p className="text-[11px] text-[#87867f] leading-tight">
                    {linkedInStatus?.session_valid
                      ? "Authenticated session active. Pulls home feed and full creator updates."
                      : "Zero-auth public bridge active. Ingests public creator and company posts without login."}
                  </p>

                  {/* Creator & Company Handles */}
                  <div>
                    <label className="block text-[10px] font-mono text-[#87867f] mb-1">
                      Target Handles (in/slug or company/slug):
                    </label>
                    <textarea
                      rows={3}
                      value={linkedInProfiles}
                      onChange={(e) => setLinkedInProfiles(e.target.value)}
                      placeholder="satyanadella&#10;company/cloudflare"
                      className="w-full text-xs font-mono bg-[#faf9f5] border border-[#e3dacc] rounded-xl p-2.5 text-[#141413] focus:outline-none focus:border-[#141413] focus:ring-1 focus:ring-[#141413] placeholder-[#b0aea5]"
                    />
                  </div>

                  {/* Quick Add Presets */}
                  <div className="space-y-1">
                    <span className="text-[10px] text-[#87867f] font-mono block">Creator Presets:</span>
                    <div className="flex flex-wrap gap-1.5">
                      {linkedInPresets.map((p) => (
                        <button
                          key={p.handle}
                          type="button"
                          onClick={() => handleAddLinkedInPreset(p.handle)}
                          className="text-[10px] font-mono px-2.5 py-0.5 rounded-full bg-[#faf9f5] hover:bg-[#141413] text-[#141413] hover:text-[#faf9f5] border border-[#e3dacc] transition duration-150"
                        >
                          + {p.label}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Auto-Sync Session Action */}
                  <div className="pt-2 border-t border-[#e3dacc]/60 flex items-center justify-between gap-2">
                    <button
                      type="button"
                      onClick={handleSyncLinkedIn}
                      disabled={syncingLinkedIn}
                      className="flex items-center gap-1.5 text-[11px] font-sans px-3 py-1.5 rounded-xl bg-[#faf9f5] hover:bg-[#e3dacc]/70 border border-[#e3dacc] text-[#141413] transition disabled:opacity-50"
                      title="Auto-extract session from local Playwright persistent browser context"
                    >
                      <RotateCw className={`w-3 h-3 ${syncingLinkedIn ? 'animate-spin' : ''}`} />
                      <span>{syncingLinkedIn ? 'Syncing...' : 'Auto-Sync Session'}</span>
                    </button>

                    <span className="text-[10px] text-[#87867f] font-mono truncate max-w-[140px]">
                      {linkedInStatus?.saved_at ? `Synced ${new Date(linkedInStatus.saved_at).toLocaleDateString()}` : 'No session'}
                    </span>
                  </div>

                  {syncMsg && (
                    <p className="text-[10px] font-mono text-[#c6613f] bg-[#f0eee6] p-1.5 rounded-lg border border-[#e3dacc]">
                      {syncMsg}
                    </p>
                  )}

                  {/* Optional Manual li_at Override */}
                  <details className="group pt-1">
                    <summary className="text-[10px] font-mono text-[#87867f] cursor-pointer hover:text-[#141413] transition select-none">
                      ▸ Manual li_at Cookie Override
                    </summary>
                    <div className="mt-2 space-y-1">
                      <input
                        type="password"
                        value={linkedInLiAt}
                        onChange={(e) => setLinkedInLiAt(e.target.value)}
                        placeholder="Paste li_at cookie..."
                        className="w-full text-xs font-mono bg-[#faf9f5] border border-[#e3dacc] rounded-xl p-2 text-[#141413] focus:outline-none focus:border-[#141413] placeholder-[#b0aea5]"
                      />
                      <span className="text-[10px] text-[#87867f] block">
                        DevTools &rarr; Application &rarr; Cookies &rarr; <code className="text-[#141413] bg-[#e3dacc]/50 px-1 rounded">li_at</code>
                      </span>
                    </div>
                  </details>
                </div>
              )}
            </div>

            {/* Sticky Footer: Freshness, Limits & Trigger Bar */}
            <div className="p-4 bg-[#f0eee6] border-t border-[#e3dacc] space-y-3 shrink-0">
              {/* Freshness & Limits */}
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

              {/* Summary Badge */}
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

              {/* Primary Trigger Button */}
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

          {/* Results Stream */}
          <div className="md:col-span-2 space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-[#e3dacc]">
              <h3 className="text-xs uppercase font-mono tracking-wider text-[#87867f]">
                Scored Candidates {candidates.length > 0 && filteredCandidates.length !== candidates.length 
                  ? `(${filteredCandidates.length} of ${candidates.length})` 
                  : `(${candidates.length})`}
              </h3>
              <span className="text-[11px] text-[#87867f] font-mono">Gate: 8.0 &bull; Margin: &plusmn;0.5</span>
            </div>

            {/* ScanProgressHUD: 3-Phase Stepper, Zero-Token Badge, Scoring Progress */}
            {(loading || scanProgress) && (
              <ScanProgressHUD
                progress={scanProgress}
                loading={loading}
                onDismiss={() => setScanProgress(null)}
              />
            )}

            {candidates.length === 0 && !loading && !scanProgress && (
              <div className="border border-dashed border-[#b0aea5] rounded-2xl p-12 text-center text-[#87867f] bg-[#f0eee6]/30">
                <Compass className="w-8 h-8 mx-auto mb-3 stroke-1 text-[#b0aea5]" />
                <p className="text-sm font-medium text-[#141413]">No candidates scored in this scan yet.</p>
                <p className="text-xs text-[#87867f] mt-1">Configure sources on the left and trigger a scan, or switch to the Feed Archive tab to browse all past posts.</p>
              </div>
            )}

            {loading && candidates.length === 0 && (
              <div className="border border-dashed border-[#e3dacc] rounded-2xl p-8 text-center text-[#87867f] bg-[#faf9f5]/50 animate-fadeIn">
                <Sparkles className="w-5 h-5 mx-auto mb-2 text-[#d97757] animate-pulse" />
                <p className="text-xs font-serif text-[#141413]">Listening to real-time signal stream...</p>
                <p className="text-[11px] text-[#87867f] mt-0.5">Scored candidates will materialize here dynamically as consensus is reached.</p>
              </div>
            )}

            {!loading && candidates.length === 0 && scanProgress && (
              <div className="border border-dashed border-[#e3dacc] rounded-2xl p-8 text-center text-[#87867f] bg-[#faf9f5]/50 animate-fadeIn">
                <p className="text-xs font-serif text-[#141413]">No signals met the score threshold (≥8.0) in this batch.</p>
                <p className="text-[11px] text-[#87867f] mt-0.5">All items were either deduplicated from SQLite cache or scored below threshold.</p>
              </div>
            )}

            {/* Active Batch Triage Toolbar */}
            {candidates.length > 0 && (
              <div className="bg-[#f0eee6]/60 p-3.5 rounded-2xl border border-[#e3dacc] space-y-3 shadow-anthropic animate-fadeIn">
                {/* Search & Sort Controls Row */}
                <div className="flex flex-col sm:flex-row gap-2.5 items-stretch sm:items-center justify-between">
                  {/* Live Search Input */}
                  <div className="relative flex-1">
                    <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-[#87867f]" />
                    <input
                      type="text"
                      value={batchSearch}
                      onChange={(e) => setBatchSearch(e.target.value)}
                      placeholder="Filter active batch by title, source, or excerpt..."
                      className="w-full pl-9 pr-8 py-1.5 bg-[#faf9f5] border border-[#e3dacc] rounded-full text-xs text-[#141413] placeholder-[#b0aea5] focus:outline-none focus:border-[#141413] transition"
                    />
                    {batchSearch && (
                      <button
                        type="button"
                        onClick={() => setBatchSearch('')}
                        className="absolute right-3 top-2 text-[#87867f] hover:text-[#141413]"
                        title="Clear search"
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>

                  {/* Sort Controls */}
                  <div className="flex items-center gap-1 bg-[#faf9f5] p-1 rounded-full border border-[#e3dacc] shrink-0 shadow-2xs">
                    <span className="text-[10px] font-mono text-[#87867f] px-2 flex items-center gap-1">
                      <Sliders className="w-3 h-3 text-[#b0aea5]" />
                      <span>Sort:</span>
                    </span>
                    <button
                      type="button"
                      onClick={() => setBatchSort('score')}
                      className={`px-3 py-1 rounded-full text-xs font-mono transition ${
                        batchSort === 'score'
                          ? 'bg-[#141413] text-[#faf9f5] font-medium shadow-sm'
                          : 'text-[#87867f] hover:text-[#141413]'
                      }`}
                    >
                      <span>Score &darr;</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => setBatchSort('recency')}
                      className={`px-3 py-1 rounded-full text-xs font-mono transition ${
                        batchSort === 'recency'
                          ? 'bg-[#141413] text-[#faf9f5] font-medium shadow-sm'
                          : 'text-[#87867f] hover:text-[#141413]'
                      }`}
                    >
                      <span>Recency &darr;</span>
                    </button>
                  </div>
                </div>

                {/* Topic Filter Chips */}
                <div className="flex items-center gap-1.5 flex-wrap pt-0.5">
                  <span className="text-[10px] font-mono text-[#87867f] uppercase tracking-wider shrink-0 flex items-center gap-1 mr-1">
                    <Tag className="w-3 h-3 text-[#d97757]" />
                    <span>Topics:</span>
                  </span>
                  {batchTopics.map((topic) => {
                    const active = batchTopic === topic
                    const count = topic === 'All'
                      ? candidates.length
                      : candidates.filter(c => c.topic_tag === topic).length

                    return (
                      <button
                        key={topic}
                        type="button"
                        onClick={() => setBatchTopic(topic)}
                        className={`text-xs px-3 py-1 rounded-full border transition flex items-center gap-1.5 ${
                          active
                            ? 'bg-[#141413] text-[#faf9f5] border-[#141413] shadow-sm font-medium'
                            : 'bg-[#faf9f5] text-[#87867f] border-[#e3dacc] hover:border-[#b0aea5] hover:text-[#141413]'
                        }`}
                      >
                        <span>{formatTopicLabel(topic)}</span>
                        <span className={`text-[10px] px-1.5 py-0.2 rounded-full font-mono ${
                          active ? 'bg-[#2a2a28] text-[#faf9f5]' : 'bg-[#f0eee6] text-[#87867f]'
                        }`}>
                          {count}
                        </span>
                      </button>
                    )
                  })}
                </div>
              </div>
            )}

            {/* Zero Filter Matches State */}
            {candidates.length > 0 && filteredCandidates.length === 0 && (
              <div className="border border-dashed border-[#b0aea5] rounded-2xl p-8 text-center text-[#87867f] bg-[#f0eee6]/30 animate-fadeIn">
                <Search className="w-6 h-6 mx-auto mb-2 text-[#b0aea5]" />
                <p className="text-xs font-medium text-[#141413]">No candidates match the active filters.</p>
                <button
                  type="button"
                  onClick={() => { setBatchSearch(''); setBatchTopic('All'); }}
                  className="text-[11px] text-[#c6613f] hover:underline mt-1.5 inline-block font-mono"
                >
                  Reset batch filters &rarr;
                </button>
              </div>
            )}

            {/* Candidates Card Feed */}
            <div className="space-y-3">
              {filteredCandidates.map((item, idx) => (
                <CandidateCard
                  key={item.url || item.title || idx}
                  candidate={item}
                  onSendToCouncil={onSendToCouncil}
                  onOpenInterview={(c) => setSelectedInterviewItem(c)}
                  onDismiss={handleDismissCandidate}
                />
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Sub-View 2: Feed Archive & Topic Explorer */}
      {oracleView === 'archive' && (
        <div className="space-y-6">
          {/* Search & Filter Bar */}
          <div className="bg-[#f0eee6]/60 p-5 rounded-2xl border border-[#e3dacc] space-y-4 shadow-anthropic">
            <div className="flex flex-col sm:flex-row gap-3">
              <div className="relative flex-1">
                <Search className="w-4 h-4 absolute left-3.5 top-3 text-[#87867f]" />
                <input
                  type="text"
                  value={archiveSearch}
                  onChange={(e) => setArchiveSearch(e.target.value)}
                  placeholder="Search past scanned posts by title or source..."
                  className="w-full pl-10 pr-8 py-2.5 bg-[#faf9f5] border border-[#e3dacc] rounded-full text-xs text-[#141413] placeholder-[#b0aea5] focus:outline-none focus:border-[#141413]"
                />
                {archiveSearch && (
                  <button 
                    onClick={() => setArchiveSearch('')}
                    className="absolute right-3.5 top-3 text-[#87867f] hover:text-[#141413]"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>

              {/* Verdict Filter Buttons */}
              <div className="flex items-center gap-1 bg-[#faf9f5] p-1 rounded-full border border-[#e3dacc] overflow-x-auto shadow-sm">
                {[
                  { key: 'All', label: 'All' },
                  { key: 'pass', label: 'Pass (≥8.0)' },
                  { key: 'review', label: 'Review (7.5-8.0)' },
                  { key: 'reject', label: 'Rejected' },
                ].map((v) => (
                  <button
                    key={v.key}
                    type="button"
                    onClick={() => setArchiveVerdict(v.key)}
                    className={`px-3 py-1 rounded-full text-xs font-mono transition shrink-0 ${
                      archiveVerdict === v.key
                        ? 'bg-[#141413] text-[#faf9f5] font-medium shadow-sm'
                        : 'text-[#87867f] hover:text-[#141413]'
                    }`}
                  >
                    {v.label}
                  </button>
                ))}
              </div>

              {/* Refresh Archive Button */}
              <button
                type="button"
                onClick={fetchArchive}
                className="px-4 py-2 rounded-full bg-[#faf9f5] border border-[#e3dacc] hover:border-[#b0aea5] text-[#141413] text-xs flex items-center gap-1.5 transition shrink-0 self-start sm:self-auto shadow-sm"
                title="Refresh archive"
              >
                <RotateCw className={`w-3.5 h-3.5 ${archiveLoading ? 'animate-spin text-[#c6613f]' : 'text-[#87867f]'}`} />
                <span>Refresh</span>
              </button>
            </div>

            {/* Topic Taxonomy Pills */}
            <div>
              <div className="flex items-center gap-1.5 mb-2.5 text-xs font-medium text-[#87867f]">
                <Tag className="w-3.5 h-3.5 text-[#c6613f]" />
                <span>Filter by Content Topic Taxonomy:</span>
              </div>
              <div className="flex flex-wrap gap-2">
                {availableTopics.map((topic) => {
                  const active = archiveTopic === topic
                  return (
                    <button
                      key={topic}
                      type="button"
                      onClick={() => setArchiveTopic(topic)}
                      className={`text-xs px-3.5 py-1.5 rounded-full border transition flex items-center gap-1.5 ${
                        active
                          ? 'bg-[#141413] text-[#faf9f5] border-[#141413] shadow-sm font-medium'
                          : 'bg-[#faf9f5] text-[#87867f] border-[#e3dacc] hover:border-[#b0aea5] hover:text-[#141413]'
                      }`}
                    >
                      <span>{topic}</span>
                      {topic !== 'All' && (
                        <span className={`text-[10px] px-1.5 py-0.2 rounded-full font-mono ${active ? 'bg-[#252524] text-[#faf9f5]' : 'bg-[#f0eee6] text-[#87867f]'}`}>
                          {archiveItems.filter(i => i.topic_tag === topic).length}
                        </span>
                      )}
                    </button>
                  )
                })}
              </div>
            </div>
          </div>

          {/* Archive Results */}
          {archiveLoading ? (
            <div className="border border-[#e3dacc] rounded-2xl p-12 text-center text-[#87867f] space-y-3 bg-[#f0eee6]/50 shadow-anthropic">
              <RotateCw className="w-6 h-6 mx-auto animate-spin text-[#c6613f]" />
              <p className="text-sm font-medium text-[#141413]">Loading historical feed archive...</p>
            </div>
          ) : archiveItems.length === 0 ? (
            <div className="border border-dashed border-[#b0aea5] rounded-2xl p-12 text-center text-[#87867f] bg-[#f0eee6]/30">
              <Database className="w-8 h-8 mx-auto mb-3 stroke-1 text-[#b0aea5]" />
              <p className="text-sm font-medium text-[#141413]">No historical posts match your filters.</p>
              <p className="text-xs text-[#87867f] mt-1">Try resetting the topic or verdict filter above.</p>
            </div>
          ) : (
            <div className="space-y-3">
              <div className="flex items-center justify-between text-xs text-[#87867f] font-mono px-1">
                <span>Showing {archiveItems.length} of {archiveTotal} historical posts</span>
                <span>Instant retrieval &bull; 0 LLM tokens spent</span>
              </div>
              {archiveItems.map((item) => (
                <div
                  key={item.id}
                  className="bg-[#faf9f5] hover:bg-[#f0eee6]/40 transition border border-[#e3dacc] rounded-2xl p-5 flex flex-col justify-between gap-3 shadow-anthropic"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="space-y-1.5">
                      <h4 className="text-sm font-serif font-medium text-[#141413] leading-snug">{item.title}</h4>
                      <div className="flex items-center gap-2 text-[11px] text-[#87867f] font-mono flex-wrap">
                        <span className={`text-[10px] font-medium px-2.5 py-0.5 rounded-full border ${getTopicBadgeClass(item.topic_tag)}`}>
                          {item.topic_tag}
                        </span>
                        <span>{item.source}</span>
                        <span className="text-[#b0aea5]">&bull;</span>
                        <span className="text-[#87867f]">
                          {new Date(item.created_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                        </span>
                        {item.url && (
                          <>
                            <span className="text-[#b0aea5]">&bull;</span>
                            <a href={item.url} target="_blank" rel="noreferrer" className="hover:text-[#141413] flex items-center gap-1">
                              <span>source</span>
                              <ExternalLink className="w-2.5 h-2.5" />
                            </a>
                          </>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      <span className={`text-xs font-mono font-semibold px-2.5 py-1 rounded-full border ${
                        item.verdict === 'pass'
                          ? 'bg-[#c6613f]/10 text-[#c6613f] border-[#c6613f]/30'
                          : item.verdict === 'review'
                          ? 'bg-[#d97757]/10 text-[#d97757] border-[#d97757]/30'
                          : 'bg-[#f0eee6] text-[#87867f] border-[#e3dacc]'
                      }`}>
                        {typeof item.score === 'number' ? item.score.toFixed(2) : item.score}
                      </span>
                      <span className="text-[10px] uppercase tracking-wider font-mono text-[#87867f]">
                        {item.verdict}
                      </span>
                    </div>
                  </div>

                  <div className="flex justify-end pt-2 border-t border-[#e3dacc]">
                    <button
                      onClick={() => setSelectedInterviewItem({ title: item.title, url: item.url, topic_tag: item.topic_tag })}
                      className="text-xs text-[#c6613f] hover:text-[#a54c2d] font-medium flex items-center gap-1.5 transition"
                    >
                      <Sparkles className="w-3 h-3 text-[#d97757]" />
                      <span>Brief & Perspective</span>
                      <ArrowRight className="w-3 h-3" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
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









