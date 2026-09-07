import React, { useState, useEffect } from 'react'
import { Sliders, History } from 'lucide-react'
import { runDistribute, getDistributeHistory } from '../../api/distribute'
import { DISTRIBUTION_FORMATS } from '../../lib/constants'
import { useCopyToClipboard } from '../../hooks/useCopyToClipboard'
import AnchorForm from './AnchorForm'
import OutputPreviews from './OutputPreviews'
import PlatformConfigModal from './PlatformConfigModal'
import DistributeHistoryDrawer from './DistributeHistoryDrawer'

export default function DistributeTab({ initialText, initialSlug }) {
  const [anchorText, setAnchorText] = useState(initialText || '')
  const [slug, setSlug] = useState(initialSlug || 'post-1')
  const [loading, setLoading] = useState(false)
  const [bundle, setBundle] = useState(null)
  const [error, setError] = useState('')
  const [activeFormat, setActiveFormat] = useState('linkedin')
  const { copied, copy } = useCopyToClipboard()
  const [showConfigModal, setShowConfigModal] = useState(false)
  const [showHistoryDrawer, setShowHistoryDrawer] = useState(false)
  const [historyItems, setHistoryItems] = useState([])
  const [historyLoading, setHistoryLoading] = useState(false)
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

  const fetchHistory = async () => {
    setHistoryLoading(true)
    try {
      const data = await getDistributeHistory()
      setHistoryItems(data?.items || [])
    } catch {
      // ignore
    } finally {
      setHistoryLoading(false)
    }
  }

  useEffect(() => {
    fetchHistory()
  }, [])

  const handleSelectHistoryItem = (item) => {
    if (!item) return
    if (item.anchor_text) {
      setAnchorText(item.anchor_text)
    }
    if (item.slug) {
      setSlug(item.slug)
    }
    if (item.has_bundle && item.bundle && Object.keys(item.bundle).length > 0) {
      setBundle(item.bundle)
      const priorityOrder = ['linkedin', 'x_thread', 'video_script_short', 'video_script', 'video_script_long', 'newsletter']
      const firstAvailable = priorityOrder.find(k => item.bundle[k])
      if (firstAvailable) {
        setActiveFormat(firstAvailable)
      }
    }
    setShowHistoryDrawer(false)
  }

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
      fetchHistory()

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

      {/* Main Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-start">
        <AnchorForm
          anchorText={anchorText}
          onAnchorChange={setAnchorText}
          slug={slug}
          onSlugChange={setSlug}
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
        />

        <OutputPreviews
          bundle={bundle}
          loading={loading}
          slug={slug}
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
