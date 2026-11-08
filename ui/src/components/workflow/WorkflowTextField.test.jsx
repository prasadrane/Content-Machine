import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import WorkflowTextField from './WorkflowTextField'

const voice = vi.hoisted(() => ({ options: null, start: vi.fn() }))
vi.mock('../../hooks/useVoiceRecording', () => ({
  useVoiceRecording: options => {
    voice.options = options
    return { isRecording: false, isTranscribing: false, error: '', startRecording: voice.start }
  },
}))
describe('workflow dictation', () => {
  it('appends to the latest value and ignores delayed text after disabling or leaving the field', () => {
    const change = vi.fn()
    const { rerender, unmount } = render(<WorkflowTextField label="Notes" value="old" onChange={change} />)
    fireEvent.click(screen.getByRole('button', { name: 'Dictate Notes' }))
    const token = voice.start.mock.calls.at(-1)[0]
    voice.options.onTranscript('spoken', token)
    expect(change.mock.calls[0][0]('newer exact notes  ')).toBe('newer exact notes  \nspoken')
    expect(screen.getByRole('textbox', { name: 'Notes' })).toHaveValue('old')
    rerender(<WorkflowTextField label="Notes" value="new" onChange={change} enabled={false} />)
    const late = voice.options.onTranscript
    late('disabled callback', token)
    rerender(<WorkflowTextField label="Notes" value="new" onChange={change} enabled />)
    voice.options.onTranscript('old session after re-enable', token)
    unmount()
    late('unmounted callback', token)
    expect(change).toHaveBeenCalledOnce()
  })
})
