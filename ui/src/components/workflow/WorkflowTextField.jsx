import { useEffect, useId, useRef } from 'react'
import { Mic, Square } from 'lucide-react'
import { isHostedWorkspace } from '../../api/workspaceMode'
import { useVoiceRecording } from '../../hooks/useVoiceRecording'
import { useVoiceRecovery } from './VoiceRecovery'

export default function WorkflowTextField({ label, value, onChange, enabled = true, rows = 7 }) {
  const id = useId()
  // Hosted mode has no audio-upload route, so dictation needs browser speech recognition.
  const hosted = isHostedWorkspace()
  const dictationAvailable = !hosted || (typeof window !== 'undefined' &&
    Boolean(window.SpeechRecognition || window.webkitSpeechRecognition))
  const recovery = useVoiceRecovery()
  const mounted = useRef(true)
  const enabledRef = useRef(enabled)
  const session = useRef(0)
  const currentValue = useRef(value)
  currentValue.current = value
  if (enabledRef.current && !enabled) session.current += 1
  enabledRef.current = enabled
  useEffect(() => {
    mounted.current = true
    return () => { mounted.current = false; session.current += 1 }
  }, [])
  const voice = useVoiceRecording({
    enabled,
    onSecondTick: () => {},
    isTargetCurrent: target => {
      if (!mounted.current || !enabledRef.current) return false
      if (typeof target !== 'object') return target === session.current
      const identity = recovery?.identityRef.current
      return target.session === session.current && target.ownerId === identity?.ownerId &&
        target.itemId === identity?.itemId && target.revision === identity?.revision &&
        target.initialValue === currentValue.current
    },
    onRecoveredTranscript: recovery?.recover,
    onTranscript: (text, target) => {
      if (mounted.current && enabledRef.current && (target?.session ?? target) === session.current) {
        const append = current => `${current}${current ? '\n' : ''}${text}`
        if (typeof target === 'object') target.initialValue = append(currentValue.current)
        onChange(append)
      }
    },
  })
  return <div className="space-y-2">
    <div className="flex flex-wrap items-center justify-between gap-2">
      <label htmlFor={id} className="cm-label mb-0">{label}</label>
      {dictationAvailable && <button type="button" className="cm-button cm-button-quiet" disabled={!enabled || voice.isTranscribing || voice.isStarting}
        onClick={() => {
          if (voice.isRecording) { voice.stopRecording(); return }
          const number = ++session.current
          const target = recovery?.identity?.ownerId && recovery?.identity?.itemId
            ? { ...recovery.identity, field: label, session: number, initialValue: currentValue.current }
            : number
          voice.startRecording(target)
        }}
        aria-label={voice.isRecording ? `Stop dictating ${label}` : `Dictate ${label}`}>
        {voice.isRecording ? <Square size={16} aria-hidden="true" /> : <Mic size={16} aria-hidden="true" />}
        {voice.isRecording ? 'Stop recording' : 'Dictate'}
      </button>}
    </div>
    <textarea id={id} rows={rows} className="cm-textarea" value={value}
      onChange={event => onChange(event.target.value)} />
    {voice.isRecording && <p role="status" className="cm-muted">Listening. Review the transcript before saving.</p>}
    {voice.isStarting && <p role="status" className="cm-muted">Requesting microphone access…</p>}
    {voice.isTranscribing && <p role="status" className="cm-muted">Transcribing…</p>}
    {(voice.isStarting || voice.isRecording || voice.isTranscribing) &&
      <button type="button" className="cm-button cm-button-quiet" onClick={voice.cancelRecording}>Cancel dictation</button>}
    {voice.error && <p role="alert" className="cm-status cm-status-error">{voice.error}</p>}
    <details className="cm-muted">
      <summary className="cursor-pointer">How dictation works</summary>
      {hosted ? <p>Dictation uses your browser's built-in speech recognition, which may send audio to your browser's provider. Nothing is uploaded to this app. If your browser doesn't support it, the Dictate button is hidden. You can always type instead. Review the text before saving.</p> : <p>Your browser's speech recognition may use its provider's service. Otherwise, recorded audio is sent to this app's transcription service. You can always type instead. Review the text before saving.</p>}
    </details>
  </div>
}
