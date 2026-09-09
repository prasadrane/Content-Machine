import React from 'react'
import { AlertCircle, RotateCw, Sparkles, Mic, X } from 'lucide-react'
import { HUMANIZE_TONES } from '../../lib/constants'
import { ANGLES } from '../../lib/angles'

export default function InputPanel({
  postContent,
  onPostChange,
  angle,
  onAngleChange,
  perspectiveText,
  onPerspectiveChange,
  humanize,
  onHumanizeToggle,
  humanizeTone,
  onToneChange,
  loading,
  deliberationPhase,
  error,
  onGenerate,
  // recording props
  isRecording,
  isTranscribing,
  recordingError,
  recordingSeconds,
  formatTimer,
  onStartVoiceRecording,
  onDismissRecordingError,
}) {
  return (
    <div className="bg-[#f0eee6]/60 border border-[#e3dacc] rounded-2xl p-6 sm:p-7 space-y-6 shadow-anthropic">
      {/* Post Content Input */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <label className="text-xs uppercase font-mono tracking-wider text-[#87867f] font-semibold">
            LinkedIn Post Content <span className="text-[#c6613f]">*</span>
          </label>
          <span className="text-[11px] font-mono text-[#87867f]">
            {postContent.trim().length} chars {postContent.trim().length < 10 && '(min 10)'}
          </span>
        </div>
        <textarea
          rows={5}
          value={postContent}
          onChange={(e) => onPostChange(e.target.value)}
          placeholder="Paste the LinkedIn post content you want to comment on..."
          className="w-full text-xs sm:text-sm font-sans bg-[#faf9f5] border border-[#e3dacc] rounded-xl p-3.5 text-[#141413] focus:outline-none focus:border-[#141413] focus:ring-1 focus:ring-[#141413]/20 transition placeholder-[#b0aea5] leading-relaxed"
        />
      </div>

      {/* Editorial Angle Selector */}
      <div className="space-y-2.5">
        <label className="text-xs uppercase font-mono tracking-wider text-[#87867f] font-semibold block">
          Editorial Angle
        </label>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {ANGLES.map((item) => {
            const active = angle === item.id
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => onAngleChange(item.id)}
                className={`flex flex-col text-left p-3.5 rounded-xl border transition-all ${
                  active
                    ? 'bg-[#141413] text-[#faf9f5] border-[#141413] shadow-sm'
                    : 'bg-[#faf9f5] text-[#87867f] hover:text-[#141413] hover:bg-[#e3dacc]/40 border-[#e3dacc]'
                }`}
              >
                <span className={`text-xs font-medium ${active ? 'text-[#faf9f5]' : 'text-[#141413]'}`}>
                  {item.label}
                  <span className="sr-only"> ({item.id})</span>
                </span>
                <span className={`text-[11px] mt-1 line-clamp-2 ${active ? 'text-[#faf9f5]/80' : 'text-[#87867f]'}`}>
                  {item.desc}
                </span>
              </button>
            )
          })}
        </div>
      </div>

      {/* Operator Perspective with Integrated Microphone */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <label className="text-xs uppercase font-mono tracking-wider text-[#87867f] font-semibold">
            Operator Perspective <span className="font-normal lowercase text-[#87867f]">(optional)</span>
          </label>

          {/* Voice Dictation Button */}
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onStartVoiceRecording}
              disabled={isTranscribing}
              className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-mono transition shadow-sm ${
                isRecording
                  ? 'bg-rose-600 text-white animate-pulse shadow-rose-200'
                  : isTranscribing
                  ? 'bg-[#e3dacc] text-[#87867f] cursor-wait'
                  : 'bg-[#faf9f5] hover:bg-[#e3dacc] text-[#141413] border border-[#e3dacc]'
              }`}
              title={isRecording ? 'Click to stop recording' : 'Dictate your perspective using voice'}
            >
              {isRecording ? (
                <>
                  <span className="w-2 h-2 rounded-full bg-white animate-ping" />
                  <span className="font-medium">Listening... Stop ({formatTimer ? formatTimer(recordingSeconds) : recordingSeconds})</span>
                </>
              ) : isTranscribing ? (
                <>
                  <RotateCw className="w-3 h-3 animate-spin text-[#c6613f]" />
                  <span>Transcribing audio...</span>
                </>
              ) : (
                <>
                  <Mic className="w-3 h-3 text-[#c6613f]" />
                  <span>🎙️ Speak Perspective</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Microphone Error Banner */}
        {recordingError && (
          <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-amber-800 text-xs flex items-center justify-between gap-2 animate-fadeIn">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0 text-amber-600" />
              <span>{recordingError}</span>
            </div>
            <button
              type="button"
              onClick={onDismissRecordingError}
              className="p-1 text-amber-600 hover:text-amber-800 rounded-full"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        )}

        <textarea
          rows={3}
          value={perspectiveText}
          onChange={(e) => onPerspectiveChange(e.target.value)}
          placeholder="Your personal perspective, counterpoint, or angle (optional)..."
          className={`w-full text-xs sm:text-sm font-sans bg-[#faf9f5] border rounded-xl p-3.5 text-[#141413] focus:outline-none focus:border-[#141413] transition placeholder-[#b0aea5] leading-relaxed ${
            isRecording ? 'border-[#c6613f] ring-2 ring-[#c6613f]/20' : 'border-[#e3dacc]'
          }`}
        />
      </div>

      {/* Humanize Polish Controls */}
      <div className="space-y-2.5 p-4 bg-[#faf9f5] border border-[#e3dacc] rounded-xl">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-xs uppercase font-mono tracking-wider text-[#87867f] font-semibold">
              Humanize Polish
            </span>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-[#f0eee6] text-[#87867f] border border-[#e3dacc]">
              Anti-AI Transformer
            </span>
          </div>
          <button
            type="button"
            onClick={onHumanizeToggle}
            className={`px-3 py-1 rounded-full text-xs font-mono font-medium transition flex items-center gap-1.5 border shadow-sm ${
              humanize
                ? 'bg-[#c6613f] text-[#faf9f5] border-[#c6613f]'
                : 'bg-[#f0eee6] text-[#87867f] border-[#e3dacc] hover:text-[#141413]'
            }`}
          >
            <span>🪄 Humanize Polish</span>
            <span className={`px-1.5 py-0.2 rounded text-[10px] font-bold ${humanize ? 'bg-[#faf9f5]/20 text-[#faf9f5]' : 'bg-[#e3dacc] text-[#87867f]'}`}>
              {humanize ? 'ON' : 'OFF'}
            </span>
          </button>
        </div>

        {humanize && (
          <div className="pt-2 border-t border-[#e3dacc]/60 space-y-2">
            <span className="text-[11px] font-mono text-[#87867f] block">Target Human Tone:</span>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
              {HUMANIZE_TONES.map((t) => {
                const active = humanizeTone === t.id
                return (
                  <button
                    key={t.id}
                    type="button"
                    onClick={() => onToneChange(t.id)}
                    className={`px-3 py-2 rounded-xl text-left border transition text-xs font-mono flex flex-col gap-0.5 ${
                      active
                        ? 'bg-[#141413] text-[#faf9f5] border-[#141413] shadow-sm'
                        : 'bg-[#f0eee6]/60 text-[#87867f] hover:text-[#141413] hover:bg-[#f0eee6] border-[#e3dacc]'
                    }`}
                  >
                    <span className={`font-medium ${active ? 'text-[#faf9f5]' : 'text-[#141413]'}`}>
                      {t.label}
                    </span>
                    <span className={`text-[10px] line-clamp-1 ${active ? 'text-[#faf9f5]/70' : 'text-[#87867f]'}`}>
                      {t.desc}
                    </span>
                  </button>
                )
              })}
            </div>
          </div>
        )}
      </div>

      {/* Error Notification */}
      {error && (
        <div className="p-3.5 bg-rose-50 border border-rose-200 rounded-xl text-rose-800 text-xs flex items-center gap-2 animate-fadeIn">
          <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
          <span>{error}</span>
        </div>
      )}

      {/* Generate Button & Animated Deliberation Status */}
      <div className="pt-2 flex flex-col gap-3">
        <button
          type="button"
          onClick={onGenerate}
          disabled={loading || postContent.trim().length < 10}
          className="w-full py-3 px-6 bg-[#c6613f] hover:bg-[#a54c2d] disabled:opacity-50 disabled:cursor-not-allowed text-[#faf9f5] rounded-full text-xs sm:text-sm font-medium transition flex items-center justify-center gap-2 shadow-sm"
        >
          {loading ? (
            <>
              <RotateCw className="w-4 h-4 animate-spin text-white" />
              <span>Council Deliberation in Progress...</span>
            </>
          ) : (
            <>
              <Sparkles className="w-4 h-4" />
              <span>Run Council Round &amp; Generate Comment</span>
            </>
          )}
        </button>

        {loading && (
          <div className="bg-[#faf9f5] border border-[#e3dacc] rounded-xl p-3.5 flex items-center gap-3 animate-fadeIn">
            <RotateCw className="w-4 h-4 animate-spin text-[#c6613f] shrink-0" />
            <div className="text-xs font-mono text-[#141413] truncate">
              <span className="font-semibold text-[#c6613f]">Council Round: </span>
              <span className="text-[#87867f]">{deliberationPhase}</span>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
