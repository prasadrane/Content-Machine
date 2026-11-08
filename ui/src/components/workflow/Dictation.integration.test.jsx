import { useState } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { act, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import WorkflowTextField from './WorkflowTextField'

let recognition
class Speech {
  constructor() { recognition = this }
  start() { this.onstart() }
  stop() {}
}
function Field() {
  const [text, setText] = useState('Typed notes')
  return <WorkflowTextField label="Your notes" value={text} onChange={setText} />
}
beforeEach(() => {
  vi.stubGlobal('SpeechRecognition', Speech)
  vi.stubGlobal('webkitSpeechRecognition', undefined)
})
afterEach(() => vi.unstubAllGlobals())

describe('field dictation controls', () => {
  it('supports keyboard start/stop/cancel and ignores results after cancellation', async () => {
    render(<Field />)
    const user = userEvent.setup()
    await user.tab()
    expect(screen.getByRole('button', { name: 'Dictate Your notes' })).toHaveFocus()
    await user.keyboard('{Enter}')
    expect(screen.getByRole('status')).toHaveTextContent('Listening')
    await user.keyboard('{Enter}')
    expect(screen.getByRole('status')).toHaveTextContent('Transcribing')
    screen.getByRole('button', { name: 'Cancel dictation' }).focus()
    await user.keyboard('{Enter}')
    const final = [{ transcript: 'Cancelled speech' }]
    final.isFinal = true
    act(() => recognition.onresult({ resultIndex: 0, results: [final] }))
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
    expect(screen.getByRole('textbox', { name: 'Your notes' })).toHaveValue('Typed notes')
    await user.click(screen.getByText('How dictation works'))
    expect(screen.getByText(/recorded audio is sent to this app's transcription service/i)).toBeInTheDocument()
  })

  it('keeps typing available after microphone permission denial', async () => {
    vi.stubGlobal('SpeechRecognition', undefined)
    Object.defineProperty(navigator, 'mediaDevices', { configurable: true,
      value: { getUserMedia: vi.fn().mockRejectedValue(new Error('denied')) } })
    render(<Field />)
    await userEvent.click(screen.getByRole('button', { name: 'Dictate Your notes' }))
    expect(await screen.findByRole('alert')).toHaveTextContent(/microphone access denied/i)
    await userEvent.type(screen.getByRole('textbox', { name: 'Your notes' }), ' plus typing')
    expect(screen.getByRole('textbox', { name: 'Your notes' })).toHaveValue('Typed notes plus typing')
  })
})
