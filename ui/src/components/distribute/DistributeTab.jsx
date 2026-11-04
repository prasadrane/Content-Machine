import React, { useEffect, useState } from 'react'
import { Sliders, History } from 'lucide-react'
import { useDistributionSession } from './useDistributionSession'
import { DISTRIBUTION_FORMATS } from '../../lib/constants'
import { useCopyToClipboard } from '../../hooks/useCopyToClipboard'
import AnchorForm from './AnchorForm'
import OutputPreviews from './OutputPreviews'
import PlatformConfigModal from './PlatformConfigModal'
import DistributeHistoryDrawer from './DistributeHistoryDrawer'

export default function DistributeTab(props) {
  const session = useDistributionSession(props)
  const { anchor, output, loading, error, reviewed, setReviewed, isApproved, approveCurrent,
    historyItems, historyLoading, activeFormat, setActiveFormat } = session
  const anchorText = anchor.text
  const slug = anchor.slug
  const bundle = output?.data
  const { copied, copy } = useCopyToClipboard()
  const [showConfigModal, setShowConfigModal] = useState(false)
  const [showHistoryDrawer, setShowHistoryDrawer] = useState(false)
  useEffect(() => {
    if (props.isActive === false) { setShowConfigModal(false); setShowHistoryDrawer(false) }
  }, [props.isActive])
  const [humanize, setHumanize] = useState(true)
  const [humanizeTone, setHumanizeTone] = useState('pragmatic_architect')
  const [enabledFormats, setEnabledFormats] = useState({ linkedin: true, x_thread: true, video_script_short: true, video_script_long: false, newsletter: true })
  const handleSelectHistoryItem = item => { session.selectHistory(item); setShowHistoryDrawer(false) }
  const toggleFormat = (id) => {
    setEnabledFormats(prev => {
      const next = { ...prev, [id]: !prev[id] }
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
  const handleGenerate = event => session.generate(event, { enabled_formats: activeFormatKeys, humanize, tone: humanizeTone })
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
            Generate channel-native formats from text you explicitly approve.
          </p>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2.5 self-start sm:self-auto flex-wrap">
          <button
            type="button"
            onClick={() => setShowHistoryDrawer(true)}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-xs font-mono bg-[#faf9f5] border border-[#e3dacc] hover:border-[#b0aea5] hover:text-[#141413] text-[#87867f] transition shadow-anthropic"
          >
            <History className="w-3.5 h-3.5 text-[#c6613f]" />
            <span>History ({historyItems.length})</span>
          </button>

          <button
            type="button"
            onClick={() => setShowConfigModal(true)}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-xs font-mono bg-[#f0eee6] border border-[#e3dacc] hover:border-[#b0aea5] text-[#141413] transition shadow-anthropic"
          >
            <Sliders className="w-3.5 h-3.5 text-[#c6613f]" />
            <span>Platforms ({activeFormatKeys.length}/5)</span>
          </button>
        </div>
      </div>

      {bundle?.replayed && (
        <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-amber-900 text-xs">
          Replayed sample output: live model quota was unavailable, so these are stored derivatives of a seeded post, not generated from your text.
        </div>
      )}

      {/* Main Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-start">
        <AnchorForm
          anchorText={anchorText}
          onAnchorChange={session.editText}
          slug={slug}
          onSlugChange={session.editSlug}
          enabledFormats={enabledFormats}
          onToggleFormat={toggleFormat}
          onOpenConfig={() => setShowConfigModal(true)}
          humanize={humanize}
          onHumanizeToggle={() => setHumanize(!humanize)}
          humanizeTone={humanizeTone}
          onToneChange={setHumanizeTone}
          loading={loading}
          error={error}
          onSubmit={handleGenerate}
          activeFormatCount={activeFormatKeys.length}
          isApproved={isApproved}
          reviewed={reviewed}
          onReviewedChange={setReviewed}
          onApprove={approveCurrent}
        />

        <OutputPreviews
          bundle={bundle}
          anchorSnapshot={output?.anchor}
          isEarlier={session.isEarlier}
          origin={output?.origin}
          loading={loading}
          slug={output?.anchor.slug || slug}
          availableFormats={availableFormats}
          activeFormat={activeFormat}
          onFormatChange={setActiveFormat}
          copied={copied}
          onCopy={handleCopy}
          getFormatContent={getFormatContent}
        />
      </div>

      <PlatformConfigModal
        show={showConfigModal}
        onClose={() => setShowConfigModal(false)}
        enabledFormats={enabledFormats}
        onToggleFormat={toggleFormat}
        onSelectAll={selectAllFormats}
        onResetDefaults={resetDefaultFormats}
      />

      <DistributeHistoryDrawer
        show={showHistoryDrawer}
        onClose={() => setShowHistoryDrawer(false)}
        items={historyItems}
        loading={historyLoading}
        onSelect={handleSelectHistoryItem}
      />
    </div>
  )
}
