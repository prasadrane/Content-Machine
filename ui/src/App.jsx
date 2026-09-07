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
import OracleTab from './components/oracle/OracleTab'
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
// ==========================================\n