import React, { useState, useEffect } from 'react'
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

export default function InterviewModal({ item, onClose, onSynthesizeComplete, onSkipToCouncil }) {
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
