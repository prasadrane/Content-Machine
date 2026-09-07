import React, { useState, useEffect, useRef } from 'react'
import { createPortal } from 'react-dom'
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
import { runCouncil, getCouncilHistory, getCouncilSpikes } from './api/council'
import { runHumanize } from './api/humanize'
import { getLessons, addCustomLesson, diffLessons, approveLesson, rejectLesson } from './api/lessons'
import { runDistribute } from './api/distribute'
import { getBrief, synthesizeDraft } from './api/interview'
import { useCopyToClipboard } from './hooks/useCopyToClipboard'
import { useVoiceRecording } from './hooks/useVoiceRecording'
import TabBtn from './components/ui/TabBtn'
import ProfileTab from './components/profile/ProfileTab'
import CommentingTab from './components/commenting/CommentingTab'
import AudioTab from './components/audio/AudioTab'

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

function InterviewModal({ item, onClose, onSynthesizeComplete, onSkipToCouncil }) {
  const [briefing, setBriefing] = useState(null)
  const [loadingBriefing, setLoadingBriefing] = useState(true)
  const [briefingError, setBriefingError] = useState('')
  const [answers, setAnswers] = useState({})
  const [rawNotes, setRawNotes] = useState('')
  const [synthesizing, setSynthesizing] = useState(false)
  const [synthError, setSynthError] = useState('')

  // Voice Input (Web Speech dictation + backend transcribe fallback) — see hooks/useVoiceRecording
  const {
    startRecording: startVoiceRecording,
    recordingTarget,
    isTranscribing: isTranscribingAudio,
    error: recordingError,
    setError: setRecordingError,
  } = useVoiceRecording({
    onTranscript: (text, target) => {
      if (target === 'raw') {
        setRawNotes((prev) => (prev ? prev.trim() + ' ' + text : text))
      } else {
        setAnswers((prev) => {
          const current = prev[target] || ''
          return {
            ...prev,
            [target]: current ? current.trim() + ' ' + text : text,
          }
        })
      }
    },
  })

  useEffect(() => {
    if (!item) return
    let isMounted = true
    setLoadingBriefing(true)
    setBriefingError('')

    getBrief({
      title: item.title,
      url: item.url || null,
      body: item.body || item.title,
      topic_tag: item.topic_tag || 'General Engineering',
    })
      .then((data) => {
        if (isMounted) {
          setBriefing(data)
          setLoadingBriefing(false)
        }
      })
      .catch((err) => {
        if (isMounted) {
          setBriefingError('Could not load automated briefing. You can still input your perspective.')
          setLoadingBriefing(false)
        }
      })

    return () => {
      isMounted = false
    }
  }, [item])

  const handleSynthesize = async () => {
    setSynthesizing(true)
    setSynthError('')

    const responses = (briefing?.questions || []).map((q, idx) => ({
      persona: q.persona,
      question: q.question,
      answer: answers[idx] || '',
    })).filter((r) => r.answer.trim().length > 0)

    const spikeId = item.title.toLowerCase().replace(/[^a-z0-9]+/g, '-').slice(0, 30)

    try {
      const data = await synthesizeDraft({
        topic_title: item.title,
        topic_summary: briefing?.summary || item.title,
        responses,
        raw_notes: rawNotes,
        spike_id: spikeId,
      })
      onSynthesizeComplete(data.draft, data.spike_id)
    } catch (err) {
      setSynthError(err.message || 'Draft synthesis failed.')
      setSynthesizing(false)
    }
  }

  return createPortal(
    <div 
      className="fixed inset-0 z-[100] w-screen h-screen bg-[#141413]/70 backdrop-blur-sm flex items-center justify-center p-6 sm:p-8 md:p-10 overflow-y-auto"
      onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
    >
      <div 
        className="bg-[#faf9f5] border border-[#e3dacc] rounded-3xl max-w-2xl w-full p-6 sm:p-8 space-y-6 shadow-2xl animate-fadeIn max-h-[calc(100vh-5rem)] flex flex-col justify-between my-auto shrink-0"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-start justify-between gap-4 border-b border-[#e3dacc] pb-4 shrink-0">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded-full bg-[#c6613f]/10 text-[#c6613f] border border-[#c6613f]/30">
                Topic Briefing & Perspective
              </span>
            </div>
            <h2 className="text-xl font-serif font-medium text-[#141413] leading-snug">
              {item.title}
            </h2>
            {item.url && (
              <a
                href={item.url}
                target="_blank"
                rel="noreferrer"
                className="text-[11px] font-mono text-[#87867f] hover:text-[#141413] flex items-center gap-1 inline-flex"
              >
                <span>{item.source || 'Source Article'}</span>
                <ExternalLink className="w-2.5 h-2.5" />
              </a>
            )}
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-full text-[#87867f] hover:text-[#141413] hover:bg-[#e3dacc]/50 transition shrink-0"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Scrollable Content */}
        <div className="space-y-6 overflow-y-auto pr-3 sm:pr-4 flex-1 py-1 -mr-1">
          {/* Section 1: Executive Briefing */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <h3 className="text-[11px] uppercase font-mono tracking-wider text-[#87867f] flex items-center gap-1.5">
                <Sparkles className="w-3 h-3 text-[#d97757]" />
                <span>Executive Topic Briefing</span>
              </h3>
              {loadingBriefing && (
                <span className="text-[10px] font-mono text-[#87867f] flex items-center gap-1">
                  <RotateCw className="w-2.5 h-2.5 animate-spin text-[#c6613f]" />
                  <span>synthesizing briefing...</span>
                </span>
              )}
            </div>

            {loadingBriefing ? (
              <div className="bg-[#f0eee6]/60 border border-[#e3dacc] rounded-2xl p-6 space-y-3 animate-pulse">
                <div className="h-3 bg-[#e3dacc] rounded w-3/4"></div>
                <div className="h-3 bg-[#e3dacc] rounded w-5/6"></div>
                <div className="h-3 bg-[#e3dacc] rounded w-1/2"></div>
              </div>
            ) : briefing ? (
              <div className="bg-[#f0eee6]/60 border border-[#e3dacc] rounded-2xl p-5 sm:p-6 space-y-3 shadow-anthropic">
                <p className="text-xs sm:text-sm font-serif text-[#141413] leading-relaxed">
                  {briefing.summary}
                </p>
                {briefing.core_conflict && (
                  <div className="pt-3 border-t border-[#e3dacc]/70 flex items-start gap-2 text-[11px] sm:text-xs text-[#87867f]">
                    <span className="font-mono text-[#c6613f] uppercase text-[10px] tracking-wider shrink-0 font-medium">Core Tension:</span>
                    <span className="italic leading-relaxed">{briefing.core_conflict}</span>
                  </div>
                )}
              </div>
            ) : (
              <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-800">
                {briefingError || 'Could not load briefing.'}
              </div>
            )}
          </div>

          {/* Section 2: Guided Persona Questions */}
          <div className="space-y-3">
            <div>
              <h3 className="text-[11px] uppercase font-mono tracking-wider text-[#87867f] flex items-center gap-1.5">
                <Users className="w-3 h-3 text-[#c6613f]" />
                <span>Interrogator Personas &bull; Your Perspective</span>
              </h3>
              <p className="text-[11px] text-[#87867f] mt-0.5">
                Ground the draft in your authentic operational reality. Answer one or more questions below using text or voice dictation:
              </p>
            </div>

            {recordingError && (
              <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-amber-800 text-xs flex items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0 text-amber-600" />
                  <span>{recordingError}</span>
                </div>
                <button
                  type="button"
                  onClick={() => setRecordingError('')}
                  className="p-1 text-amber-600 hover:text-amber-800 rounded-full"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            )}

            {loadingBriefing ? (
              <div className="space-y-2">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-20 bg-[#f0eee6]/40 border border-[#e3dacc] rounded-xl animate-pulse"></div>
                ))}
              </div>
            ) : (
              <div className="space-y-4">
                {(briefing?.questions || []).map((q, idx) => (
                  <div key={idx} className="bg-[#faf9f5] border border-[#e3dacc] rounded-2xl p-5 space-y-3 shadow-sm">
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] font-mono px-2.5 py-0.5 rounded-full bg-[#f0eee6] text-[#141413] font-medium border border-[#e3dacc]">
                          {q.persona}
                        </span>
                        <span className="text-[10px] font-mono text-[#87867f]">
                          {q.focus}
                        </span>
                      </div>

                      <button
                        type="button"
                        onClick={() => startVoiceRecording(idx)}
                        className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-mono transition shadow-sm ${
                          recordingTarget === idx
                            ? 'bg-rose-600 text-white animate-pulse shadow-rose-200'
                            : isTranscribingAudio && recordingTarget === idx
                            ? 'bg-[#e3dacc] text-[#87867f] cursor-wait'
                            : 'bg-[#f0eee6] hover:bg-[#e3dacc] text-[#141413] border border-[#e3dacc]'
                        }`}
                        title={recordingTarget === idx ? 'Click to stop recording' : 'Dictate your answer using voice'}
                      >
                        {recordingTarget === idx ? (
                          <>
                            <span className="w-2 h-2 rounded-full bg-white animate-ping" />
                            <span className="font-medium">Listening... Stop</span>
                          </>
                        ) : isTranscribingAudio && recordingTarget === idx ? (
                          <>
                            <RotateCw className="w-3 h-3 animate-spin text-[#c6613f]" />
                            <span>Transcribing...</span>
                          </>
                        ) : (
                          <>
                            <Mic className="w-3 h-3 text-[#c6613f]" />
                            <span>Voice Input</span>
                          </>
                        )}
                      </button>
                    </div>
                    <p className="text-xs sm:text-sm font-medium text-[#141413] leading-snug">
                      {q.question}
                    </p>
                    <textarea
                      rows={3}
                      value={answers[idx] || ''}
                      onChange={(e) => setAnswers({ ...answers, [idx]: e.target.value })}
                      placeholder="Your concrete experience, numbers, tools, or observations..."
                      className={`w-full text-xs sm:text-sm font-sans bg-[#f0eee6]/40 border rounded-xl p-3 sm:p-3.5 text-[#141413] focus:outline-none focus:border-[#141413] focus:bg-[#faf9f5] transition placeholder-[#b0aea5] ${
                        recordingTarget === idx
                          ? 'border-[#c6613f] ring-2 ring-[#c6613f]/20 bg-[#faf9f5]'
                          : 'border-[#e3dacc]'
                      }`}
                    />
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Section 3: Freeform Notes or Dictation */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="block text-[11px] font-mono uppercase tracking-wider text-[#87867f] flex items-center gap-1.5">
                <Mic className="w-3 h-3 text-[#d97757]" />
                <span>Additional Notes / Raw Dictation</span>
              </label>
              <button
                type="button"
                onClick={() => startVoiceRecording('raw')}
                className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-mono transition shadow-sm ${
                  recordingTarget === 'raw'
                    ? 'bg-rose-600 text-white animate-pulse shadow-rose-200'
                    : isTranscribingAudio && recordingTarget === 'raw'
                    ? 'bg-[#e3dacc] text-[#87867f] cursor-wait'
                    : 'bg-[#f0eee6] hover:bg-[#e3dacc] text-[#141413] border border-[#e3dacc]'
                }`}
                title={recordingTarget === 'raw' ? 'Click to stop recording' : 'Dictate notes using voice'}
              >
                {recordingTarget === 'raw' ? (
                  <>
                    <span className="w-2 h-2 rounded-full bg-white animate-ping" />
                    <span className="font-medium">Listening... Stop</span>
                  </>
                ) : isTranscribingAudio && recordingTarget === 'raw' ? (
                  <>
                    <RotateCw className="w-3 h-3 animate-spin text-[#c6613f]" />
                    <span>Transcribing...</span>
                  </>
                ) : (
                  <>
                    <Mic className="w-3 h-3 text-[#c6613f]" />
                    <span>Voice Input</span>
                  </>
                )}
              </button>
            </div>
            <textarea
              rows={3}
              value={rawNotes}
              onChange={(e) => setRawNotes(e.target.value)}
              placeholder="Paste voice dictation or any unstructured thoughts, counter-intuitive arguments, or specific dialogue..."
              className={`w-full text-xs sm:text-sm font-sans bg-[#f0eee6]/40 border rounded-xl p-3 sm:p-3.5 text-[#141413] focus:outline-none focus:border-[#141413] focus:bg-[#faf9f5] transition placeholder-[#b0aea5] ${
                recordingTarget === 'raw'
                  ? 'border-[#c6613f] ring-2 ring-[#c6613f]/20 bg-[#faf9f5]'
                  : 'border-[#e3dacc]'
              }`}
            />
          </div>

          {synthError && (
            <div className="p-3.5 bg-rose-50 border border-rose-200 rounded-xl text-rose-800 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
              <span>{synthError}</span>
            </div>
          )}
        </div>

        {/* Modal Actions */}
        <div className="flex items-center justify-between pt-5 mt-2 border-t border-[#e3dacc] shrink-0 gap-3">
          <button
            onClick={() => onSkipToCouncil(item)}
            className="text-xs font-mono text-[#87867f] hover:text-[#141413] px-3.5 py-2 rounded-full hover:bg-[#e3dacc]/50 transition"
          >
            Skip to Manual Drafting &rarr;
          </button>

          <button
            onClick={handleSynthesize}
            disabled={synthesizing || loadingBriefing}
            className="py-2.5 px-5 bg-[#c6613f] hover:bg-[#a54c2d] disabled:opacity-50 text-[#faf9f5] rounded-full text-xs font-medium transition flex items-center gap-2 shadow-sm"
          >
            {synthesizing ? (
              <>
                <RotateCw className="w-3.5 h-3.5 animate-spin" />
                <span>Synthesizing Grounded Draft...</span>
              </>
            ) : (
              <>
                <Sparkles className="w-3.5 h-3.5" />
                <span>Synthesize Grounded Draft &rarr;</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>,
    document.body
  )
}

function ScanProgressHUD({ progress, loading, onDismiss }) {
  if (!progress) return null

  const {
    phase = 'fetching',
    message = '',
    sourcesFetched = 0,
    sourcesTotal = 0,
    cachedSkipped = 0,
    newSignals = 0,
    current = 0,
    total = 0,
    currentItemTitle = '',
    passed = 0,
    elapsedSec = 0,
  } = progress

  const isFetchingDone = ['deduplicating', 'scoring', 'complete'].includes(phase)
  const isFetchingActive = phase === 'fetching'

  const isDedupDone = ['scoring', 'complete'].includes(phase)
  const isDedupActive = phase === 'deduplicating'

  const isScoringDone = phase === 'complete'
  const isScoringActive = phase === 'scoring'

  const isComplete = phase === 'complete'
  const isError = phase === 'error'

  let progressPercent = 0
  if (isComplete) {
    progressPercent = 100
  } else if (isScoringActive) {
    const fraction = total > 0 ? current / total : 0
    progressPercent = Math.min(95, Math.round(35 + fraction * 60))
  } else if (isDedupActive) {
    progressPercent = 30
  } else if (isFetchingActive) {
    const fraction = sourcesTotal > 0 ? sourcesFetched / sourcesTotal : 0
    progressPercent = Math.min(25, Math.round(5 + fraction * 20))
  }

  return (
    <div className="bg-[#faf9f5] border border-[#e3dacc] rounded-2xl p-5 sm:p-6 shadow-anthropic space-y-4 animate-fadeIn">
      {/* 3-Phase Stepper Header */}
      <div className="flex items-center justify-between gap-3 border-b border-[#e3dacc]/70 pb-3.5">
        <div className="flex items-center gap-2 sm:gap-4 overflow-x-auto w-full py-0.5">
          {/* Phase 1: Ingesting */}
          <div className="flex items-center gap-2.5 shrink-0">
            <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-mono font-medium transition ${
              isFetchingDone
                ? 'bg-emerald-100 text-emerald-800 border border-emerald-300/60'
                : isFetchingActive
                ? 'bg-[#c6613f] text-[#faf9f5] shadow-xs font-semibold'
                : 'bg-[#f0eee6] text-[#87867f] border border-[#e3dacc]'
            }`}>
              {isFetchingDone ? <Check className="w-3.5 h-3.5 stroke-[2.5]" /> : '1'}
            </div>
            <div className="flex flex-col">
              <span className={`text-xs ${isFetchingActive ? 'font-semibold text-[#141413]' : 'font-medium text-[#87867f]'}`}>
                Ingesting Sources
              </span>
              <span className="text-[10px] font-mono text-[#87867f]">
                {sourcesFetched}/{sourcesTotal || 1} sources
              </span>
            </div>
          </div>

          <ChevronRight className="w-3.5 h-3.5 text-[#b0aea5] shrink-0" />

          {/* Phase 2: Zero-Token Deduplication */}
          <div className="flex items-center gap-2.5 shrink-0">
            <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-mono font-medium transition ${
              isDedupDone
                ? 'bg-emerald-100 text-emerald-800 border border-emerald-300/60'
                : isDedupActive
                ? 'bg-[#c6613f] text-[#faf9f5] shadow-xs font-semibold'
                : 'bg-[#f0eee6] text-[#87867f] border border-[#e3dacc]'
            }`}>
              {isDedupDone ? <Check className="w-3.5 h-3.5 stroke-[2.5]" /> : '2'}
            </div>
            <div className="flex flex-col">
              <span className={`text-xs ${isDedupActive ? 'font-semibold text-[#141413]' : 'font-medium text-[#87867f]'}`}>
                Zero-Token Dedup
              </span>
              <span className="text-[10px] font-mono text-[#87867f]">
                {cachedSkipped} cached skipped
              </span>
            </div>
          </div>

          <ChevronRight className="w-3.5 h-3.5 text-[#b0aea5] shrink-0" />

          {/* Phase 3: Scoring & Ranking */}
          <div className="flex items-center gap-2.5 shrink-0">
            <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-mono font-medium transition ${
              isScoringDone
                ? 'bg-emerald-100 text-emerald-800 border border-emerald-300/60'
                : isScoringActive
                ? 'bg-[#c6613f] text-[#faf9f5] shadow-xs font-semibold'
                : 'bg-[#f0eee6] text-[#87867f] border border-[#e3dacc]'
            }`}>
              {isScoringDone ? <Check className="w-3.5 h-3.5 stroke-[2.5]" /> : '3'}
            </div>
            <div className="flex flex-col">
              <span className={`text-xs ${isScoringActive ? 'font-semibold text-[#141413]' : 'font-medium text-[#87867f]'}`}>
                Scoring &amp; Ranking
              </span>
              <span className="text-[10px] font-mono text-[#87867f]">
                {current}/{total || '-'} signals
              </span>
            </div>
          </div>
        </div>

        {/* Dismiss Button */}
        {(isComplete || isError) && (
          <button
            type="button"
            onClick={onDismiss}
            className="p-1 rounded-full text-[#87867f] hover:text-[#141413] hover:bg-[#e3dacc]/50 transition shrink-0"
            title="Dismiss HUD"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Live Message Badge & Metric Pills */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-0.5">
        {/* Live Message Badge */}
        <div className="flex items-center gap-2.5 min-w-0 flex-1">
          {loading ? (
            <RotateCw className="w-4 h-4 animate-spin text-[#c6613f] shrink-0" />
          ) : isComplete ? (
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
          ) : (
            <AlertCircle className="w-4 h-4 text-rose-500 shrink-0" />
          )}
          <span className="text-xs font-mono text-[#141413] truncate font-medium">
            {message || (loading ? 'Processing scan pipeline...' : 'Scan idle.')}
          </span>
        </div>

        {/* Live Metrics */}
        <div className="flex items-center gap-2 flex-wrap shrink-0">
          <span className="inline-flex items-center gap-1.5 text-[11px] font-mono px-3 py-1 rounded-full bg-emerald-50 text-emerald-900 border border-emerald-200/80 font-medium">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
            <span>Zero-Token: <strong>{cachedSkipped}</strong> cached</span>
          </span>

          <span className="text-[11px] font-mono px-3 py-1 rounded-full bg-[#f0eee6] text-[#141413] border border-[#e3dacc] font-medium">
            Scored: <strong>{current}</strong>/{total}
          </span>

          <span className="text-[11px] font-mono px-3 py-1 rounded-full bg-[#c6613f]/10 text-[#c6613f] border border-[#c6613f]/30 font-medium">
            Passed: <strong>{passed}</strong>
          </span>

          {isComplete && elapsedSec > 0 && (
            <span className="text-[11px] font-mono px-3 py-1 rounded-full bg-[#f0eee6] text-[#87867f] border border-[#e3dacc]">
              {elapsedSec}s
            </span>
          )}
        </div>
      </div>

      {/* Progress Bar for Item Scoring */}
      <div className="bg-[#f0eee6]/50 border border-[#e3dacc] rounded-xl p-3.5 space-y-2">
        <div className="flex items-center justify-between text-xs font-mono text-[#87867f]">
          <span className="truncate max-w-[80%]">
            {isScoringActive 
              ? (currentItemTitle ? `Evaluating: "${currentItemTitle}"` : 'Evaluating signals consensus...')
              : isComplete 
              ? 'Scan pipeline completed & cached' 
              : isDedupActive 
              ? 'Deduplicating signals with SQLite (0 tokens)' 
              : 'Pulling items from registered sources...'}
          </span>
          <span className="font-semibold text-[#141413]">{progressPercent}%</span>
        </div>
        <div className="w-full h-2 bg-[#e3dacc]/60 rounded-full overflow-hidden border border-[#e3dacc]/50">
          <div
            className={`h-full transition-all duration-300 rounded-full ${
              isComplete ? 'bg-emerald-600' : 'bg-[#c6613f]'
            }`}
            style={{ width: `${progressPercent}%` }}
          />
        </div>
      </div>
    </div>
  )
}

function CandidateCard({ candidate, onSendToCouncil, onOpenInterview, onDismiss }) {
  const { copied, copy, setCopied } = useCopyToClipboard()

  const handleCopySummary = async (e) => {
    e.stopPropagation()
    const parts = [
      candidate.title,
      candidate.url ? `Source: ${candidate.url}` : null,
      candidate.source ? `Feed: ${candidate.source}` : null,
      candidate.body_snippet ? `Excerpt:\n${candidate.body_snippet}` : null,
    ].filter(Boolean)
    const text = parts.join('\n')

    if (!(await copy(text))) {
      try {
        const textArea = document.createElement('textarea')
        textArea.value = text
        textArea.style.position = 'fixed'
        textArea.style.opacity = '0'
        document.body.appendChild(textArea)
        textArea.focus()
        textArea.select()
        document.execCommand('copy')
        document.body.removeChild(textArea)
        setCopied(true)
        setTimeout(() => setCopied(false), 2000)
      } catch (fallbackErr) {
        console.error('Failed to copy', fallbackErr)
      }
    }
  }

  const renderDimensionScores = () => {
    if (!candidate.dimension_scores || typeof candidate.dimension_scores !== 'object') return null

    const seen = new Set()
    const chips = []
    const preferredOrder = ['lived_experience', 'novelty', 'counter_intuitive', 'specificity', 'pov', 'relevance', 'rigor']
    const allKeys = [...preferredOrder, ...Object.keys(candidate.dimension_scores)]

    for (const key of allKeys) {
      if (key === 'composite') continue
      const val = candidate.dimension_scores[key]
      if (typeof val !== 'number') continue
      const label = DIMENSION_LABELS[key] || (key.charAt(0).toUpperCase() + key.slice(1).replace(/_/g, ' '))
      if (seen.has(label)) continue
      seen.add(label)
      chips.push({ label, val: val.toFixed(1) })
      if (chips.length >= 5) break
    }

    if (chips.length === 0) return null

    return (
      <div className="flex items-center gap-1.5 flex-wrap pt-0.5">
        {chips.map(({ label, val }) => (
          <span
            key={label}
            className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-[#f0eee6] text-[#5c5a55] border border-[#e3dacc] flex items-center gap-1"
          >
            <span className="text-[#87867f]">{label}:</span>
            <span className="font-semibold text-[#141413]">{val}</span>
          </span>
        ))}
      </div>
    )
  }

  const isPass = candidate.verdict === 'pass'
  const isReview = candidate.verdict === 'review'
  const scoreFormatted = typeof candidate.score === 'number' ? candidate.score.toFixed(2) : candidate.score
  const verdictText = (candidate.verdict || 'PASS').toUpperCase()

  return (
    <div className="bg-[#faf9f5] hover:bg-[#f0eee6]/30 transition-all duration-200 border border-[#e3dacc] hover:border-[#b0aea5] rounded-2xl p-5 space-y-3.5 shadow-anthropic group">
      {/* Top Row: Topic Badge & Score Capsule */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2 flex-wrap">
          {candidate.topic_tag && (
            <span className={`text-[10px] font-medium px-2.5 py-0.5 rounded-full border ${getTopicBadgeClass(candidate.topic_tag)}`}>
              {candidate.topic_tag}
            </span>
          )}
          <span className="text-[11px] text-[#87867f] font-mono">{candidate.source}</span>
          {candidate.published_at && (
            <>
              <span className="text-[#b0aea5]">&bull;</span>
              <span className="text-[11px] text-[#87867f] font-mono">
                {new Date(candidate.published_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}
              </span>
            </>
          )}
        </div>

        {/* Score Capsule: PASS 8.95 */}
        <div className="flex items-center shrink-0">
          <span className={`text-xs font-mono font-semibold px-2.5 py-0.5 rounded-full border flex items-center gap-1.5 ${
            isPass
              ? 'bg-[#c6613f]/10 text-[#c6613f] border-[#c6613f]/30'
              : isReview
              ? 'bg-[#d97757]/10 text-[#d97757] border-[#d97757]/30'
              : 'bg-[#f0eee6] text-[#87867f] border-[#e3dacc]'
          }`}>
            <span className="text-[10px] uppercase font-bold tracking-wider">{verdictText}</span>
            <span className="font-bold">{scoreFormatted}</span>
          </span>
        </div>
      </div>

      {/* Title (Clickable link to source) */}
      <div>
        {candidate.url ? (
          <a
            href={candidate.url}
            target="_blank"
            rel="noreferrer"
            className="text-base font-serif font-medium text-[#141413] hover:text-[#c6613f] transition leading-snug inline-block"
          >
            {candidate.title}
          </a>
        ) : (
          <h4 className="text-base font-serif font-medium text-[#141413] leading-snug">
            {candidate.title}
          </h4>
        )}
      </div>

      {/* 2-line Clean Excerpt Preview */}
      {candidate.body_snippet && (
        <p
          className="text-xs text-[#5c5a55] font-sans leading-relaxed line-clamp-2"
          style={{
            display: '-webkit-box',
            WebkitLineClamp: 2,
            WebkitBoxOrient: 'vertical',
            overflow: 'hidden',
          }}
        >
          {candidate.body_snippet}
        </p>
      )}

      {/* Dimension Scores Micro-Chips */}
      {renderDimensionScores()}

      {/* Card Footer Action Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-[#e3dacc]">
        {/* Quick Actions */}
        <div className="flex items-center gap-1.5 flex-wrap">
          {/* Brief & Perspective (Subsystem 2) */}
          {onOpenInterview && (
            <button
              type="button"
              onClick={() => onOpenInterview(candidate)}
              className="text-xs text-[#87867f] hover:text-[#141413] px-2.5 py-1 rounded-full hover:bg-[#e3dacc]/50 transition flex items-center gap-1 font-medium"
              title="Open Topic Briefing & Perspective Intake"
            >
              <Sparkles className="w-3 h-3 text-[#d97757]" />
              <span>Perspective</span>
            </button>
          )}

          {/* Copy Summary */}
          <button
            type="button"
            onClick={handleCopySummary}
            className={`text-xs px-2.5 py-1 rounded-full transition flex items-center gap-1 font-mono ${
              copied
                ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                : 'text-[#87867f] hover:text-[#141413] hover:bg-[#e3dacc]/50'
            }`}
            title="Copy title, link, and excerpt to clipboard"
          >
            {copied ? (
              <>
                <Check className="w-3 h-3 text-emerald-600 stroke-[2.5]" />
                <span className="font-semibold">Copied!</span>
              </>
            ) : (
              <>
                <Copy className="w-3 h-3" />
                <span>Copy Summary</span>
              </>
            )}
          </button>

          {/* Open Source */}
          {candidate.url && (
            <a
              href={candidate.url}
              target="_blank"
              rel="noreferrer"
              className="text-xs text-[#87867f] hover:text-[#141413] px-2 py-1 rounded-full hover:bg-[#e3dacc]/50 transition inline-flex items-center gap-1 font-mono"
              title="Open source URL in new tab"
            >
              <span>Open Source</span>
              <ExternalLink className="w-3 h-3" />
            </a>
          )}

          {/* Dismiss */}
          <button
            type="button"
            onClick={() => onDismiss(candidate)}
            className="text-xs text-[#87867f] hover:text-rose-600 px-2 py-1 rounded-full hover:bg-rose-50 transition flex items-center gap-1 font-mono"
            title="Dismiss candidate from active batch"
          >
            <X className="w-3 h-3" />
            <span>Dismiss</span>
          </button>
        </div>

        {/* Primary Action: Send to Council */}
        <button
          type="button"
          onClick={() => onSendToCouncil(candidate)}
          className="py-1.5 px-4 bg-[#141413] hover:bg-[#252524] text-[#faf9f5] rounded-full text-xs font-medium transition flex items-center gap-1.5 shadow-sm ml-auto shrink-0"
        >
          <span>Send to Council</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  )
}

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

function CouncilTab({ draft, setDraft, spikeId, setSpikeId, onSendToDistribute }) {
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [historyData, setHistoryData] = useState(null)
  const [recentSpikes, setRecentSpikes] = useState([])
  const [showHistory, setShowHistory] = useState(false)
  const [humanizing, setHumanizing] = useState(false)
  const [humanizedResult, setHumanizedResult] = useState(null)
  const { copied: humanizeCopied, copy: copyHumanized } = useCopyToClipboard()
  const [humanizeError, setHumanizeError] = useState('')

  const fetchHistory = async (slug) => {
    if (!slug) return
    try {
      const data = await getCouncilHistory(slug)
      setHistoryData(data)
    } catch {
      // ignore
    }
  }

  const fetchSpikes = async () => {
    try {
      const data = await getCouncilSpikes()
      setRecentSpikes(data)
    } catch {
      // ignore
    }
  }

  useEffect(() => {
    fetchSpikes()
  }, [])

  useEffect(() => {
    if (spikeId) {
      fetchHistory(spikeId)
    }
  }, [spikeId])

  const handleReview = async (e) => {
    e.preventDefault()
    if (!draft.trim()) {
      setError('Draft text cannot be empty.')
      return
    }
    setLoading(true)
    setError('')
    setResult(null)

    try {
      const targetSlug = spikeId || 'council-ui'
      const data = await runCouncil({ draft, spike_id: targetSlug })
      setResult(data)
      fetchHistory(targetSlug)
      fetchSpikes()
    } catch (err) {
      setError(err.message || 'Council run failed.')
    } finally {
      setLoading(false)
    }
  }

  const handleSelectSpike = (slug) => {
    setSpikeId(slug)
    fetchHistory(slug)
  }

  const handleLoadDraft = (text) => {
    if (text) {
      setDraft(text)
    }
  }

  const best = historyData?.best

  const handleHumanize = async (sourceText) => {
    const textToHumanize = sourceText || best?.draft || draft
    if (!textToHumanize || !textToHumanize.trim()) {
      setHumanizeError('No draft text available to humanize.')
      return
    }

    setHumanizing(true)
    setHumanizeError('')
    try {
      const data = await runHumanize({
        text: textToHumanize,
        channel: 'linkedin_post',
        tone: 'pragmatic_architect',
      })
      setHumanizedResult(data)
    } catch (err) {
      setHumanizeError(err.message || 'Failed to humanize draft.')
    } finally {
      setHumanizing(false)
    }
  }

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Editorial Title */}
      <div>
        <h2 className="font-serif text-2xl font-medium tracking-tight text-[#141413]">Writer's Council</h2>
        <p className="text-sm text-[#87867f] mt-1 font-sans">
          Multi-judge editorial review and iterative revision.
        </p>
      </div>

      {/* Historical Peak Banner (Refined Warm Stone & Clay) */}
      {best && (
        <div className="p-5 bg-[#f0eee6] border border-[#e3dacc] rounded-2xl flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-anthropic">
          <div className="flex items-start gap-3.5">
            <div className="p-2.5 bg-[#c6613f]/10 text-[#c6613f] rounded-xl shrink-0 mt-0.5 border border-[#c6613f]/20">
              <Trophy className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono font-bold uppercase tracking-wider text-[#c6613f]">All-Time Peak Iteration</span>
                <span className="text-[10px] font-mono px-2.5 py-0.5 rounded-full bg-[#faf9f5] text-[#141413] border border-[#e3dacc]">
                  Iteration {best.iteration}
                </span>
                {best.score >= 8.0 && (
                  <span className="text-[10px] font-mono px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-300">
                    PASS
                  </span>
                )}
              </div>
              <div className="text-2xl font-serif font-semibold text-[#141413] mt-0.5">
                {best.score.toFixed(3)}
                <span className="text-xs font-normal text-[#87867f] ml-2 font-mono">/ 10.0</span>
              </div>
              <p className="text-xs text-[#87867f] mt-0.5">
                Highest scoring version recorded for <span className="font-mono text-[#141413] font-medium">{spikeId}</span>.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2.5 shrink-0 flex-wrap">
            {best.draft && (
              <button
                type="button"
                onClick={() => handleLoadDraft(best.draft)}
                className="px-4 py-2 bg-[#faf9f5] hover:bg-[#e3dacc]/50 text-[#141413] rounded-full text-xs font-medium transition flex items-center gap-1.5 border border-[#e3dacc] shadow-sm"
              >
                <RotateCw className="w-3.5 h-3.5 text-[#87867f]" />
                <span>Load Peak Draft</span>
              </button>
            )}
            {best.draft && (
              <button
                type="button"
                onClick={() => handleHumanize(best.draft)}
                disabled={humanizing}
                className="px-4 py-2 bg-[#faf9f5] hover:bg-[#e3dacc]/50 text-[#c6613f] border border-[#c6613f]/40 hover:border-[#c6613f] rounded-full text-xs font-medium transition flex items-center gap-1.5 shadow-sm disabled:opacity-50"
              >
                {humanizing ? (
                  <RotateCw className="w-3.5 h-3.5 animate-spin text-[#c6613f]" />
                ) : (
                  <Sparkles className="w-3.5 h-3.5 text-[#c6613f]" />
                )}
                <span>{humanizing ? 'Humanizing...' : '🪄 Humanize Peak Draft'}</span>
              </button>
            )}
            {best.draft && onSendToDistribute && (
              <button
                type="button"
                onClick={() => onSendToDistribute(best.draft, spikeId)}
                className="px-4 py-2 bg-[#c6613f] hover:bg-[#b55535] text-[#faf9f5] rounded-full text-xs font-medium transition flex items-center gap-1.5 shadow-sm"
              >
                <Share2 className="w-3.5 h-3.5" />
                <span>Distribute Peak Post</span>
              </button>
            )}
          </div>
        </div>
      )}

      {/* Humanized Peak Draft Card */}
      {humanizedResult && (
        <div className="p-6 bg-[#faf9f5] border border-[#e3dacc] rounded-2xl shadow-anthropic space-y-4 animate-fadeIn">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#e3dacc] pb-4">
            <div className="flex items-center gap-2.5 flex-wrap">
              <div className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono font-semibold bg-[#c6613f]/10 text-[#c6613f] border border-[#c6613f]/30">
                <Sparkles className="w-3.5 h-3.5" />
                <span>Humanized ✨ (Burstiness: {typeof humanizedResult.burstiness_score === 'number' ? humanizedResult.burstiness_score.toFixed(1) : humanizedResult.burstiness_score})</span>
              </div>
              <span className="text-[11px] font-mono px-2.5 py-0.5 rounded-full bg-[#f0eee6] text-[#87867f] border border-[#e3dacc]">
                {humanizedResult.sentence_count || 0} sentences
              </span>
              <span className="text-[11px] font-mono px-2.5 py-0.5 rounded-full bg-[#f0eee6] text-[#87867f] border border-[#e3dacc]">
                Tone: Pragmatic Architect
              </span>
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => {
                  setDraft(humanizedResult.humanized_text)
                }}
                className="px-3.5 py-1.5 rounded-full text-xs font-mono font-medium transition bg-[#141413] hover:bg-[#252524] text-[#faf9f5] flex items-center gap-1.5 shadow-sm"
                title="Replace editor content with this humanized version"
              >
                <FileText className="w-3.5 h-3.5 text-[#d97757]" />
                <span>Use in Editor</span>
              </button>

              <button
                type="button"
                onClick={() => {
                  copyHumanized(humanizedResult.humanized_text)
                }}
                className="px-3.5 py-1.5 rounded-full text-xs font-mono font-medium transition bg-[#faf9f5] hover:bg-[#e3dacc]/50 text-[#141413] border border-[#e3dacc] flex items-center gap-1.5 shadow-sm"
              >
                {humanizeCopied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5 text-[#87867f]" />}
                <span>{humanizeCopied ? 'Copied!' : 'Copy'}</span>
              </button>

              <button
                type="button"
                onClick={() => setHumanizedResult(null)}
                className="p-1.5 rounded-full text-[#87867f] hover:text-[#141413] hover:bg-[#f0eee6] transition"
                title="Dismiss"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Purged Clichés Chips */}
          {humanizedResult.banned_words_purged && humanizedResult.banned_words_purged.length > 0 && (
            <div className="flex items-center gap-2 flex-wrap text-xs">
              <span className="text-[#87867f] font-mono text-[11px] uppercase tracking-wider font-semibold">
                Purged AI Clichés ({humanizedResult.banned_words_purged.length}):
              </span>
              {humanizedResult.banned_words_purged.map((word, idx) => (
                <span
                  key={idx}
                  className="px-2.5 py-0.5 rounded-full text-[11px] font-mono bg-rose-50 text-rose-800 border border-rose-200 line-through"
                >
                  {word}
                </span>
              ))}
            </div>
          )}

          {/* Humanized Text Box */}
          <div className="bg-[#f0eee6]/40 border border-[#e3dacc] rounded-xl p-5 font-serif text-sm sm:text-base leading-relaxed text-[#141413] whitespace-pre-wrap selection:bg-[#c6613f]/20">
            {humanizedResult.humanized_text}
          </div>
        </div>
      )}

      {humanizeError && (
        <div className="p-3.5 bg-rose-50 border border-rose-200 rounded-xl text-rose-800 text-xs flex items-center gap-2 animate-fadeIn">
          <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
          <span>{humanizeError}</span>
        </div>
      )}

      {/* Signature High-Contrast Dual Panel Layout: Dark Editor vs Warm Ivory Verdict */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-start">
        {/* Left: High-Contrast Slate Dark Drafting Studio */}
        <form onSubmit={handleReview} className="bg-[#141413] text-[#faf9f5] p-6 rounded-2xl border border-[#252524] shadow-xl space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-xs uppercase font-mono tracking-wider text-[#b0aea5] flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-[#d97757]" />
              <span>Draft Studio</span>
            </h3>
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={spikeId}
                onChange={(e) => setSpikeId(e.target.value)}
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
                  onClick={() => handleSelectSpike(spk.spike_id)}
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
            onChange={(e) => setDraft(e.target.value)}
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

        {/* Right: Warm Ivory Editorial Verdict Panel */}
        <div className="space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-[#e3dacc]">
            <h3 className="text-xs uppercase font-mono tracking-wider text-[#87867f]">Editorial Verdict</h3>
            <div className="flex items-center gap-3">
              {result && (
                <span className="text-[11px] font-mono text-[#87867f]">Iteration {result.iteration}</span>
              )}
              {historyData?.history?.length > 0 && (
                <button
                  type="button"
                  onClick={() => setShowHistory(!showHistory)}
                  className="text-[11px] font-mono text-[#87867f] hover:text-[#141413] flex items-center gap-1 transition"
                >
                  <History className="w-3 h-3" />
                  <span>{showHistory ? 'Hide History' : `History (${historyData.history.length})`}</span>
                </button>
              )}
            </div>
          </div>

          {!result && !loading && (
            <div className="border border-dashed border-[#b0aea5] rounded-2xl p-12 text-center text-[#87867f] bg-[#f0eee6]/30">
              <Users className="w-8 h-8 mx-auto mb-3 stroke-1 text-[#b0aea5]" />
              <p className="text-sm font-medium text-[#141413]">No active evaluation.</p>
              <p className="text-xs text-[#87867f] mt-1">Submit your draft or load a historical peak iteration to view the multi-judge evaluation.</p>
            </div>
          )}

          {loading && (
            <div className="border border-[#e3dacc] rounded-2xl p-12 text-center text-[#87867f] space-y-3 bg-[#f0eee6]/50 shadow-anthropic">
              <RotateCw className="w-6 h-6 mx-auto animate-spin text-[#c6613f]" />
              <p className="text-sm font-medium text-[#141413]">Obfuscating authorship & gathering parallel verdicts...</p>
              <p className="text-xs text-[#87867f] font-mono">Running z-score normalization against rolling history</p>
            </div>
          )}

          {result && (
            <div className="bg-[#faf9f5] border border-[#e3dacc] rounded-2xl p-6 space-y-6 shadow-anthropic">
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-xs font-mono uppercase text-[#87867f]">Current Run Score</span>
                  <div className="text-3xl font-serif font-bold text-[#141413] mt-0.5">
                    {result.score.toFixed(3)}
                  </div>
                </div>

                <div className={`px-4 py-1.5 rounded-full border text-xs font-mono font-semibold uppercase tracking-wider flex items-center gap-1.5 ${
                  result.verdict === 'pass' 
                    ? 'bg-[#c6613f]/10 text-[#c6613f] border-[#c6613f]/30' 
                    : result.verdict === 'revise'
                    ? 'bg-[#d97757]/10 text-[#d97757] border-[#d97757]/30'
                    : 'bg-rose-50 text-rose-800 border-rose-200'
                }`}>
                  {result.verdict === 'pass' && <CheckCircle2 className="w-3.5 h-3.5" />}
                  {result.verdict === 'revise' && <RotateCw className="w-3.5 h-3.5" />}
                  {result.verdict === 'reject' && <XCircle className="w-3.5 h-3.5" />}
                  <span>{result.verdict}</span>
                </div>
              </div>

              {/* Peak comparison note */}
              {best && best.score > result.score && (
                <div className="p-3 bg-[#f0eee6] border border-[#e3dacc] rounded-xl flex items-center justify-between gap-3 text-xs text-[#87867f]">
                  <span>A previous iteration scored higher ({best.score.toFixed(3)}).</span>
                  <button
                    type="button"
                    onClick={() => handleLoadDraft(best.draft)}
                    className="text-[#c6613f] hover:underline font-mono font-medium text-[11px]"
                  >
                    Restore Peak Draft
                  </button>
                </div>
              )}

              {result.actions && result.actions.length > 0 && (
                <div className="space-y-3 pt-4 border-t border-[#e3dacc]">
                  <h4 className="text-xs font-mono uppercase tracking-wider text-[#87867f]">Required Editorial Actions</h4>
                  <ul className="space-y-2">
                    {result.actions.map((act, idx) => (
                      <li key={idx} className="text-xs text-[#141413] flex items-start gap-2 bg-[#f0eee6]/70 p-3 rounded-xl border border-[#e3dacc]">
                        <ChevronRight className="w-3.5 h-3.5 text-[#c6613f] shrink-0 mt-0.5" />
                        <span>{act}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="pt-4 border-t border-[#e3dacc] flex items-center justify-between gap-3 flex-wrap">
                {(result.verdict === 'pass' || best?.draft) && (
                  <button
                    type="button"
                    onClick={() => handleHumanize(best?.draft || draft)}
                    disabled={humanizing}
                    className="px-4 py-2 bg-[#faf9f5] hover:bg-[#e3dacc]/50 text-[#c6613f] border border-[#c6613f]/40 hover:border-[#c6613f] rounded-full text-xs font-medium transition flex items-center gap-1.5 shadow-sm disabled:opacity-50"
                  >
                    {humanizing ? (
                      <RotateCw className="w-3.5 h-3.5 animate-spin text-[#c6613f]" />
                    ) : (
                      <Sparkles className="w-3.5 h-3.5 text-[#c6613f]" />
                    )}
                    <span>{humanizing ? 'Humanizing...' : '🪄 Humanize Peak Draft'}</span>
                  </button>
                )}

                {onSendToDistribute && (
                  <button
                    onClick={() => onSendToDistribute(draft, spikeId)}
                    className="px-5 py-2.5 bg-[#141413] hover:bg-[#252524] text-[#faf9f5] rounded-full text-xs font-medium transition flex items-center gap-2 shadow-sm ml-auto"
                  >
                    <span>Distribute Current Post</span>
                    <Share2 className="w-3.5 h-3.5 text-[#d97757]" />
                  </button>
                )}
              </div>
            </div>
          )}

          {/* History Timeline */}
          {showHistory && historyData?.history?.length > 0 && (
            <div className="bg-[#f0eee6]/60 border border-[#e3dacc] rounded-2xl p-4 space-y-3 animate-fadeIn shadow-anthropic">
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono uppercase tracking-wider text-[#87867f]">Iteration History</span>
                <span className="text-[10px] font-mono text-[#87867f]">{historyData.history.length} records</span>
              </div>
              <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                {historyData.history.map((item) => (
                  <div
                    key={item.id}
                    className="flex items-center justify-between p-2.5 bg-[#faf9f5] border border-[#e3dacc] rounded-xl text-xs"
                  >
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-semibold text-[#141413]">Iter {item.iteration}</span>
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-mono ${
                        item.score >= 8.0 ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'
                      }`}>
                        {item.score.toFixed(3)}
                      </span>
                      {item.score === best?.score && (
                        <span className="text-[9px] font-mono px-2 py-0.5 bg-[#c6613f]/15 text-[#c6613f] rounded-full border border-[#c6613f]/30">PEAK</span>
                      )}
                    </div>

                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-mono text-[#87867f]">
                        {new Date(item.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                      {item.draft && (
                        <button
                          type="button"
                          onClick={() => handleLoadDraft(item.draft)}
                          className="text-[11px] font-mono text-[#c6613f] hover:underline"
                        >
                          Load
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function DistributeTab({ initialText, initialSlug }) {
  const [anchorText, setAnchorText] = useState(initialText || '')
  const [slug, setSlug] = useState(initialSlug || 'post-1')
  const [loading, setLoading] = useState(false)
  const [bundle, setBundle] = useState(null)
  const [error, setError] = useState('')
  const [activeFormat, setActiveFormat] = useState('linkedin')
  const { copied, copy } = useCopyToClipboard()
  const [showConfigModal, setShowConfigModal] = useState(false)
  const [humanize, setHumanize] = useState(true)
  const [humanizeTone, setHumanizeTone] = useState('pragmatic_architect')

  // Format selection state (LinkedIn default ON)
  const [enabledFormats, setEnabledFormats] = useState({
    linkedin: true,
    x_thread: true,
    video_script_short: true,
    video_script_long: false,
    newsletter: true,
  })

  // Update if initialText changes
  useEffect(() => {
    if (initialText) setAnchorText(initialText)
    if (initialSlug) setSlug(initialSlug)
  }, [initialText, initialSlug])

  const toggleFormat = (id) => {
    setEnabledFormats(prev => {
      const next = { ...prev, [id]: !prev[id] }
      // Ensure at least one format is enabled
      const hasAny = Object.values(next).some(Boolean)
      if (!hasAny) return prev
      return next
    })
  }

  const selectAllFormats = () => {
    setEnabledFormats({
      linkedin: true,
      x_thread: true,
      video_script_short: true,
      video_script_long: true,
      newsletter: true,
    })
  }

  const resetDefaultFormats = () => {
    setEnabledFormats({
      linkedin: true,
      x_thread: true,
      video_script_short: true,
      video_script_long: false,
      newsletter: true,
    })
  }

  const activeFormatKeys = Object.keys(enabledFormats).filter(k => enabledFormats[k])

  const handleGenerate = async (e) => {
    e.preventDefault()
    if (!anchorText.trim()) {
      setError('Anchor post cannot be empty.')
      return
    }
    if (activeFormatKeys.length === 0) {
      setError('Please enable at least one distribution format.')
      return
    }

    setLoading(true)
    setError('')
    setBundle(null)

    try {
      const data = await runDistribute({
        anchor_post: anchorText,
        project_slug: slug || 'post',
        enabled_formats: activeFormatKeys,
        humanize: humanize,
        tone: humanizeTone,
      })
      setBundle(data)

      const priorityOrder = ['linkedin', 'x_thread', 'video_script_short', 'video_script', 'video_script_long', 'newsletter']
      const firstAvailable = priorityOrder.find(k => data[k])
      if (firstAvailable) {
        setActiveFormat(firstAvailable)
      }
    } catch (err) {
      setError(err.message || 'Failed to generate distribution derivatives.')
    } finally {
      setLoading(false)
    }
  }

  const handleCopy = (text) => {
    if (!text) return
    copy(text)
  }

  const getFormatContent = (fmt) => {
    if (!bundle) return ''
    if (fmt === 'video_script_short') {
      return bundle.video_script_short || bundle.video_script || ''
    }
    return bundle[fmt] || ''
  }

  const availableFormats = DISTRIBUTION_FORMATS.filter(fmt => {
    if (!bundle) return false
    if (fmt.id === 'video_script_short') {
      return Boolean(bundle.video_script_short || bundle.video_script)
    }
    return Boolean(bundle[fmt.id])
  })

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#e3dacc] pb-5">
        <div>
          <h2 className="font-serif text-2xl font-medium tracking-tight text-[#141413]">Distribute</h2>
          <p className="text-sm text-[#87867f] mt-1 font-sans">
            Generate channel-native formats from your verified post.
          </p>
        </div>

        {/* Configuration Modal Trigger */}
        <button
          type="button"
          onClick={() => setShowConfigModal(true)}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-xs font-mono bg-[#f0eee6] border border-[#e3dacc] hover:border-[#b0aea5] text-[#141413] transition shadow-anthropic self-start sm:self-auto"
        >
          <Sliders className="w-3.5 h-3.5 text-[#c6613f]" />
          <span>Platforms ({activeFormatKeys.length}/5)</span>
        </button>
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-start">
        {/* Anchor Input Form */}
        <form onSubmit={handleGenerate} className="space-y-4 bg-[#f0eee6]/60 p-6 rounded-2xl border border-[#e3dacc] shadow-anthropic">
          <div className="flex items-center justify-between">
            <h3 className="text-xs uppercase font-mono tracking-wider text-[#87867f]">Anchor Post (Verified)</h3>
            <input
              type="text"
              value={slug}
              onChange={(e) => setSlug(e.target.value)}
              placeholder="Project Slug"
              className="text-xs font-mono bg-[#faf9f5] border border-[#e3dacc] rounded-lg px-2.5 py-1 text-[#141413] w-36 focus:outline-none focus:border-[#141413]"
            />
          </div>

          <textarea
            rows={16}
            value={anchorText}
            onChange={(e) => setAnchorText(e.target.value)}
            placeholder="Paste your approved anchor post or final draft..."
            className="w-full text-xs font-mono leading-relaxed bg-[#faf9f5] border border-[#e3dacc] rounded-xl p-4 text-[#141413] focus:outline-none focus:border-[#141413] resize-none placeholder-[#b0aea5]"
          />

          {/* Active Platform Chips */}
          <div className="flex items-center justify-between gap-2 p-3 bg-[#faf9f5] border border-[#e3dacc] rounded-xl">
            <div className="flex items-center gap-1.5 flex-wrap text-[11px] font-mono">
              <span className="text-[#87867f] mr-1">Active:</span>
              {DISTRIBUTION_FORMATS.map(fmt => {
                const isEnabled = enabledFormats[fmt.id]
                return (
                  <span
                    key={fmt.id}
                    onClick={() => toggleFormat(fmt.id)}
                    className={`cursor-pointer px-2.5 py-0.5 rounded-full border transition ${
                      isEnabled
                        ? fmt.id === 'linkedin'
                          ? 'bg-[#141413] text-[#faf9f5] border-[#141413] font-semibold'
                          : 'bg-[#f0eee6] text-[#141413] border-[#b0aea5] hover:border-[#141413]'
                        : 'opacity-40 line-through text-[#87867f] border-transparent hover:opacity-60'
                    }`}
                  >
                    {fmt.shortLabel}
                  </span>
                )
              })}
            </div>
            <button
              type="button"
              onClick={() => setShowConfigModal(true)}
              className="text-xs text-[#c6613f] hover:text-[#a54c2d] font-mono flex items-center gap-1 shrink-0"
            >
              <Settings className="w-3 h-3" />
              <span>Edit</span>
            </button>
          </div>

          {/* Humanize Polish Control Bar */}
          <div className="p-3.5 bg-[#faf9f5] border border-[#e3dacc] rounded-xl space-y-2.5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-xs uppercase font-mono tracking-wider text-[#87867f] font-semibold">
                  Humanize Polish
                </span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-[#f0eee6] text-[#87867f] border border-[#e3dacc]">
                  Cross-Channel De-AI
                </span>
              </div>
              <button
                type="button"
                onClick={() => setHumanize(!humanize)}
                className={`px-3 py-1 rounded-full text-xs font-mono font-medium transition flex items-center gap-1.5 border shadow-sm ${
                  humanize
                    ? 'bg-[#c6613f] text-[#faf9f5] border-[#c6613f]'
                    : 'bg-[#f0eee6] text-[#87867f] border-[#e3dacc] hover:text-[#141413]'
                }`}
              >
                <span>🪄 Humanize Polish</span>
                <span className={`px-1.5 py-0.2 rounded text-[10px] font-bold ${humanize ? 'bg-[#faf9f5]/20 text-[#faf9f5]' : 'bg-[#e3dacc] text-[#87867f]'}`}>
                  {humanize ? 'ON' : 'OFF'}
                </span>
              </button>
            </div>

            {humanize && (
              <div className="pt-2 border-t border-[#e3dacc]/60 flex items-center gap-1.5 flex-wrap">
                <span className="text-[11px] font-mono text-[#87867f] mr-1">Tone:</span>
                {HUMANIZE_TONES.map(t => {
                  const active = humanizeTone === t.id
                  return (
                    <button
                      key={t.id}
                      type="button"
                      onClick={() => setHumanizeTone(t.id)}
                      className={`px-2.5 py-1 rounded-full text-[11px] font-mono border transition ${
                        active
                          ? 'bg-[#141413] text-[#faf9f5] border-[#141413] shadow-sm font-semibold'
                          : 'bg-[#f0eee6] text-[#87867f] hover:text-[#141413] border-[#e3dacc]'
                      }`}
                    >
                      {t.label}
                    </button>
                  )
                })}
              </div>
            )}
          </div>

          {error && (
            <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-800 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
              <span>{error}</span>
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 px-4 bg-[#141413] hover:bg-[#252524] disabled:opacity-50 text-[#faf9f5] rounded-full text-xs font-medium transition flex items-center justify-center gap-2 shadow-sm"
          >
            {loading ? <RotateCw className="w-3.5 h-3.5 animate-spin" /> : <Share2 className="w-3.5 h-3.5 text-[#d97757]" />}
            <span>{loading ? 'Synthesizing Platform Derivatives...' : `Generate Platform Bundle (${activeFormatKeys.length} Formats)`}</span>
          </button>
        </form>

        {/* Output Channel Previews */}
        <div className="space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-[#e3dacc]">
            <h3 className="text-xs uppercase font-mono tracking-wider text-[#87867f]">Derivative Formats</h3>
            {bundle && (
              <span className="text-[11px] font-mono text-[#c6613f]">Saved to /projects/{slug}/distribution/</span>
            )}
          </div>

          {!bundle && !loading && (
            <div className="border border-dashed border-[#b0aea5] rounded-2xl p-12 text-center text-[#87867f] bg-[#f0eee6]/30">
              <Share2 className="w-8 h-8 mx-auto mb-3 stroke-1 text-[#b0aea5]" />
              <p className="text-sm font-medium text-[#141413]">No derivatives generated yet.</p>
              <p className="text-xs text-[#87867f] mt-1">Submit anchor text to generate LinkedIn post, X thread, video scripts, and newsletter.</p>
            </div>
          )}

          {loading && (
            <div className="border border-[#e3dacc] rounded-2xl p-12 text-center text-[#87867f] space-y-3 bg-[#f0eee6]/50 shadow-anthropic">
              <RotateCw className="w-6 h-6 mx-auto animate-spin text-[#c6613f]" />
              <p className="text-sm font-medium text-[#141413]">Generating Enabled Platform Derivatives...</p>
              <p className="text-xs text-[#87867f] font-mono">Enforcing strict groundedness (zero new facts)</p>
            </div>
          )}

          {bundle && (
            <div className="space-y-4">
              {/* Channel Switcher */}
              <div className="flex items-center justify-between bg-[#f0eee6] p-1 rounded-full border border-[#e3dacc] overflow-x-auto shadow-anthropic">
                <div className="flex items-center gap-1">
                  {availableFormats.map(fmt => {
                    const isActive = activeFormat === fmt.id || (fmt.id === 'video_script_short' && activeFormat === 'video_script')
                    const isLinkedIn = fmt.id === 'linkedin'
                    return (
                      <button
                        key={fmt.id}
                        onClick={() => setActiveFormat(fmt.id)}
                        className={`px-3.5 py-1.5 rounded-full text-xs font-mono transition flex items-center gap-1.5 whitespace-nowrap ${
                          isActive
                            ? 'bg-[#141413] text-[#faf9f5] shadow-sm'
                            : 'text-[#87867f] hover:text-[#141413]'
                        }`}
                      >
                        {isLinkedIn && <span className="w-1.5 h-1.5 rounded-full bg-[#d97757]" />}
                        <span>{fmt.shortLabel}</span>
                      </button>
                    )
                  })}
                </div>

                <button
                  onClick={() => handleCopy(getFormatContent(activeFormat))}
                  className="flex items-center gap-1.5 px-3 py-1 text-xs font-mono bg-[#faf9f5] hover:bg-[#e3dacc]/50 text-[#141413] rounded-full border border-[#e3dacc] transition shrink-0 ml-2"
                >
                  {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5 text-[#87867f]" />}
                  <span>{copied ? 'Copied!' : 'Copy'}</span>
                </button>
              </div>

              {/* Text Preview Box */}
              <div className="bg-[#faf9f5] border border-[#e3dacc] rounded-2xl p-6 font-mono text-xs text-[#141413] leading-relaxed max-h-[480px] overflow-y-auto whitespace-pre-wrap shadow-anthropic">
                {getFormatContent(activeFormat) || 'No content available for this format.'}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Platform Configuration Modal */}
      {showConfigModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#141413]/60 backdrop-blur-sm animate-fadeIn">
          <div className="bg-[#faf9f5] border border-[#e3dacc] rounded-2xl w-full max-w-lg overflow-hidden shadow-2xl space-y-0">
            {/* Modal Header */}
            <div className="p-5 border-b border-[#e3dacc] flex items-center justify-between">
              <div>
                <h3 className="font-serif text-base font-semibold text-[#141413] flex items-center gap-2">
                  <Sliders className="w-4 h-4 text-[#c6613f]" />
                  <span>Platform Distribution Formats</span>
                </h3>
                <p className="text-xs text-[#87867f] mt-0.5">
                  Select which platforms to generate. LinkedIn is set as default.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setShowConfigModal(false)}
                className="p-1 rounded-full text-[#87867f] hover:text-[#141413] hover:bg-[#f0eee6] transition"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Platform Options List */}
            <div className="p-5 space-y-3 max-h-[60vh] overflow-y-auto">
              {DISTRIBUTION_FORMATS.map(fmt => {
                const isEnabled = enabledFormats[fmt.id]
                return (
                  <div
                    key={fmt.id}
                    onClick={() => toggleFormat(fmt.id)}
                    className={`p-4 rounded-xl border transition cursor-pointer flex items-start gap-3.5 ${
                      isEnabled
                        ? 'bg-[#f0eee6] border-[#b0aea5]'
                        : 'bg-[#faf9f5] border-[#e3dacc] opacity-60'
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={isEnabled}
                      onChange={() => {}}
                      className="mt-1 rounded text-[#141413] focus:ring-0 focus:outline-none"
                    />
                    <div className="flex-1 space-y-1">
                      <div className="flex items-center justify-between">
                        <span className={`text-xs font-medium ${isEnabled ? 'text-[#141413]' : 'text-[#87867f]'}`}>
                          {fmt.label}
                        </span>
                        <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full border ${fmt.tagColor}`}>
                          {fmt.tag}
                        </span>
                      </div>
                      <p className="text-[11px] text-[#87867f] leading-normal">
                        {fmt.desc}
                      </p>
                    </div>
                  </div>
                )
              })}
            </div>

            {/* Modal Footer */}
            <div className="p-4 bg-[#f0eee6] border-t border-[#e3dacc] flex items-center justify-between">
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={selectAllFormats}
                  className="text-[11px] font-mono text-[#87867f] hover:text-[#141413] px-2 py-1 rounded hover:bg-[#e3dacc]/50 transition"
                >
                  Select All
                </button>
                <span className="text-[#b0aea5]">•</span>
                <button
                  type="button"
                  onClick={resetDefaultFormats}
                  className="text-[11px] font-mono text-[#87867f] hover:text-[#141413] px-2 py-1 rounded hover:bg-[#e3dacc]/50 transition"
                >
                  Reset Defaults
                </button>
              </div>

              <button
                type="button"
                onClick={() => setShowConfigModal(false)}
                className="px-5 py-2 bg-[#141413] hover:bg-[#252524] text-[#faf9f5] rounded-full text-xs font-medium transition shadow-sm"
              >
                Apply & Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// ==========================================
// 3. LESSONS TAB (Governed Memory & Diff)
// ==========================================
function LessonsTab() {
  const [activeRules, setActiveRules] = useState([])
  const [pendingRules, setPendingRules] = useState([])
  const [draftText, setDraftText] = useState('')
  const [pubText, setPubText] = useState('')
  const [proposals, setProposals] = useState([])
  const [loadingDiff, setLoadingDiff] = useState(false)
  const [error, setError] = useState('')
  const [customRuleText, setCustomRuleText] = useState('')
  const [loadingCustom, setLoadingCustom] = useState(false)
  const [customSuccess, setCustomSuccess] = useState('')

  const fetchLessons = async () => {
    try {
      const data = await getLessons()
      setActiveRules(data.rules || [])
      setPendingRules(data.pending || [])
    } catch {}
  }

  const handleAddCustomRule = async (e) => {
    e.preventDefault()
    if (!customRuleText.trim()) return
    setLoadingCustom(true)
    setError('')
    setCustomSuccess('')

    try {
      await addCustomLesson({
        rule_text: customRuleText.trim(),
        provenance_project: 'manual',
        auto_approve: true,
      })
      setCustomRuleText('')
      setCustomSuccess('Rule active in Council loop!')
      setTimeout(() => setCustomSuccess(''), 3500)
      fetchLessons()
    } catch (err) {
      setError(err.message || 'Failed to add custom rule')
    } finally {
      setLoadingCustom(false)
    }
  }

  useEffect(() => {
    fetchLessons()
  }, [])

  const handleDiff = async (e) => {
    e.preventDefault()
    if (!draftText.trim() || !pubText.trim()) {
      setError('Both draft and published texts are required.')
      return
    }
    setLoadingDiff(true)
    setError('')
    setProposals([])

    try {
      const data = await diffLessons({ draft: draftText, published: pubText, project_id: 'ui-diff' })
      setProposals(data.rules || [])
    } catch (err) {
      setError(err.message || 'Diff extraction failed.')
    } finally {
      setLoadingDiff(false)
    }
  }

  const handleApprove = async (ruleId) => {
    try {
      await approveLesson(ruleId)
      fetchLessons()
      setProposals(prev => prev.filter(p => p.rule_id !== ruleId))
    } catch {}
  }

  const handleReject = async (ruleId) => {
    try {
      await rejectLesson(ruleId)
      fetchLessons()
      setProposals(prev => prev.filter(p => p.rule_id !== ruleId))
    } catch {}
  }

  return (
    <div className="space-y-8 animate-fadeIn">
      <div className="border-b border-[#e3dacc] pb-5">
        <h2 className="font-serif text-2xl font-medium tracking-tight text-[#141413]">Editorial Lessons</h2>
        <p className="text-sm text-[#87867f] mt-1 font-sans">
          Codified writing rules and approved stylistic constraints.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-start">
        {/* Left Column: Direct Add + Diff Extractor */}
        <div className="space-y-6">
          {/* Add Custom Rule Card */}
          <form onSubmit={handleAddCustomRule} className="space-y-3 bg-[#f0eee6]/60 p-5 rounded-2xl border border-[#e3dacc] shadow-anthropic">
            <div className="flex items-center justify-between">
              <h3 className="text-xs uppercase font-mono tracking-wider text-[#87867f]">Add Custom Writing Rule</h3>
              <span className="text-[10px] font-mono text-[#c6613f] bg-[#c6613f]/10 px-2 py-0.5 rounded-full border border-[#c6613f]/20">
                Instant Governance
              </span>
            </div>
            <div>
              <label className="block text-[11px] font-mono text-[#87867f] mb-1">Declarative Rule (Injected directly into Council drafter)</label>
              <textarea
                rows={2}
                value={customRuleText}
                onChange={(e) => setCustomRuleText(e.target.value)}
                placeholder="e.g. Never open with buzzwords or greetings. Start immediately on what failed in production."
                className="w-full text-xs font-mono bg-[#faf9f5] border border-[#e3dacc] rounded-xl p-3 text-[#141413] focus:outline-none focus:border-[#141413] placeholder-[#b0aea5]"
              />
            </div>
            {customSuccess && (
              <div className="p-2.5 bg-emerald-50 text-emerald-800 text-xs rounded-xl border border-emerald-200 flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5 shrink-0 text-emerald-600" />
                <span>{customSuccess}</span>
              </div>
            )}
            <button
              type="submit"
              disabled={loadingCustom || !customRuleText.trim()}
              className="w-full py-2.5 px-4 bg-[#141413] hover:bg-[#252524] disabled:opacity-50 text-[#faf9f5] rounded-full text-xs font-medium transition flex items-center justify-center gap-2 shadow-sm"
            >
              {loadingCustom ? <RotateCw className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5 text-[#d97757]" />}
              <span>{loadingCustom ? 'Saving & Activating...' : 'Save & Activate Rule'}</span>
            </button>
          </form>

          {/* Diff Extractor Form */}
          <div className="space-y-4 bg-[#f0eee6]/60 p-5 rounded-2xl border border-[#e3dacc] shadow-anthropic">
            <h3 className="text-xs uppercase font-mono tracking-wider text-[#87867f]">Diff Extractor (Draft vs Published)</h3>

            <div className="space-y-3">
              <div>
                <label className="block text-[11px] font-mono text-[#87867f] mb-1">Original Draft (AI generated)</label>
                <textarea
                  rows={5}
                  value={draftText}
                  onChange={(e) => setDraftText(e.target.value)}
                  placeholder="Paste AI generated draft..."
                  className="w-full text-xs font-mono bg-[#faf9f5] border border-[#e3dacc] rounded-xl p-3 text-[#141413] focus:outline-none focus:border-[#141413] placeholder-[#b0aea5]"
                />
              </div>

              <div>
                <label className="block text-[11px] font-mono text-[#87867f] mb-1">Published Text (Operator final edit)</label>
                <textarea
                  rows={5}
                  value={pubText}
                  onChange={(e) => setPubText(e.target.value)}
                  placeholder="Paste published final version..."
                  className="w-full text-xs font-mono bg-[#faf9f5] border border-[#e3dacc] rounded-xl p-3 text-[#141413] focus:outline-none focus:border-[#141413] placeholder-[#b0aea5]"
                />
              </div>

              {error && (
                <div className="p-2.5 bg-rose-50 text-rose-800 text-xs rounded-xl border border-rose-200">{error}</div>
              )}

              <button
                onClick={handleDiff}
                disabled={loadingDiff}
                className="w-full py-2.5 px-4 bg-[#141413] hover:bg-[#252524] disabled:opacity-50 text-[#faf9f5] rounded-full text-xs font-medium transition flex items-center justify-center gap-2 shadow-sm"
              >
                {loadingDiff ? <RotateCw className="w-3.5 h-3.5 animate-spin" /> : <BookOpen className="w-3.5 h-3.5 text-[#d97757]" />}
                <span>{loadingDiff ? 'Analyzing Diff Patterns...' : 'Extract Declarative Rules'}</span>
              </button>
            </div>

            {/* Proposals / Review Queue */}
            {proposals.length > 0 && (
              <div className="mt-4 pt-4 border-t border-[#e3dacc] space-y-3">
                <h4 className="text-xs font-mono uppercase text-[#87867f]">Proposed Rules Pending Approval</h4>
                {proposals.map((prop, idx) => (
                  <div key={idx} className="bg-[#faf9f5] p-3.5 rounded-xl border border-[#e3dacc] space-y-2">
                    <p className="text-xs text-[#141413] font-medium">{prop.rule}</p>
                    
                    {prop.is_conflict && (
                      <div className="flex items-center gap-1.5 text-[11px] text-[#c6613f] bg-[#c6613f]/10 p-2 rounded-lg border border-[#c6613f]/20 font-mono">
                        <ShieldAlert className="w-3.5 h-3.5 shrink-0" />
                        <span>Potential conflict with existing rule #{prop.conflict_rule_id}</span>
                      </div>
                    )}

                    {prop.merge_required && (
                      <div className="flex items-center gap-1.5 text-[11px] text-rose-800 bg-rose-50 p-2 rounded-lg border border-rose-200 font-mono">
                        <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                        <span>Rule cap reached (150 rules). Merge pass recommended.</span>
                      </div>
                    )}

                    <div className="flex justify-end gap-2 pt-1">
                      <button
                        onClick={() => handleReject(prop.rule_id)}
                        className="px-3 py-1 text-[11px] font-mono text-[#87867f] hover:text-[#141413] hover:bg-[#e3dacc]/50 rounded-full transition"
                      >
                        Reject
                      </button>
                      <button
                        onClick={() => handleApprove(prop.rule_id)}
                        className="px-3.5 py-1 text-[11px] font-mono text-[#faf9f5] bg-emerald-700 hover:bg-emerald-600 rounded-full transition shadow-sm"
                      >
                        Approve Rule
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Pending Review Queue + Active Rules List */}
        <div className="space-y-6">
          {/* Pending Approval Queue from DB */}
          {pendingRules.length > 0 && (
            <div className="space-y-3 bg-[#c6613f]/5 p-5 rounded-2xl border border-[#c6613f]/30 shadow-anthropic">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-[#c6613f] animate-pulse" />
                  <h3 className="text-xs uppercase font-mono tracking-wider text-[#c6613f] font-semibold">
                    Governance Review Queue ({pendingRules.length} Pending)
                  </h3>
                </div>
                <span className="text-[10px] font-mono text-[#87867f]">Human Approval Gate</span>
              </div>
              <p className="text-[11px] text-[#87867f] font-sans">
                Extracted declarative rules must be approved before injection into the Writer's Council loop.
              </p>
              <div className="space-y-2.5 pt-1">
                {pendingRules.map((rule) => (
                  <div key={rule.id} className="bg-[#faf9f5] border border-[#e3dacc] rounded-xl p-3.5 space-y-2.5 shadow-sm">
                    <div className="flex items-center justify-between text-[10px] font-mono text-[#87867f]">
                      <span className="font-semibold text-[#141413]">Pending Rule #{rule.id}</span>
                      <span className="bg-[#f0eee6] px-1.5 py-0.5 rounded text-[#141413]">{rule.provenance_project || 'diff'}</span>
                    </div>
                    <p className="text-xs text-[#141413] font-serif leading-relaxed">{rule.rule_text}</p>
                    <div className="flex justify-end gap-2 pt-1 border-t border-[#e3dacc]/60">
                      <button
                        type="button"
                        onClick={() => handleReject(rule.id)}
                        className="px-3 py-1 text-[11px] font-mono text-[#87867f] hover:text-rose-700 hover:bg-rose-50 rounded-full transition"
                      >
                        Reject
                      </button>
                      <button
                        type="button"
                        onClick={() => handleApprove(rule.id)}
                        className="px-3.5 py-1 text-[11px] font-mono text-[#faf9f5] bg-emerald-700 hover:bg-emerald-600 rounded-full transition shadow-sm flex items-center gap-1"
                      >
                        <Check className="w-3 h-3" />
                        <span>Approve Rule</span>
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Active Rules List */}
          <div className="space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-[#e3dacc]">
              <h3 className="text-xs uppercase font-mono tracking-wider text-[#87867f]">Active Governed Rules ({activeRules.length})</h3>
              <button onClick={fetchLessons} className="text-xs text-[#87867f] hover:text-[#141413] font-mono flex items-center gap-1">
                <RotateCw className="w-3 h-3" />
                <span>refresh</span>
              </button>
            </div>

          <div className="space-y-2.5 max-h-[600px] overflow-y-auto pr-1">
            {activeRules.length === 0 ? (
              <div className="border border-dashed border-[#b0aea5] rounded-2xl p-8 text-center text-[#87867f] bg-[#f0eee6]/30">
                <p className="text-xs">No active lessons codified yet.</p>
              </div>
            ) : (
              activeRules.map((rule) => (
                <div key={rule.id} className="bg-[#faf9f5] border border-[#e3dacc] rounded-xl p-3.5 space-y-1 shadow-anthropic">
                  <div className="flex items-center justify-between text-[10px] font-mono text-[#87867f]">
                    <span>#{rule.id}</span>
                    <span className="bg-[#f0eee6] px-1.5 py-0.5 rounded text-[#141413]">{rule.provenance_project || 'manual'}</span>
                  </div>
                  <p className="text-xs text-[#141413] font-serif leading-relaxed">{rule.rule_text}</p>
                </div>
              ))
            )}
          </div>
        </div>
        </div>
      </div>
    </div>
  )
}



