import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { act, renderHook, waitFor } from '@testing-library/react'
import { useVoiceRecording } from './useVoiceRecording'
import { transcribeAudio } from '../api/interview'

vi.mock('../api/interview', () => ({ transcribeAudio: vi.fn() }))

const target = { owner: 'creator-a', item: 'draft-a', field: 'notes', revision: 3 }
let stopTrack
let instances

function deferred() {
  let resolve
  let reject
  const promise = new Promise((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}

class FakeRecorder {
  constructor(stream) {
    this.stream = stream
    this.state = 'inactive'
    instances.push(this)
  }
  start() {
    this.state = 'recording'
    this.onstart?.()
  }
  stop() {
    this.state = 'inactive'
    this.ondataavailable?.({ data: new Blob(['audio'], { type: 'audio/webm' }) })
    queueMicrotask(() => this.onstop?.())
  }
}

beforeEach(() => {
  vi.resetAllMocks()
  instances = []
  stopTrack = vi.fn()
  vi.stubGlobal('SpeechRecognition', undefined)
  vi.stubGlobal('webkitSpeechRecognition', undefined)
  vi.stubGlobal('MediaRecorder', FakeRecorder)
  Object.defineProperty(navigator, 'mediaDevices', {
    configurable: true,
    value: { getUserMedia: vi.fn().mockResolvedValue({ getTracks: () => [{ stop: stopTrack }] }) },
  })
})
afterEach(() => vi.unstubAllGlobals())

describe('voice transcript ownership and recovery', () => {
  it('keeps processing visible after stop and recovers a result when disabled', async () => {
    const transcription = deferred()
    transcribeAudio.mockReturnValue(transcription.promise)
    const insert = vi.fn()
    const recover = vi.fn()
    const { result, rerender } = renderHook(({ enabled }) => useVoiceRecording({
      enabled, onTranscript: insert, onRecoveredTranscript: recover,
      isTargetCurrent: () => true,
    }), { initialProps: { enabled: true } })
    await act(async () => { await result.current.startRecording(target) })
    expect(result.current.isRecording).toBe(true)
    act(() => result.current.stopRecording())
    expect(result.current.isRecording).toBe(false)
    await waitFor(() => expect(result.current.isTranscribing).toBe(true))
    expect(stopTrack).toHaveBeenCalledOnce()
    rerender({ enabled: false })
    await act(async () => { transcription.resolve({ text: 'original spoken text' }); await transcription.promise })
    expect(insert).not.toHaveBeenCalled()
    expect(recover).toHaveBeenCalledOnce()
    expect(recover).toHaveBeenCalledWith('original spoken text', target)
    expect(result.current.isTranscribing).toBe(false)
  })

  it('recovers audio after unmount instead of inserting into a new item', async () => {
    const transcription = deferred()
    transcribeAudio.mockReturnValue(transcription.promise)
    const insert = vi.fn()
    const recover = vi.fn()
    const { result, unmount } = renderHook(() => useVoiceRecording({
      onTranscript: insert, onRecoveredTranscript: recover,
    }))
    await act(async () => { await result.current.startRecording(target) })
    unmount()
    await act(async () => { transcription.resolve({ text: 'spoken before leaving' }); await transcription.promise })
    expect(stopTrack).toHaveBeenCalledOnce()
    expect(transcribeAudio).toHaveBeenCalledOnce()
    expect(insert).not.toHaveBeenCalled()
    expect(recover).toHaveBeenCalledWith('spoken before leaving', target)
  })

  it('uses the target validity check to recover after an intervening edit', async () => {
    const transcription = deferred()
    transcribeAudio.mockReturnValue(transcription.promise)
    const insert = vi.fn()
    const recover = vi.fn()
    const isTargetCurrent = vi.fn().mockReturnValue(false)
    const { result } = renderHook(() => useVoiceRecording({ onTranscript: insert,
      onRecoveredTranscript: recover, isTargetCurrent }))
    await act(async () => { await result.current.startRecording(target) })
    await act(async () => { result.current.stopRecording(); await Promise.resolve() })
    await act(async () => { transcription.resolve({ text: 'keep this' }); await transcription.promise })
    expect(isTargetCurrent).toHaveBeenCalledWith(target)
    expect(insert).not.toHaveBeenCalled()
    expect(recover).toHaveBeenCalledWith('keep this', target)
  })

  it('does not let a re-enabled session redirect an earlier pending transcript', async () => {
    const first = deferred()
    transcribeAudio.mockReturnValueOnce(first.promise).mockResolvedValueOnce({ text: 'second' })
    const insert = vi.fn()
    const recover = vi.fn()
    const { result, rerender } = renderHook(({ enabled }) => useVoiceRecording({
      enabled, onTranscript: insert, onRecoveredTranscript: recover,
    }), { initialProps: { enabled: true } })
    await act(async () => { await result.current.startRecording(target) })
    await act(async () => { result.current.stopRecording(); await Promise.resolve() })
    rerender({ enabled: false })
    rerender({ enabled: true })
    await act(async () => { await result.current.startRecording('another-item') })
    expect(instances).toHaveLength(1)
    await act(async () => { first.resolve({ text: 'first' }); await first.promise })
    expect(recover).toHaveBeenCalledWith('first', target)
    await act(async () => { await result.current.startRecording('another-item') })
    await act(async () => { result.current.stopRecording(); await Promise.resolve() })
    await waitFor(() => expect(insert).toHaveBeenCalledWith('second', 'another-item'))
    expect(insert).toHaveBeenCalledOnce()
  })

  it('reports permission denial and releases a stream if recorder setup fails', async () => {
    navigator.mediaDevices.getUserMedia.mockRejectedValueOnce(new Error('denied'))
    const { result } = renderHook(() => useVoiceRecording())
    await act(async () => { await result.current.startRecording(target) })
    expect(result.current.error).toMatch(/microphone access denied/i)
    expect(result.current.isRecording).toBe(false)
    vi.stubGlobal('MediaRecorder', class { constructor() { throw new Error('unsupported') } })
    await act(async () => { await result.current.startRecording(target) })
    expect(stopTrack).toHaveBeenCalledOnce()
    expect(result.current.isRecording).toBe(false)
  })

  it('reports transcription errors without inventing a recovered result', async () => {
    transcribeAudio.mockRejectedValue(new Error('Transcription service failed'))
    const recover = vi.fn()
    const { result } = renderHook(() => useVoiceRecording({ onRecoveredTranscript: recover }))
    await act(async () => { await result.current.startRecording(target) })
    await act(async () => { result.current.stopRecording(); await Promise.resolve() })
    await waitFor(() => expect(result.current.error).toBe('Transcription service failed'))
    expect(result.current.isTranscribing).toBe(false)
    expect(recover).not.toHaveBeenCalled()
  })

  it('recovers a final browser recognition event after the field is disabled', async () => {
    let recognition
    class Speech {
      constructor() { recognition = this }
      start() { this.onstart() }
      stop() {}
    }
    vi.stubGlobal('SpeechRecognition', Speech)
    const insert = vi.fn()
    const recover = vi.fn()
    const { result, rerender } = renderHook(({ enabled }) => useVoiceRecording({
      enabled, onTranscript: insert, onRecoveredTranscript: recover,
    }), { initialProps: { enabled: true } })
    await act(async () => { await result.current.startRecording(target) })
    rerender({ enabled: false })
    const speechResult = [{ transcript: 'late speech' }]
    speechResult.isFinal = true
    act(() => recognition.onresult({ resultIndex: 0, results: [speechResult] }))
    expect(insert).not.toHaveBeenCalled()
    expect(recover).toHaveBeenCalledWith('late speech', target)
    act(() => recognition.onend())
  })

  it('keeps a recoverable result in hook state when the mounted caller has no recovery callback', async () => {
    transcribeAudio.mockResolvedValue({ text: 'saved for review' })
    const { result } = renderHook(() => useVoiceRecording({ isTargetCurrent: () => false }))
    await act(async () => { await result.current.startRecording(target) })
    await act(async () => { result.current.stopRecording(); await Promise.resolve() })
    await waitFor(() => expect(result.current.recoverableTranscripts).toEqual([{ text: 'saved for review', target }]))
    act(() => result.current.removeRecoveredTranscript(0))
    expect(result.current.recoverableTranscripts).toEqual([])
  })

  it('ignores extra starts while permission is pending and releases the cancelled stream', async () => {
    const microphone = deferred()
    navigator.mediaDevices.getUserMedia.mockReturnValue(microphone.promise)
    const { result } = renderHook(() => useVoiceRecording())
    let pending
    act(() => { pending = result.current.startRecording(target) })
    await act(async () => { await result.current.startRecording('another') })
    expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalledOnce()
    act(() => result.current.stopRecording())
    await act(async () => { microphone.resolve({ getTracks: () => [{ stop: stopTrack }] }); await pending })
    expect(stopTrack).toHaveBeenCalledOnce()
    expect(instances).toHaveLength(0)
  })

  it('does not transcribe audio after a recorder failure', async () => {
    const recover = vi.fn()
    const { result } = renderHook(() => useVoiceRecording({ onRecoveredTranscript: recover }))
    await act(async () => { await result.current.startRecording(target) })
    act(() => instances[0].ondataavailable({ data: new Blob(['partial']) }))
    act(() => instances[0].onerror(new Error('recorder failed')))
    await act(async () => { instances[0].onstop(); await Promise.resolve() })
    expect(result.current.error).toMatch(/audio recording failed/i)
    expect(transcribeAudio).not.toHaveBeenCalled()
    expect(recover).not.toHaveBeenCalled()
    expect(stopTrack).toHaveBeenCalledOnce()
  })

  it('starts timers once when the recorder emits its asynchronous start event', async () => {
    class AsyncRecorder extends FakeRecorder { start() { this.state = 'recording' } }
    vi.stubGlobal('MediaRecorder', AsyncRecorder)
    const tick = vi.fn()
    const { result } = renderHook(() => useVoiceRecording({ onSecondTick: tick }))
    await act(async () => { await result.current.startRecording(target) })
    act(() => instances[0].onstart())
    expect(tick).toHaveBeenCalledTimes(1)
    act(() => result.current.stopRecording())
  })

  it('stops recognition if the workspace closes before the browser starts it', async () => {
    const stop = vi.fn()
    class PendingSpeech {
      start() {}
      stop() { stop(); this.onend?.() }
    }
    vi.stubGlobal('SpeechRecognition', PendingSpeech)
    const { result, rerender } = renderHook(({ enabled }) => useVoiceRecording({ enabled }), {
      initialProps: { enabled: true },
    })
    await act(async () => { await result.current.startRecording(target) })
    expect(result.current.isStarting).toBe(true)
    rerender({ enabled: false })
    expect(stop).toHaveBeenCalledOnce()
    expect(result.current.isStarting).toBe(false)
  })

  it('releases browser recognition after an error and ignores later events', async () => {
    const stop = vi.fn()
    let recognition
    class Speech {
      constructor() { recognition = this }
      start() { this.onstart() }
      stop() { stop(); this.onend?.() }
    }
    vi.stubGlobal('SpeechRecognition', Speech)
    const insert = vi.fn()
    const recover = vi.fn()
    const { result } = renderHook(() => useVoiceRecording({ onTranscript: insert, onRecoveredTranscript: recover }))
    await act(async () => { await result.current.startRecording(target) })
    act(() => recognition.onerror({ error: 'network' }))
    const speechResult = [{ transcript: 'unusable' }]
    speechResult.isFinal = true
    act(() => recognition.onresult({ resultIndex: 0, results: [speechResult] }))
    expect(stop).toHaveBeenCalledOnce()
    expect(result.current.error).toMatch(/network/i)
    expect(insert).not.toHaveBeenCalled()
    expect(recover).not.toHaveBeenCalled()
  })

  it('delivers a final result after a user stop and ignores events after recognition ends', async () => {
    let recognition
    class Speech {
      constructor() { recognition = this }
      start() { this.onstart() }
      stop() {}
    }
    vi.stubGlobal('SpeechRecognition', Speech)
    const insert = vi.fn()
    const recover = vi.fn()
    const { result } = renderHook(() => useVoiceRecording({ onTranscript: insert, onRecoveredTranscript: recover }))
    await act(async () => { await result.current.startRecording(target) })
    act(() => result.current.stopRecording())
    const final = [{ transcript: 'final result' }]
    expect(result.current.isTranscribing).toBe(true)
    final.isFinal = true
    act(() => recognition.onresult({ resultIndex: 0, results: [final] }))
    expect(insert).toHaveBeenCalledWith('final result', target)
    act(() => recognition.onend())
    act(() => recognition.onresult({ resultIndex: 0, results: [final] }))
    expect(insert).toHaveBeenCalledOnce()
    expect(recover).not.toHaveBeenCalled()
  })

  it('cancels pending transcription without insertion or losing newer input', async () => {
    const transcription = deferred()
    transcribeAudio.mockReturnValue(transcription.promise)
    const insert = vi.fn()
    const recover = vi.fn()
    const { result } = renderHook(() => useVoiceRecording({ onTranscript: insert, onRecoveredTranscript: recover }))
    await act(async () => { await result.current.startRecording(target) })
    act(() => result.current.stopRecording())
    await waitFor(() => expect(result.current.isTranscribing).toBe(true))
    act(() => result.current.cancelRecording())
    expect(result.current.isTranscribing).toBe(false)
    await act(async () => { transcription.resolve({ text: 'cancelled words' }); await transcription.promise })
    expect(insert).not.toHaveBeenCalled()
    expect(recover).not.toHaveBeenCalled()
    expect(stopTrack).toHaveBeenCalledOnce()
  })
})
