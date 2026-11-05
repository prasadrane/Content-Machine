import React, { useState, useEffect, useRef } from 'react'
import { createPortal } from 'react-dom'
import {
  Sparkles,
  RotateCw,
  AlertCircle,
  ExternalLink,
  X,
} from 'lucide-react'
import { getBrief, synthesizeDraft } from '../../api/interview'
import { useVoiceRecording } from '../../hooks/useVoiceRecording'
import {
  ExecutiveBriefingSection,
  PersonaQuestionsSection,
  RawNotesSection,
} from './BriefingSections'

export default function InterviewModal({ item, onClose, onSynthesizeComplete, onSkipToCouncil, isActive = true }) {
  const activeRef = useRef(isActive)
  activeRef.current = isActive
  const dialogRef = useRef(null)
  const [completedDraft, setCompletedDraft] = useState(null)
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
    enabled: isActive,
    onTranscript: (text, target) => {
      if (!activeRef.current) return
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
    if (!isActive) return
    const opener = document.activeElement, dialog = dialogRef.current
    const selector = 'button:not([disabled]), a[href], input:not([disabled]), textarea:not([disabled])'
    dialog?.querySelector('button')?.focus()
    const handleKey = event => {
      if (event.key === 'Escape') { event.preventDefault(); onClose(); return }
      if (event.key !== 'Tab') return
      const controls = [...dialog.querySelectorAll(selector)].filter(el => !el.closest('details:not([open])'))
      const first = controls[0], last = controls[controls.length - 1]
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus() }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus() }
    }
    dialog?.addEventListener('keydown', handleKey)
    return () => {
      dialog?.removeEventListener('keydown', handleKey)
      if (opener?.isConnected && !opener.closest('[hidden]')) opener.focus()
    }
  }, [isActive, onClose])

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
      if (activeRef.current) onSynthesizeComplete(data.draft, data.spike_id)
      else setCompletedDraft(data)
    } catch (err) {
      setSynthError(err.message || 'Draft synthesis failed.')
    } finally {
      setSynthesizing(false)
    }
  }

  if (!isActive) return null
  return createPortal(
    <div 
      className="fixed inset-0 z-[100] w-screen h-screen bg-anthropic-slate-dark/70 backdrop-blur-sm flex items-center justify-center p-6 sm:p-8 md:p-10 overflow-y-auto"
      onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
    >
      <div 
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label={`Perspective on ${item.title}`}
        className="cm-dialog p-4 sm:p-6 max-w-2xl w-full space-y-6 animate-fadeIn max-h-[calc(100vh-5rem)] flex flex-col justify-between my-auto shrink-0"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-start justify-between gap-4 border-b border-anthropic-oat pb-4 shrink-0">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="cm-badge">
                Topic Briefing & Perspective
              </span>
            </div>
            <h2 className="text-xl font-serif font-medium text-anthropic-slate-dark leading-snug">
              {item.title}
            </h2>
            {item.url && (
              <a
                href={item.url}
                target="_blank"
                rel="noreferrer"
                className="cm-link inline-flex items-center gap-1"
              >
                <span>{item.source || 'Source Article'}</span>
                <ExternalLink className="w-2.5 h-2.5" />
              </a>
            )}
          </div>
          <button
            type="button"
            aria-label="Close perspective interview"
            onClick={onClose}
            className="cm-icon-button shrink-0"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Scrollable Content */}
        <div className="space-y-6 overflow-y-auto pr-3 sm:pr-4 flex-1 py-1 -mr-1">
          <ExecutiveBriefingSection
            loadingBriefing={loadingBriefing}
            briefing={briefing}
            briefingError={briefingError}
          />

          <PersonaQuestionsSection
            briefing={briefing}
            loadingBriefing={loadingBriefing}
            recordingError={recordingError}
            setRecordingError={setRecordingError}
            answers={answers}
            setAnswers={setAnswers}
            recordingTarget={recordingTarget}
            isTranscribingAudio={isTranscribingAudio}
            startVoiceRecording={startVoiceRecording}
          />

          <RawNotesSection
            rawNotes={rawNotes}
            setRawNotes={setRawNotes}
            recordingTarget={recordingTarget}
            isTranscribingAudio={isTranscribingAudio}
            startVoiceRecording={startVoiceRecording}
          />

          {synthError && (
            <div className="cm-status cm-status-error flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
              <span>{synthError}</span>
            </div>
          )}
        </div>

        {/* Modal Actions */}
        {completedDraft && <div role="status" className="cm-status cm-status-success">
          Your draft finished while you were elsewhere. Your notes are preserved.
          <button type="button" className="cm-button cm-button-quiet ml-2 underline" onClick={() => onSynthesizeComplete(completedDraft.draft, completedDraft.spike_id)}>Open completed draft</button>
        </div>}
        <div className="flex flex-wrap items-center justify-between pt-5 mt-2 border-t border-anthropic-oat shrink-0 gap-3">
          <button
            onClick={() => onSkipToCouncil(item)}
            className="cm-button cm-button-quiet"
          >
            Skip to Manual Drafting &rarr;
          </button>

          <button
            onClick={handleSynthesize}
            disabled={synthesizing || loadingBriefing}
            className="cm-button cm-button-primary disabled:opacity-50 flex items-center gap-2"
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
