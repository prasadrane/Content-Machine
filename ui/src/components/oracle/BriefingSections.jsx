import React from 'react'
import {
  Sparkles,
  RotateCw,
  Users,
  AlertCircle,
  Mic,
  X,
} from 'lucide-react'

export function ExecutiveBriefingSection({ loadingBriefing, briefing, briefingError }) {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <h3 className="cm-panel-title flex items-center gap-1.5">
          <Sparkles className="w-3 h-3 text-anthropic-clay" />
          <span>Executive Topic Briefing</span>
        </h3>
        {loadingBriefing && (
          <span className="text-sm text-anthropic-cloud-dark flex items-center gap-1">
            <RotateCw className="w-2.5 h-2.5 animate-spin text-anthropic-accent" />
            <span>synthesizing briefing...</span>
          </span>
        )}
      </div>

      {loadingBriefing ? (
        <div className="cm-panel space-y-3 animate-pulse">
          <div className="h-3 bg-anthropic-oat rounded w-3/4"></div>
          <div className="h-3 bg-anthropic-oat rounded w-5/6"></div>
          <div className="h-3 bg-anthropic-oat rounded w-1/2"></div>
        </div>
      ) : briefing ? (
        <div className="cm-panel space-y-3">
          <p className="cm-prose leading-relaxed">
            {briefing.summary}
          </p>
          {briefing.core_conflict && (
            <div className="pt-3 border-t border-anthropic-oat/70 flex items-start gap-2 text-sm text-anthropic-cloud-dark">
              <span className="text-anthropic-accent uppercase text-sm tracking-wider shrink-0 font-medium">Core Tension:</span>
              <span className="italic leading-relaxed">{briefing.core_conflict}</span>
            </div>
          )}
        </div>
      ) : (
        <div className="cm-status cm-status-warning">
          {briefingError || 'Could not load briefing.'}
        </div>
      )}
    </div>
  )
}

export function PersonaQuestionsSection({
  briefing,
  loadingBriefing,
  recordingError,
  setRecordingError,
  answers,
  setAnswers,
  recordingTarget,
  isTranscribingAudio,
  startVoiceRecording,
}) {
  return (
    <div className="space-y-3">
      <div>
        <h3 className="cm-panel-title flex items-center gap-1.5">
          <Users className="w-3 h-3 text-anthropic-accent" />
          <span>Interrogator Personas &bull; Your Perspective</span>
        </h3>
        <p className="cm-prose mt-0.5">
          Ground the draft in your authentic operational reality. Answer one or more questions below using text or voice dictation:
        </p>
      </div>

      {recordingError && (
        <div className="cm-status cm-status-warning flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 text-amber-600" />
            <span>{recordingError}</span>
          </div>
          <button
            type="button"
            onClick={() => setRecordingError('')}
            className="cm-button cm-button-quiet"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {loadingBriefing ? (
        <div className="space-y-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="cm-subpanel h-20 animate-pulse"></div>
          ))}
        </div>
      ) : (
        <div className="space-y-4">
          {(briefing?.questions || []).map((q, idx) => (
            <div key={idx} className="cm-panel space-y-3">
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className="cm-badge">
                    {q.persona}
                  </span>
                  <span className="text-sm text-anthropic-cloud-dark">
                    {q.focus}
                  </span>
                </div>

                <button
                  type="button"
                  onClick={() => startVoiceRecording(idx)}
                  className={` cm-button inline-flex items-center gap-1.5 ${
                    recordingTarget === idx
                      ? "cm-button-primary animate-pulse"
                      : isTranscribingAudio && recordingTarget === idx
                      ? "cm-button-secondary cursor-wait"
                      : "cm-button-secondary"
                  }  `}
                  title={recordingTarget === idx ? 'Click to stop recording' : 'Dictate your answer using voice'}
                >
                  {recordingTarget === idx ? (
                    <>
                      <span className="w-2 h-2 rounded-full bg-white animate-ping" />
                      <span className="font-medium">Listening... Stop</span>
                    </>
                  ) : isTranscribingAudio && recordingTarget === idx ? (
                    <>
                      <RotateCw className="w-3 h-3 animate-spin text-anthropic-accent" />
                      <span>Transcribing...</span>
                    </>
                  ) : (
                    <>
                      <Mic className="w-3 h-3 text-anthropic-accent" />
                      <span>Voice Input</span>
                    </>
                  )}
                </button>
              </div>
              <p className="cm-prose leading-snug">
                {q.question}
              </p>
              <textarea
                rows={3}
                value={answers[idx] || ''}
                onChange={(e) => setAnswers({ ...answers, [idx]: e.target.value })}
                placeholder="Your concrete experience, numbers, tools, or observations..."
                className={` cm-textarea w-full ${
                  recordingTarget === idx
                    ? "border-anthropic-accent ring-2 ring-anthropic-accent/20 bg-anthropic-ivory-light"
                    : "border-anthropic-oat"
                }  `}
              />
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export function RawNotesSection({
  rawNotes,
  setRawNotes,
  recordingTarget,
  isTranscribingAudio,
  startVoiceRecording,
}) {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <label className="cm-label block flex items-center gap-1.5">
          <Mic className="w-3 h-3 text-anthropic-clay" />
          <span>Additional Notes / Raw Dictation</span>
        </label>
        <button
          type="button"
          onClick={() => startVoiceRecording('raw')}
          className={` cm-button inline-flex items-center gap-1.5 ${
            recordingTarget === 'raw'
              ? "cm-button-primary animate-pulse"
              : isTranscribingAudio && recordingTarget === 'raw'
              ? "cm-button-secondary cursor-wait"
              : "cm-button-secondary"
          }  `}
          title={recordingTarget === 'raw' ? 'Click to stop recording' : 'Dictate notes using voice'}
        >
          {recordingTarget === 'raw' ? (
            <>
              <span className="w-2 h-2 rounded-full bg-white animate-ping" />
              <span className="font-medium">Listening... Stop</span>
            </>
          ) : isTranscribingAudio && recordingTarget === 'raw' ? (
            <>
              <RotateCw className="w-3 h-3 animate-spin text-anthropic-accent" />
              <span>Transcribing...</span>
            </>
          ) : (
            <>
              <Mic className="w-3 h-3 text-anthropic-accent" />
              <span>Voice Input</span>
            </>
          )}
        </button>
      </div>
      <textarea
        rows={3}
        value={rawNotes}
        onChange={(e) => setRawNotes(e.target.value)}
        placeholder="Paste voice dictation or any unstructured thoughts, counter-intuitive arguments, or specific dialogue..."
        className={` cm-textarea w-full ${
          recordingTarget === 'raw'
            ? "border-anthropic-accent ring-2 ring-anthropic-accent/20 bg-anthropic-ivory-light"
            : "border-anthropic-oat"
        }  `}
      />
    </div>
  )
}
