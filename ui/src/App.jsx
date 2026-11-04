import React, { useCallback, useEffect, useRef, useState } from 'react'
import TabBtn from './components/ui/TabBtn'
import DemoBanner from './components/DemoBanner'
import { TABS } from './app/tabs'
import { useServerHealth } from './app/useServerHealth'
import { useSharedFlow } from './app/useSharedFlow'
import WorkspaceEntry from './components/WorkspaceEntry'
import SampleStory from './components/SampleStory'

export default function App() {
  const [activeTab, setActiveTab] = useState('oracle')
  const [visitedTabs, setVisitedTabs] = useState(['oracle'])
  const [showSample, setShowSample] = useState(false)
  const workspaceRef = useRef(null)
  const navigate = useCallback((id) => {
    setVisitedTabs(previous => previous.includes(id) ? previous : [...previous, id])
    setShowSample(false)
    setActiveTab(id)
  }, [])
  const serverOnline = useServerHealth()
  const shared = useSharedFlow(navigate)
  useEffect(() => {
    workspaceRef.current?.focus({ preventScroll: true })
  }, [activeTab, showSample])

  return (
    <div className="min-h-screen w-full bg-[#faf9f5] text-[#141413] flex flex-col font-sans selection:bg-[#c6613f]/20 selection:text-[#c6613f]">
      <DemoBanner
        activeTab={activeTab}
        approved={Boolean(shared.approvedText)}
        onGoto={navigate}
        onStart={() => setShowSample(true)}
      />
      {/* Minimalist Editorial Navigation Header */}
      <header className="border-b border-[#e3dacc]/70 bg-[#faf9f5]/85 backdrop-blur-md sticky top-0 z-40 transition-colors w-full">
        <div className="max-w-7xl w-full mx-auto px-4 sm:px-6 py-3 flex flex-wrap items-center justify-between gap-3">
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
          <nav className="flex flex-wrap items-center gap-1 sm:gap-1.5 order-3 w-full md:order-none md:w-auto" aria-label="Main Navigation">
            {TABS.map(({ id, label }) => (
              <TabBtn
                key={id}
                active={activeTab === id}
                onClick={() => navigate(id)}
                label={label}
              />
            ))}
          </nav>

          {/* Minimal Live Status */}
          <div className="flex items-center gap-1.5 text-xs text-[#87867f] font-mono">
            <span className={`w-2 h-2 rounded-full ${serverOnline ? 'bg-emerald-600' : 'bg-[#c6613f]'}`} />
            <span className="text-[11px] hidden sm:inline">{serverOnline ? 'Online' : 'Offline'}</span>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main ref={workspaceRef} tabIndex={-1} aria-label={`${TABS.find(tab => tab.id === activeTab)?.label} workspace`} className="flex-1 min-w-0 max-w-7xl w-full mx-auto px-4 sm:px-6 py-6 sm:py-8">
        {showSample && <SampleStory onClose={() => setShowSample(false)} />}
        {activeTab === 'oracle' && !showSample && <WorkspaceEntry onNavigate={navigate} onSample={() => setShowSample(true)} />}
        {TABS.map(({ id, Component, getProps }) =>
          visitedTabs.includes(id) && (['oracle', 'council', 'distribute'].includes(id) || activeTab === id) ? (
            <section key={id} hidden={showSample || activeTab !== id}>
              <Component {...(getProps ? getProps(shared) : {})} isActive={!showSample && activeTab === id} />
            </section>
          ) : null
        )}
      </main>

      {/* Editorial Footer */}
      <footer className="border-t border-[#e3dacc]/60 py-6 text-center text-xs text-[#87867f] font-sans w-full bg-[#faf9f5]">
        <p>Content Machine</p>
      </footer>
    </div>
  )
}
