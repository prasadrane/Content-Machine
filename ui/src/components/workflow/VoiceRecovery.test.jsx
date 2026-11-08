import { describe, expect, it, vi } from 'vitest'
import { act, fireEvent, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { VoiceRecoveryProvider, VoiceRecoveryPanel } from './VoiceRecovery'
import WorkflowTextField from './WorkflowTextField'

const voice = vi.hoisted(() => ({ options: null, start: vi.fn() }))
vi.mock('../../hooks/useVoiceRecording', () => ({
  useVoiceRecording: options => {
    voice.options = options
    return { isRecording: false, isTranscribing: false, error: '', startRecording: voice.start }
  },
}))
const identity = { ownerId: 'owner-a', itemId: 'item-a', revision: 2 }
function Workspace({ showField = true, item = identity, value = 'original', change = vi.fn() }) {
  return <VoiceRecoveryProvider identity={item}>
    {showField && <WorkflowTextField label="Your notes" value={value} onChange={change} />}
    <VoiceRecoveryPanel />
  </VoiceRecoveryProvider>
}
describe('voice recovery', () => {
  it('retains a late transcript after its field unmounts and offers explicit copy', async () => {
    const copy = vi.fn().mockResolvedValue()
    Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText: copy } })
    const change = vi.fn()
    const { rerender } = render(<Workspace change={change} />)
    await userEvent.click(screen.getByRole('button', { name: 'Dictate Your notes' }))
    const target = voice.start.mock.calls.at(-1)[0]
    const callback = voice.options.onRecoveredTranscript
    expect(target).toMatchObject({ ownerId: 'owner-a', itemId: 'item-a', revision: 2, field: 'Your notes' })
    rerender(<Workspace showField={false} item={{ ...identity, itemId: 'item-b' }} change={change} />)
    act(() => callback('A spoken observation', target))
    await userEvent.click(screen.getByRole('button', { name: /show recovered transcripts/i }))
    const entry = await screen.findByRole('listitem')
    expect(within(entry).getByText('A spoken observation')).toBeInTheDocument()
    expect(within(entry).getByText(/item-a/)).toBeInTheDocument()
    expect(within(entry).getByText(/Your notes/)).toBeInTheDocument()
    fireEvent.change(within(entry).getByRole('textbox', { name: /recovered transcript/i }), { target: { value: 'Edited observation' } })
    await userEvent.click(within(entry).getByRole('button', { name: /copy transcript/i }))
    expect(copy).toHaveBeenCalledWith('Edited observation')
    expect(change).not.toHaveBeenCalled()
  })

  it('treats a changed field as unsafe and routes its text into recovery', async () => {
    const change = vi.fn()
    const { rerender } = render(<Workspace change={change} />)
    await userEvent.click(screen.getByRole('button', { name: 'Dictate Your notes' }))
    const target = voice.start.mock.calls.at(-1)[0]
    expect(voice.options.isTargetCurrent(target)).toBe(true)
    rerender(<Workspace value="typed newer text" change={change} />)
    expect(voice.options.isTargetCurrent(target)).toBe(false)
    act(() => voice.options.onRecoveredTranscript('Recover this', target))
    expect(change).not.toHaveBeenCalled()
  })

  it('allows consecutive recognized phrases while the creator has not edited the field', async () => {
    let current = 'original'
    const change = vi.fn(updater => { current = updater(current) })
    const { rerender } = render(<Workspace value={current} change={change} />)
    await userEvent.click(screen.getByRole('button', { name: 'Dictate Your notes' }))
    const target = voice.start.mock.calls.at(-1)[0]
    act(() => voice.options.onTranscript('first phrase', target))
    rerender(<Workspace value={current} change={change} />)
    expect(voice.options.isTargetCurrent(target)).toBe(true)
    act(() => voice.options.onTranscript('second phrase', target))
    expect(current).toBe('original\nfirst phrase\nsecond phrase')
  })

  it('does not show recovered transcripts under a different owner', async () => {
    const { rerender } = render(<Workspace />)
    await userEvent.click(screen.getByRole('button', { name: 'Dictate Your notes' }))
    const target = voice.start.mock.calls.at(-1)[0]
    act(() => voice.options.onRecoveredTranscript('Private owner A transcript', target))
    rerender(<Workspace item={{ ...identity, ownerId: 'owner-b', itemId: 'item-b' }} />)
    expect(screen.queryByText('Private owner A transcript')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /show recovered transcripts/i })).not.toBeInTheDocument()
  })

  it('keeps a late result for its original owner while another owner is active', async () => {
    const { rerender } = render(<Workspace />)
    await userEvent.click(screen.getByRole('button', { name: 'Dictate Your notes' }))
    const target = voice.start.mock.calls.at(-1)[0]
    const recover = voice.options.onRecoveredTranscript
    rerender(<Workspace item={{ ...identity, ownerId: 'owner-b', itemId: 'item-b' }} />)
    act(() => recover('Late private transcript', target))
    expect(screen.queryByText('Late private transcript')).not.toBeInTheDocument()
    rerender(<Workspace item={identity} />)
    await userEvent.click(screen.getByRole('button', { name: /show recovered transcripts/i }))
    expect(screen.getByText('Late private transcript')).toBeInTheDocument()
  })
})
