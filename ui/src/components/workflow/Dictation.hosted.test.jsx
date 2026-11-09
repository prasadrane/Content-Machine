import { afterEach, describe, expect, it, vi } from 'vitest'
import { act, render, renderHook, screen } from '@testing-library/react'
import WorkflowTextField from './WorkflowTextField'
import { useVoiceRecording } from '../../hooks/useVoiceRecording'
import { transcribeAudio } from '../../api/interview'

vi.mock('../../api/workspaceMode', () => ({ isHostedWorkspace: () => true }))
vi.mock('../../api/interview', () => ({ transcribeAudio: vi.fn() }))

afterEach(() => vi.unstubAllGlobals())

describe('hosted dictation', () => {
  it('hides Dictate without browser speech recognition and describes the hosted behavior', () => {
    render(<WorkflowTextField label="Notes" value="" onChange={() => {}} />)
    expect(screen.queryByRole('button', { name: /dictate notes/i })).not.toBeInTheDocument()
    expect(screen.getByText(/nothing is uploaded to this app/i)).toBeInTheDocument()
    expect(screen.queryByText(/transcription service/i)).not.toBeInTheDocument()
  })

  it('keeps Dictate when browser speech recognition exists', () => {
    vi.stubGlobal('SpeechRecognition', class {})
    render(<WorkflowTextField label="Notes" value="" onChange={() => {}} />)
    expect(screen.getByRole('button', { name: /dictate notes/i })).toBeInTheDocument()
  })

  it('never falls back to microphone upload when speech recognition is missing', async () => {
    const getUserMedia = vi.fn()
    vi.stubGlobal('navigator', { mediaDevices: { getUserMedia } })
    const { result } = renderHook(() => useVoiceRecording())
    await act(async () => { await result.current.startRecording('t') })
    expect(getUserMedia).not.toHaveBeenCalled()
    expect(transcribeAudio).not.toHaveBeenCalled()
    expect(result.current.error).toMatch(/isn't supported/i)
  })
})
