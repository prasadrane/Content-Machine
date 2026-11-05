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
    <div className="cm-page animate-fadeIn">
      {/* 1. Header */}
      <div className="cm-page-header">
        <div>
        {hasChanges && (
          <div className="mb-2">
            <span className="cm-badge cm-status-warning">
              Unsaved Changes
            </span>
          </div>
        )}
        <h2 className="cm-page-title">
          Author Voice &amp; Profile
        </h2>
        <p className="cm-page-description">
          Codified engineering persona, active upskilling focus, and non-negotiable voice invariants.
        </p>
        </div>
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
              <div className="cm-status cm-status-error flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
                <span>{error}</span>
              </div>
            )}

            {saveSuccess && (
              <div className="cm-status cm-status-success flex items-center gap-2 animate-fadeIn">
                <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-600" />
                <span>Voice profile saved &amp; synced with active editorial pipeline!</span>
              </div>
            )}

            <button
              type="button"
              onClick={handleSave}
              disabled={saving || loading}
              className="cm-button cm-button-primary w-full"
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
          <div className="cm-panel space-y-4">
            <div className="cm-panel-header flex flex-wrap items-start justify-between gap-3">
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="cm-panel-title">
                    Live Voice Guide Preview
                  </h3>
                  <span className="cm-badge font-mono">
                    02_voice-guide.md
                  </span>
                </div>
                <p className="cm-muted mt-1">
                  Exact context injected into editorial &amp; council models
                </p>
              </div>

              <div className="flex items-center gap-2 shrink-0">
                <button
                  type="button"
                  onClick={handleCopyMarkdown}
                  className="cm-icon-button"
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
                  className="cm-icon-button"
                  title="Refresh voice guide from backend"
                >
                  <RotateCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin text-[#c6613f]' : ''}`} />
                </button>
              </div>
            </div>

            {/* Markdown Preview Content */}
            {loading && !profile ? (
              <div className="cm-empty animate-pulse">
                Loading active voice guide...
              </div>
            ) : (
              <div className="cm-subpanel text-base font-mono leading-relaxed max-h-[720px] overflow-y-auto whitespace-pre-wrap break-words select-text">
                {profile?.full_markdown || '// Voice guide markdown will load here'}
              </div>
            )}

            <div className="flex flex-wrap items-center justify-between gap-2 cm-muted pt-1">
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
