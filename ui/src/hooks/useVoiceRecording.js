import { useEffect, useRef, useState } from 'react'
import { transcribeAudio } from '../api/interview'

// Sentinel target for call sites that start recording without an explicit
// target; interview callers can select a specific answer destination.
const DEFAULT_TARGET = '__voice_default__'

// Hard cap for the optional recording-seconds timer.
const MAX_SECONDS = 120

/**
 * useVoiceRecording — voice input for perspective intake.
 * Wraps Web Speech API (live dictation) with a MediaRecorder +
 * backend transcribe fallback.
 *
 * options:
 *   onTranscript(text, target)  — called with final transcript text and the
 *                                 target passed to startRecording (undefined
 *                                 when the site has no per-target semantics).
 *   onSecondTick(seconds)       — optional; when provided the hook runs the
 *                                 seconds timer (reset to 0 on start, tick
 *                                 each second, auto-stop at MAX_SECONDS) and
 *                                 the MAX_SECONDS hard timeout safeguard.
 *
 * returns:
 *   { startRecording(target), stopRecording(), isRecording, recordingTarget,
 *     isTranscribing, error, setError }
 */
export function useVoiceRecording({ onTranscript, onSecondTick, enabled = true } = {}) {
  const enabledRef = useRef(enabled)
  enabledRef.current = enabled
  const [recordingTarget, setRecordingTarget] = useState(null)
  const [isTranscribing, setIsTranscribing] = useState(false)
  const [error, setError] = useState('')

  const recognitionRef = useRef(null)
  const mediaRecorderRef = useRef(null)
  const audioChunksRef = useRef([])
  const timerRef = useRef(null)
  const timeoutRef = useRef(null)
  const secondsRef = useRef(0)
  const activeTargetRef = useRef(null)

  // Always-call-latest callbacks so per-session closures never go stale.
  const cbRef = useRef({ onTranscript, onSecondTick })
  cbRef.current = { onTranscript, onSecondTick }

  const clearTimer = () => {
    if (timerRef.current) {
      clearInterval(timerRef.current)
      timerRef.current = null
    }
  }

  const stopRecording = () => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current)
      timeoutRef.current = null
    }
    if (recognitionRef.current) {
      const recognition = recognitionRef.current
      recognitionRef.current = null
      try {
        recognition.stop()
      } catch (e) {}
    }
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      try {
        mediaRecorderRef.current.stop()
      } catch (e) {}
    }
    clearTimer()
    activeTargetRef.current = null
    setRecordingTarget(null)
  }

  const markActive = (norm) => {
    activeTargetRef.current = norm
    setRecordingTarget(norm)
  }

  const startTimer = () => {
    if (!cbRef.current.onSecondTick || timerRef.current) return
    timerRef.current = setInterval(() => {
      secondsRef.current += 1
      cbRef.current.onSecondTick(Math.min(secondsRef.current, MAX_SECONDS))
      if (secondsRef.current >= MAX_SECONDS) {
        stopRecording()
      }
    }, 1000)
  }

  const startRecording = async (target) => {
    if (!enabledRef.current) return
    const norm = target === undefined ? DEFAULT_TARGET : target
    setError('')
    if (recordingTarget === norm) {
      stopRecording()
      return
    }
    if (recordingTarget !== null) {
      stopRecording()
    }

    if (cbRef.current.onSecondTick) {
      secondsRef.current = 0
      cbRef.current.onSecondTick(0)
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current)
        timeoutRef.current = null
      }
      // 120-second automatic recording stop timeout safeguard
      timeoutRef.current = setTimeout(() => {
        stopRecording()
      }, MAX_SECONDS * 1000)
    }

    const SpeechRecognition = typeof window !== 'undefined' ? (window.SpeechRecognition || window.webkitSpeechRecognition) : null
    if (SpeechRecognition) {
      try {
        const recog = new SpeechRecognition()
        recog.continuous = true
        recog.interimResults = true
        recog.lang = 'en-US'

        recog.onstart = () => {
          if (!enabledRef.current) { stopRecording(); return }
          markActive(norm)
          startTimer()
        }

        recog.onresult = (event) => {
          if (!enabledRef.current) return
          let sessionFinal = ''
          for (let i = event.resultIndex; i < event.results.length; ++i) {
            if (event.results[i].isFinal) {
              sessionFinal += event.results[i][0].transcript + ' '
            }
          }
          if (sessionFinal.trim()) {
            cbRef.current.onTranscript(sessionFinal.trim(), target)
          }
        }

        recog.onerror = (event) => {
          if (event.error !== 'no-speech') {
            setError(`Voice input error: ${event.error}`)
          }
          stopRecording()
        }

        recog.onend = () => {
          if (activeTargetRef.current === norm) {
            stopRecording()
          }
        }

        recognitionRef.current = recog
        recog.start()
        return
      } catch (err) {
        console.warn('SpeechRecognition failed, falling back to MediaRecorder:', err)
      }
    }

    // Fallback: MediaRecorder + backend /api/interview/transcribe
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      if (!enabledRef.current) { stream.getTracks().forEach(track => track.stop()); return }
      const mediaRecorder = new MediaRecorder(stream)
      mediaRecorderRef.current = mediaRecorder
      audioChunksRef.current = []

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          audioChunksRef.current.push(e.data)
        }
      }

      mediaRecorder.onstart = () => {
        markActive(norm)
        startTimer()
      }

      mediaRecorder.onstop = async () => {
        stream.getTracks().forEach((track) => track.stop())
        clearTimer()
        activeTargetRef.current = null
        setRecordingTarget(null)

        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' })
        if (audioBlob.size === 0 || !enabledRef.current) return

        setIsTranscribing(true)
        try {
          const data = await transcribeAudio(audioBlob, 'recording.webm')
          if (data.text) {
            cbRef.current.onTranscript(data.text.trim(), target)
          }
        } catch (err) {
          setError(err.message || 'Failed to transcribe audio.')
        } finally {
          setIsTranscribing(false)
        }
      }

      mediaRecorder.start()
      markActive(norm)
    } catch (err) {
      setError('Microphone access denied or audio recording unavailable.')
      stopRecording()
    }
  }

  useEffect(() => {
    enabledRef.current = enabled
    if (!enabled) stopRecording()
  }, [enabled])

  useEffect(() => {
    return () => {
      enabledRef.current = false
      stopRecording()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return {
    startRecording,
    stopRecording,
    isRecording: recordingTarget !== null,
    recordingTarget,
    isTranscribing,
    error,
    setError,
  }
}
