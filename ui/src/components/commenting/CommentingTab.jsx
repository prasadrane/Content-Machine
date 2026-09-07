import React, { useState, useEffect } from 'react'
import { generateComments, getCommentsHistory } from '../../api/comments'
import { useVoiceRecording } from '../../hooks/useVoiceRecording'
import { useCopyToClipboard } from '../../hooks/useCopyToClipboard'
import InputPanel from './InputPanel'
import PolishCard from './PolishCard'
import CommentsHistory from './CommentsHistory'

export default function CommentingTab() {
  const [postContent, setPostContent] = useState('')
  const [angle, setAngle] = useState('insightful')
  const [perspectiveText, setPerspectiveText] = useState('')
  const [humanize, setHumanize] = useState(true)
  const [humanizeTone, setHumanizeTone] = useState('punchy_direct')
  const [loading, setLoading] = useState(false)
  const [deliberationPhase, setDeliberationPhase] = useState('')
  const [error, setError] = useState('')
  const [currentResult, setCurrentResult] = useState(null)
  const [accordionOpen, setAccordionOpen] = useState(true)
  const [history, setHistory] = useState([])
  const [historyLoading, setHistoryLoading] = useState(false)
  const [showHistory, setShowHistory] = useState(true)
  const [historyCopiedId, setHistoryCopiedId] = useState(null)

  const { copied, copy: copyToClipboard } = useCopyToClipboard()

  const [recordingSeconds, setRecordingSeconds] = useState(0)
  const {
    startRecording: startVoiceRecording,
    isRecording,
    isTranscribing,
    error: recordingError,
    setError: setRecordingError,
  } = useVoiceRecording({
    onTranscript: (text) => setPerspectiveText((prev) => (prev ? prev.trim() + ' ' + text : text)),
    onSecondTick: (seconds) => setRecordingSeconds(seconds),
  })

  const formatTimer = (seconds) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const fetchHistory = async () => {
    setHistoryLoading(true)
    try {
      const data = await getCommentsHistory(50)
      setHistory(data?.items || [])
    } catch (err) {
      console.warn('Could not fetch comments history:', err)
    } finally {
      setHistoryLoading(false)
    }
  }

  useEffect(() => {
    fetchHistory()
  }, [])

  const handleGenerate = async (e) => {
    if (e) e.preventDefault()
    if (!postContent.trim() || postContent.trim().length < 10) {
      setError('LinkedIn post content must be at least 10 characters long.')
      return
    }

    setLoading(true)
    setError('')
    setCurrentResult(null)

    const phases = [
      'Drafting candidate perspectives based on selected angle...',
      "Writer's Council convening: Perell, Puri, Housel & Slop Allergist reviewing...",
      'Evaluating z-score consensus & zero-slop purity...',
      'Executing editorial polish and brevity calibration...',
    ]
    let phaseIdx = 0
    setDeliberationPhase(phases[0])
    const phaseInterval = setInterval(() => {
      phaseIdx = (phaseIdx + 1) % phases.length
      setDeliberationPhase(phases[phaseIdx])
    }, 2400)

    try {
      const data = await generateComments({
        post_content: postContent.trim(),
        angle: angle,
        perspective_text: perspectiveText.trim() || null,
        humanize: humanize,
        tone: humanizeTone,
      })
      setCurrentResult(data)
      setAccordionOpen(true)
      fetchHistory()
    } catch (err) {
      setError(err.message || 'Comment generation failed.')
    } finally {
      clearInterval(phaseInterval)
      setLoading(false)
    }
  }

  const handleLoadFromHistory = (item) => {
    setPostContent(item.post_content || item.post_excerpt || '')
    if (item.angle) setAngle(item.angle)
    if (item.perspective_text) setPerspectiveText(item.perspective_text)
    if (item.humanize_tone) setHumanizeTone(item.humanize_tone)
    if (typeof item.humanized === 'boolean') setHumanize(item.humanized)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const handleCopyHistory = async (text, id) => {
    try {
      await navigator.clipboard.writeText(text)
      if (id) {
        setHistoryCopiedId(id)
        setTimeout(() => setHistoryCopiedId(null), 2000)
      }
    } catch (err) {
      console.error('Failed to copy text:', err)
    }
  }

  return (
    <div className="space-y-8 animate-fadeIn max-w-4xl mx-auto">
      <div className="border-b border-[#e3dacc] pb-5">
        <h2 className="font-serif text-2xl font-medium tracking-tight text-[#141413]">
          LinkedIn Comments
        </h2>
        <p className="text-sm text-[#87867f] mt-1 font-sans">
          High-signal 2-3 sentence perspectives verified against your style guide.
        </p>
      </div>

      <InputPanel
        postContent={postContent}
        onPostChange={setPostContent}
        angle={angle}
        onAngleChange={setAngle}
        perspectiveText={perspectiveText}
        onPerspectiveChange={setPerspectiveText}
        humanize={humanize}
        onHumanizeToggle={() => setHumanize(!humanize)}
        humanizeTone={humanizeTone}
        onToneChange={setHumanizeTone}
        loading={loading}
        deliberationPhase={deliberationPhase}
        error={error}
        onGenerate={handleGenerate}
        isRecording={isRecording}
        isTranscribing={isTranscribing}
        recordingError={recordingError}
        recordingSeconds={recordingSeconds}
        formatTimer={formatTimer}
        onStartVoiceRecording={() => startVoiceRecording()}
        onDismissRecordingError={() => setRecordingError('')}
      />

      {currentResult && (
        <PolishCard
          result={currentResult}
          copied={copied}
          onCopy={copyToClipboard}
          accordionOpen={accordionOpen}
          onToggleAccordion={() => setAccordionOpen(!accordionOpen)}
        />
      )}

      <CommentsHistory
        history={history}
        historyLoading={historyLoading}
        showHistory={showHistory}
        copiedId={historyCopiedId}
        onRefresh={fetchHistory}
        onToggleShow={() => setShowHistory(!showHistory)}
        onLoadFromHistory={handleLoadFromHistory}
        onCopyHistory={handleCopyHistory}
      />
    </div>
  )
}
