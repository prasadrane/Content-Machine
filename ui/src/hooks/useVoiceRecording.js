import { useEffect, useRef, useState } from 'react'
import { transcribeAudio } from '../api/interview'
import { isHostedWorkspace } from '../api/workspaceMode'

const DEFAULT_TARGET = '__voice_default__'
const MAX_SECONDS = 120

/**
 * Optional isTargetCurrent(target) checks the original opaque field context.
 * Supply onRecoveredTranscript(text, target) from a persistent owner when a
 * completed transcript cannot safely be inserted, including after unmount.
 * Without that callback, mounted callers receive recoverableTranscripts.
 */
export function useVoiceRecording({
  onTranscript, onRecoveredTranscript, isTargetCurrent, onSecondTick, enabled = true,
} = {}) {
  const [recordingTarget, setRecordingTarget] = useState(null)
  const [isRecording, setIsRecording] = useState(false)
  const [isStarting, setIsStarting] = useState(false)
  const [isTranscribing, setIsTranscribing] = useState(false)
  const [transcribingTarget, setTranscribingTarget] = useState(null)
  const [recoverableTranscripts, setRecoverableTranscripts] = useState([])
  const [error, setError] = useState('')
  const mounted = useRef(true)
  const enabledRef = useRef(enabled)
  const active = useRef(null)
  const sequence = useRef(0)
  const callbacks = useRef({})
  enabledRef.current = enabled
  callbacks.current = { onTranscript, isTargetCurrent, onSecondTick, onRecoveredTranscript }

  const clearTimers = session => {
    if (session.timer) clearInterval(session.timer)
    if (session.timeout) clearTimeout(session.timeout)
    session.timer = null
    session.timeout = null
  }
  const releaseStream = session => {
    const stream = session.stream
    session.stream = null
    stream?.getTracks().forEach(track => track.stop())
  }
  const finish = session => {
    clearTimers(session)
    releaseStream(session)
    if (active.current !== session) return
    active.current = null
    session.phase = 'ended'
    if (mounted.current) {
      setIsStarting(false)
      setIsRecording(false)
      setRecordingTarget(null)
      setIsTranscribing(false)
      setTranscribingTarget(null)
    }
  }
  const fail = (session, message) => {
    if (session.failed || session.cancelled || session.phase === 'ended') return
    session.failed = true
    if (mounted.current && active.current === session && !session.cancelled) setError(message)
    if (session.recognition) {
      try { session.recognition.stop() } catch { /* The browser may have already stopped. */ }
    }
    if (session.recorder && session.recorder.state !== 'inactive') {
      try { session.recorder.stop() } catch { /* The stream is still released below. */ }
    }
    finish(session)
  }
  const deliver = (session, value) => {
    if (session.failed || session.cancelled || session.phase === 'ended') return
    const text = typeof value === 'string' ? value.trim() : ''
    if (!text) return
    let current = mounted.current && enabledRef.current && !session.invalidated &&
      session.id === sequence.current
    if (current && callbacks.current.isTargetCurrent) {
      try { current = Boolean(callbacks.current.isTargetCurrent(session.target)) } catch { current = false }
    }
    if (current && callbacks.current.onTranscript) {
      callbacks.current.onTranscript(text, session.target)
    } else if (session.onRecoveredTranscript) {
      session.onRecoveredTranscript(text, session.target)
    } else if (mounted.current) {
      setRecoverableTranscripts(previous => [...previous, { text, target: session.target }])
    }
  }
  const startTimers = session => {
    if (callbacks.current.onSecondTick) {
      let seconds = 0
      callbacks.current.onSecondTick(0)
      session.timer = setInterval(() => {
        seconds += 1
        callbacks.current.onSecondTick?.(Math.min(seconds, MAX_SECONDS))
      }, 1000)
    }
    session.timeout = setTimeout(() => stop(false), MAX_SECONDS * 1000)
  }
  const markRecording = session => {
    if (active.current !== session || session.phase !== 'starting') return
    if (!mounted.current || !enabledRef.current || session.cancelled) {
      stop(true)
      return
    }
    session.phase = 'recording'
    setIsStarting(false)
    setIsRecording(true)
    setRecordingTarget(session.normalizedTarget)
    startTimers(session)
  }
  const stop = invalidated => {
    const session = active.current
    if (!session) return
    if (invalidated) session.invalidated = true
    clearTimers(session)
    if (session.phase === 'starting') {
      session.cancelled = true
      if (mounted.current) setIsStarting(false)
      if (session.recognition) {
        try { session.recognition.stop() } catch { /* Browser may not have started yet. */ }
        finish(session)
      }
      return
    }
    if (session.phase !== 'recording') return
    session.phase = 'stopping'
    if (mounted.current) {
      setIsRecording(false)
      setRecordingTarget(null)
      setIsTranscribing(true)
      setTranscribingTarget(session.normalizedTarget)
    }
    if (session.recognition) {
      try { session.recognition.stop() } catch { finish(session) }
      return
    }
    try {
      session.recorder.stop()
      releaseStream(session)
    } catch {
      fail(session, 'Could not stop the microphone recording.')
    }
  }

  const startRecording = async target => {
    if (!mounted.current || !enabledRef.current) return
    const normalizedTarget = target === undefined ? DEFAULT_TARGET : target
    if (active.current) {
      if (active.current.phase === 'recording' && active.current.normalizedTarget === normalizedTarget) stop(false)
      return
    }
    const session = {
      id: ++sequence.current, target, normalizedTarget, phase: 'starting',
      invalidated: false, cancelled: false, chunks: [], stream: null,
      onRecoveredTranscript: callbacks.current.onRecoveredTranscript,
    }
    active.current = session
    setError('')
    setIsStarting(true)
    const Recognition = typeof window !== 'undefined' &&
      (window.SpeechRecognition || window.webkitSpeechRecognition)
    if (Recognition) {
      try {
        const recognition = new Recognition()
        session.recognition = recognition
        recognition.continuous = true
        recognition.interimResults = true
        recognition.lang = 'en-US'
        recognition.onstart = () => markRecording(session)
        recognition.onresult = event => {
          let finalText = ''
          for (let index = event.resultIndex; index < event.results.length; index += 1) {
            if (event.results[index].isFinal) finalText += event.results[index][0].transcript + ' '
          }
          deliver(session, finalText)
        }
        recognition.onerror = event => {
          if (event.error !== 'no-speech') fail(session, `Voice input error: ${event.error}`)
          else finish(session)
        }
        recognition.onend = () => finish(session)
        recognition.start()
        return
      } catch {
        session.recognition = null
      }
    }
    if (isHostedWorkspace()) {
      // Hosted mode has no audio-upload transcription route (410); browser speech recognition only.
      fail(session, "Dictation isn't supported in this browser. You can type instead.")
      return
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      session.stream = stream
      if (session.cancelled || !mounted.current || !enabledRef.current || active.current !== session) {
        finish(session)
        return
      }
      const recorder = new MediaRecorder(stream)
      session.recorder = recorder
      recorder.ondataavailable = event => {
        if (event.data.size > 0) session.chunks.push(event.data)
      }
      recorder.onstart = () => markRecording(session)
      recorder.onerror = () => fail(session, 'Audio recording failed.')
      recorder.onstop = async () => {
        releaseStream(session)
        if (session.failed || session.cancelled || session.phase === 'ended') {
          finish(session)
          return
        }
        const audio = new Blob(session.chunks, { type: 'audio/webm' })
        if (!audio.size) {
          finish(session)
          return
        }
        session.phase = 'transcribing'
        if (mounted.current) {
          setIsRecording(false)
          setRecordingTarget(null)
          setIsTranscribing(true)
          setTranscribingTarget(session.normalizedTarget)
        }
        try {
          const result = await transcribeAudio(audio, 'recording.webm')
          deliver(session, result.text)
        } catch (failure) {
          if (mounted.current && active.current === session) {
            setError(failure.message || 'Failed to transcribe audio.')
          }
        } finally {
          finish(session)
        }
      }
      recorder.start()
      if (session.phase === 'starting') markRecording(session)
    } catch {
      fail(session, 'Microphone access denied or audio recording unavailable.')
    }
  }

  useEffect(() => {
    if (!enabled) stop(true)
  }, [enabled])
  useEffect(() => {
    mounted.current = true
    enabledRef.current = enabled
    return () => {
      mounted.current = false
      enabledRef.current = false
      stop(true)
    }
  }, [])

  return {
    startRecording, stopRecording: () => stop(false), isRecording, isStarting,
    cancelRecording: () => {
      const session = active.current
      if (!session) return
      session.cancelled = true
      stop(true)
      finish(session)
    },
    recordingTarget, isTranscribing, transcribingTarget, error, setError,
    recoverableTranscripts,
    removeRecoveredTranscript: index => setRecoverableTranscripts(previous =>
      previous.filter((_, position) => position !== index)),
  }
}
