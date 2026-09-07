import React, { useState, useEffect } from 'react'
import { Sliders } from 'lucide-react'
import { runDistribute } from '../../api/distribute'
import { DISTRIBUTION_FORMATS } from '../../lib/constants'
import { useCopyToClipboard } from '../../hooks/useCopyToClipboard'
import AnchorForm from './AnchorForm'
import OutputPreviews from './OutputPreviews'
import PlatformConfigModal from './PlatformConfigModal'

export default function DistributeTab({ initialText, initialSlug }) {
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
    </div>
  )
}
