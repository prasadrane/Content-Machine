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
        <h3 className="text-[11px] uppercase font-mono tracking-wider text-[#87867f] flex items-center gap-1.5">
          <Sparkles className="w-3 h-3 text-[#d97757]" />
          <span>Executive Topic Briefing</span>
        </h3>
        {loadingBriefing && (
          <span className="text-[10px] font-mono text-[#87867f] flex items-center gap-1">
            <RotateCw className="w-2.5 h-2.5 animate-spin text-[#c6613f]" />
            <span>synthesizing briefing...</span>
          </span>
        )}
      </div>

      {loadingBriefing ? (
        <div className="bg-[#f0eee6]/60 border border-[#e3dacc] rounded-2xl p-6 space-y-3 animate-pulse">
          <div className="h-3 bg-[#e3dacc] rounded w-3/4"></div>
          <div className="h-3 bg-[#e3dacc] rounded w-5/6"></div>
          <div className="h-3 bg-[#e3dacc] rounded w-1/2"></div>
        </div>
      ) : briefing ? (
        <div className="bg-[#f0eee6]/60 border border-[#e3dacc] rounded-2xl p-5 sm:p-6 space-y-3 shadow-anthropic">
          <p className="text-xs sm:text-sm font-serif text-[#141413] leading-relaxed">
            {briefing.summary}
          </p>
          {briefing.core_conflict && (
            <div className="pt-3 border-t border-[#e3dacc]/70 flex items-start gap-2 text-[11px] sm:text-xs text-[#87867f]">
              <span className="font-mono text-[#c6613f] uppercase text-[10px] tracking-wider shrink-0 font-medium">Core Tension:</span>
              <span className="italic leading-relaxed">{briefing.core_conflict}</span>
            </div>
          )}
        </div>
      ) : (
        <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-800">
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
        <h3 className="text-[11px] uppercase font-mono tracking-wider text-[#87867f] flex items-center gap-1.5">
          <Users className="w-3 h-3 text-[#c6613f]" />
          <span>Interrogator Personas &bull; Your Perspective</span>
        </h3>
        <p className="text-[11px] text-[#87867f] mt-0.5">
          Ground the draft in your authentic operational reality. Answer one or more questions below using text or voice dictation:
        </p>
      </div>

      {recordingError && (
        <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-amber-800 text-xs flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 text-amber-600" />
            <span>{recordingError}</span>
          </div>
          <button
            type="button"
            onClick={() => setRecordingError('')}
            className="p-1 text-amber-600 hover:text-amber-800 rounded-full"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {loadingBriefing ? (
        <div className="space-y-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-20 bg-[#f0eee6]/40 border border-[#e3dacc] rounded-xl animate-pulse"></div>
          ))}
        </div>
      ) : (
        <div className="space-y-4">
          {(briefing?.questions || []).map((q, idx) => (
            <div key={idx} className="bg-[#faf9f5] border border-[#e3dacc] rounded-2xl p-5 space-y-3 shadow-sm">
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-mono px-2.5 py-0.5 rounded-full bg-[#f0eee6] text-[#141413] font-medium border border-[#e3dacc]">
                    {q.persona}
                  </span>
                  <span className="text-[10px] font-mono text-[#87867f]">
                    {q.focus}
                  </span>
                </div>

                <button
                  type="button"
                  onClick={() => startVoiceRecording(idx)}
                  className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-mono transition shadow-sm ${
                    recordingTarget === idx
                      ? 'bg-rose-600 text-white animate-pulse shadow-rose-200'
                      : isTranscribingAudio && recordingTarget === idx
                      ? 'bg-[#e3dacc] text-[#87867f] cursor-wait'
                      : 'bg-[#f0eee6] hover:bg-[#e3dacc] text-[#141413] border border-[#e3dacc]'
                  }`}
                  title={recordingTarget === idx ? 'Click to stop recording' : 'Dictate your answer using voice'}
                >
                  {recordingTarget === idx ? (
                    <>
                      <span className="w-2 h-2 rounded-full bg-white animate-ping" />
                      <span className="font-medium">Listening... Stop</span>
                    </>
                  ) : isTranscribingAudio && recordingTarget === idx ? (
                    <>
                      <RotateCw className="w-3 h-3 animate-spin text-[#c6613f]" />
                      <span>Transcribing...</span>
                    </>
                  ) : (
                    <>
                      <Mic className="w-3 h-3 text-[#c6613f]" />
                      <span>Voice Input</span>
                    </>
                  )}
                </button>
              </div>
              <p className="text-xs sm:text-sm font-medium text-[#141413] leading-snug">
                {q.question}
              </p>
              <textarea
                rows={3}
                value={answers[idx] || ''}
                onChange={(e) => setAnswers({ ...answers, [idx]: e.target.value })}
                placeholder="Your concrete experience, numbers, tools, or observations..."
                className={`w-full text-xs sm:text-sm font-sans bg-[#f0eee6]/40 border rounded-xl p-3 sm:p-3.5 text-[#141413] focus:outline-none focus:border-[#141413] focus:bg-[#faf9f5] transition placeholder-[#b0aea5] ${
                  recordingTarget === idx
                    ? 'border-[#c6613f] ring-2 ring-[#c6613f]/20 bg-[#faf9f5]'
                    : 'border-[#e3dacc]'
                }`}
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
        <label className="block text-[11px] font-mono uppercase tracking-wider text-[#87867f] flex items-center gap-1.5">
          <Mic className="w-3 h-3 text-[#d97757]" />
          <span>Additional Notes / Raw Dictation</span>
        </label>
        <button
          type="button"
          onClick={() => startVoiceRecording('raw')}
          className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-mono transition shadow-sm ${
            recordingTarget === 'raw'
              ? 'bg-rose-600 text-white animate-pulse shadow-rose-200'
              : isTranscribingAudio && recordingTarget === 'raw'
              ? 'bg-[#e3dacc] text-[#87867f] cursor-wait'
              : 'bg-[#f0eee6] hover:bg-[#e3dacc] text-[#141413] border border-[#e3dacc]'
          }`}
          title={recordingTarget === 'raw' ? 'Click to stop recording' : 'Dictate notes using voice'}
        >
          {recordingTarget === 'raw' ? (
            <>
              <span className="w-2 h-2 rounded-full bg-white animate-ping" />
              <span className="font-medium">Listening... Stop</span>
            </>
          ) : isTranscribingAudio && recordingTarget === 'raw' ? (
            <>
              <RotateCw className="w-3 h-3 animate-spin text-[#c6613f]" />
              <span>Transcribing...</span>
            </>
          ) : (
            <>
              <Mic className="w-3 h-3 text-[#c6613f]" />
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
        className={`w-full text-xs sm:text-sm font-sans bg-[#f0eee6]/40 border rounded-xl p-3 sm:p-3.5 text-[#141413] focus:outline-none focus:border-[#141413] focus:bg-[#faf9f5] transition placeholder-[#b0aea5] ${
          recordingTarget === 'raw'
            ? 'border-[#c6613f] ring-2 ring-[#c6613f]/20 bg-[#faf9f5]'
            : 'border-[#e3dacc]'
        }`}
      />
    </div>
  )
}
