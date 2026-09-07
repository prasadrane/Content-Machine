import React, { useState, useEffect } from 'react'
import {
  AlertCircle,
  CheckCircle2,
  RotateCw,
  Save,
  Copy,
  Check,
} from 'lucide-react'
import { getProfile, saveProfile } from '../../api/profile'
import { CORE_VOICE_INVARIANTS } from '../../lib/constants'
import { useCopyToClipboard } from '../../hooks/useCopyToClipboard'
import IdentityCard from './IdentityCard'
import DomainsEditor from './DomainsEditor'
import InvariantsDisplay from './InvariantsDisplay'

export default function ProfileTab() {
  const [profile, setProfile] = useState(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [saveSuccess, setSaveSuccess] = useState(false)
  const { copied: copiedMarkdown, copy } = useCopyToClipboard()

  // Form state
  const [currentFocus, setCurrentFocus] = useState('')
  const [technicalDomains, setTechnicalDomains] = useState([])
  const [newDomainInput, setNewDomainInput] = useState('')

  const fetchProfile = async (isManualRefresh = false) => {
    if (isManualRefresh) setRefreshing(true)
    else setLoading(true)
    setError('')

    try {
      const data = await getProfile()
      setProfile(data)
      setCurrentFocus(data.current_focus || '')
      setTechnicalDomains(data.technical_domains || [])
    } catch (err) {
      setError(err.message || 'Failed to load author profile.')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => {
    fetchProfile()
  }, [])

  const handleSave = async (e) => {
    if (e) e.preventDefault()
    setSaving(true)
    setError('')
    setSaveSuccess(false)

    try {
      const data = await saveProfile({
        current_focus: currentFocus,
        technical_domains: technicalDomains,
      })
      setProfile(data)
      setCurrentFocus(data.current_focus || '')
      setTechnicalDomains(data.technical_domains || [])
      setSaveSuccess(true)
      setTimeout(() => setSaveSuccess(false), 4000)
    } catch (err) {
      setError(err.message || 'Failed to update voice profile.')
    } finally {
      setSaving(false)
    }
  }

  const handleAddDomain = (e) => {
    if (e) e.preventDefault()
    const trimmed = newDomainInput.trim()
    if (!trimmed) return
    if (!technicalDomains.some((d) => d.toLowerCase() === trimmed.toLowerCase())) {
      setTechnicalDomains([...technicalDomains, trimmed])
    }
    setNewDomainInput('')
  }

  const handleRemoveDomain = (domainToRemove) => {
    setTechnicalDomains(technicalDomains.filter((d) => d !== domainToRemove))
  }

  const handleDomainKeyDown = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      handleAddDomain()
    }
  }

  const handleCopyMarkdown = () => {
    if (!profile?.full_markdown) return
    copy(profile.full_markdown)
  }

  const hasChanges = profile && (
    currentFocus !== (profile.current_focus || '') ||
    JSON.stringify(technicalDomains) !== JSON.stringify(profile.technical_domains || [])
  )

  return (
    <div className="space-y-8 animate-fadeIn max-w-7xl mx-auto">
      {/* 1. Header */}
      <div className="border-b border-[#e3dacc] pb-5">
        {hasChanges && (
          <div className="mb-2">
            <span className="text-[10px] uppercase font-mono px-2.5 py-0.5 rounded-full bg-amber-50 text-amber-800 border border-amber-200">
              Unsaved Changes
            </span>
          </div>
        )}
        <h2 className="font-serif text-2xl font-medium tracking-tight text-[#141413]">
          Author Voice &amp; Profile
        </h2>
        <p className="text-sm text-[#87867f] mt-1 font-sans">
          Codified engineering persona, active upskilling focus, and non-negotiable voice invariants.
        </p>
      </div>

      {/* Main Two-Column Layout */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-start">
        {/* Left Column: Structured Profile Controls */}
        <div className="space-y-6">
          <IdentityCard
            profile={profile}
            currentFocus={currentFocus}
            onFocusChange={setCurrentFocus}
            onSave={handleSave}
            saving={saving}
            saveSuccess={saveSuccess}
            error={error}
            hasChanges={hasChanges}
            loading={loading}
          />

          <DomainsEditor
            domains={technicalDomains}
            onAdd={handleAddDomain}
            onRemove={handleRemoveDomain}
            newDomainInput={newDomainInput}
            onInputChange={setNewDomainInput}
            onKeyDown={handleDomainKeyDown}
          />

          <InvariantsDisplay invariants={CORE_VOICE_INVARIANTS} />

          {/* Save Action & Feedback */}
          <div className="space-y-3">
            {error && (
              <div className="p-3 bg-rose-50 text-rose-800 text-xs rounded-xl border border-rose-200 flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
                <span>{error}</span>
              </div>
            )}

            {saveSuccess && (
              <div className="p-3 bg-emerald-50 text-emerald-800 text-xs rounded-xl border border-emerald-200 flex items-center gap-2 animate-fadeIn">
                <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-600" />
                <span>Voice profile saved &amp; synced with active editorial pipeline!</span>
              </div>
            )}

            <button
              type="button"
              onClick={handleSave}
              disabled={saving || loading}
              className={`w-full py-3 px-5 rounded-full text-xs font-medium transition flex items-center justify-center gap-2 shadow-sm ${
                hasChanges
                  ? 'bg-[#c6613f] hover:bg-[#a54c2d] text-[#faf9f5]'
                  : 'bg-[#141413] hover:bg-[#252524] text-[#faf9f5]'
              } disabled:opacity-50`}
            >
              {saving ? (
                <>
                  <RotateCw className="w-3.5 h-3.5 animate-spin" />
                  <span>Saving &amp; Syncing Voice Profile...</span>
                </>
              ) : (
                <>
                  <Save className="w-3.5 h-3.5 text-[#faf9f5]" />
                  <span>Save &amp; Sync Voice Profile</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Right Column: Live Voice Guide Markdown Preview */}
        <div className="space-y-4">
          <div className="bg-[#f0eee6]/60 border border-[#e3dacc] rounded-2xl p-5 sm:p-6 space-y-4 shadow-anthropic">
            <div className="flex items-center justify-between gap-3 border-b border-[#e3dacc]/80 pb-3.5">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-xs uppercase font-mono tracking-wider text-[#87867f] font-semibold">
                    Live Voice Guide Preview
                  </h3>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-[#faf9f5] text-[#141413] border border-[#e3dacc]">
                    02_voice-guide.md
                  </span>
                </div>
                <p className="text-[11px] text-[#87867f] font-sans mt-0.5">
                  Exact context injected into editorial &amp; council models
                </p>
              </div>

              <div className="flex items-center gap-2 shrink-0">
                <button
                  type="button"
                  onClick={handleCopyMarkdown}
                  className="p-1.5 text-[#87867f] hover:text-[#141413] hover:bg-[#e3dacc]/50 rounded-full transition"
                  title="Copy markdown"
                >
                  {copiedMarkdown ? (
                    <Check className="w-3.5 h-3.5 text-emerald-600" />
                  ) : (
                    <Copy className="w-3.5 h-3.5" />
                  )}
                </button>
                <button
                  type="button"
                  onClick={() => fetchProfile(true)}
                  disabled={refreshing || loading}
                  className="p-1.5 text-[#87867f] hover:text-[#141413] hover:bg-[#e3dacc]/50 rounded-full transition disabled:opacity-50"
                  title="Refresh voice guide from backend"
                >
                  <RotateCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin text-[#c6613f]' : ''}`} />
                </button>
              </div>
            </div>

            {/* Markdown Preview Content */}
            {loading && !profile ? (
              <div className="bg-[#faf9f5] border border-[#e3dacc] rounded-2xl p-8 text-center text-[#87867f] font-mono text-xs animate-pulse">
                Loading active voice guide...
              </div>
            ) : (
              <div className="bg-[#faf9f5] border border-[#e3dacc] rounded-2xl p-5 font-mono text-xs text-[#141413] leading-relaxed max-h-[720px] overflow-y-auto whitespace-pre-wrap select-text shadow-xs">
                {profile?.full_markdown || '// Voice guide markdown will load here'}
              </div>
            )}

            <div className="flex items-center justify-between text-[10px] font-mono text-[#87867f] pt-1">
              <span>
                Length: {profile?.full_markdown ? `${profile.full_markdown.length} chars | ${profile.full_markdown.split('\n').length} lines` : '-'}
              </span>
              <span>
                Source: knowledge/02_voice-guide.md
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
