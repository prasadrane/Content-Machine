import { act, fireEvent, render, screen } from '@testing-library/react'
import { expect, it, vi } from 'vitest'
import InterviewModal from './InterviewModal'
import { useVoiceRecording } from '../../hooks/useVoiceRecording'
import { getBrief, synthesizeDraft } from '../../api/interview'

vi.mock('../../hooks/useVoiceRecording', () => ({ useVoiceRecording: vi.fn(() => ({ startRecording: vi.fn(), recordingTarget: null, isTranscribing: false, error: '', setError: vi.fn() })) }))
vi.mock('../../api/interview', () => ({ getBrief: vi.fn().mockResolvedValue({ summary: 'Source summary', questions: [] }), synthesizeDraft: vi.fn() }))

const item = { title: 'A source signal' }

it('preserves typed notes and manual continuation after briefing and synthesis fail', async () => {
  getBrief.mockRejectedValueOnce(new Error('Briefing unavailable'))
  synthesizeDraft.mockRejectedValueOnce(new Error('Synthesis unavailable'))
  const done = vi.fn(), skip = vi.fn()
  render(<InterviewModal item={item} onClose={vi.fn()} onSkipToCouncil={skip} onSynthesizeComplete={done} />)
  await screen.findByText(/could not load automated briefing/i)
  const notes = screen.getByPlaceholderText(/Paste voice dictation/i)
  fireEvent.change(notes, { target: { value: '  My actual notes\n' } })
  fireEvent.click(screen.getByRole('button', { name: /synthesize grounded draft/i }))
  await screen.findByText('Synthesis unavailable')
  expect(notes).toHaveValue('  My actual notes\n')
  expect(done).not.toHaveBeenCalled()
  expect(screen.getByRole('button', { name: /synthesize grounded draft/i })).toBeEnabled()
  fireEvent.click(screen.getByRole('button', { name: /skip to manual drafting/i }))
  expect(skip).toHaveBeenCalledWith(item)
})
it('removes inactive portal, disables recording and preserves notes on resume', async () => {
  const props = { item, onClose: vi.fn(), onSkipToCouncil: vi.fn(), onSynthesizeComplete: vi.fn() }
  const { rerender } = render(<InterviewModal {...props} isActive />)
  await act(async () => {})
  const notes = screen.getByPlaceholderText(/Paste voice dictation/i)
  fireEvent.change(notes, { target: { value: 'My actual experience' } })
  rerender(<InterviewModal {...props} isActive={false} />)
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  expect(screen.queryByDisplayValue('My actual experience')).not.toBeInTheDocument()
  expect(useVoiceRecording).toHaveBeenLastCalledWith(expect.objectContaining({ enabled: false }))
  rerender(<InterviewModal {...props} isActive />)
  expect(screen.getByDisplayValue('My actual experience')).toBeVisible()
})

it('holds an inactive synthesis result until the author explicitly opens it', async () => {
  let resolve
  synthesizeDraft.mockReturnValue(new Promise(done => { resolve = done }))
  const done = vi.fn(), props = { item, onClose: vi.fn(), onSkipToCouncil: vi.fn(), onSynthesizeComplete: done }
  const { rerender } = render(<InterviewModal {...props} isActive />)
  await act(async () => {})
  fireEvent.click(screen.getByRole('button', { name: /synthesize grounded draft/i }))
  rerender(<InterviewModal {...props} isActive={false} />)
  await act(async () => { resolve({ draft: 'New grounded draft', spike_id: 'source' }) })
  expect(done).not.toHaveBeenCalled()
  rerender(<InterviewModal {...props} isActive />)
  fireEvent.click(screen.getByRole('button', { name: /open completed draft/i }))
  expect(done).toHaveBeenCalledWith('New grounded draft', 'source')
})

it('names the active dialog, focuses its close control and supports Escape', async () => {
  const close = vi.fn()
  render(<InterviewModal item={item} onClose={close} onSkipToCouncil={vi.fn()} onSynthesizeComplete={vi.fn()} />)
  await act(async () => {})
  const dialog = screen.getByRole('dialog', { name: 'Perspective on A source signal' })
  expect(screen.getByRole('button', { name: 'Close perspective interview' })).toHaveFocus()
  fireEvent.keyDown(dialog, { key: 'Escape' })
  expect(close).toHaveBeenCalledTimes(1)
})
