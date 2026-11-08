import { useState } from 'react'
import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import IdeaStage from './IdeaStage'
import DraftStage from './DraftStage'

vi.mock('./AIWorkflowPanel', () => ({ default: () => null }))
vi.mock('../../hooks/useVoiceRecording', () => ({
  useVoiceRecording: () => ({ isRecording: false, isTranscribing: false, error: '' }),
}))

function Example() {
  const [stage, setStage] = useState('idea')
  const [draft, updateDraft] = useState({ context: { notes: '  Original notes\n',
    experience: 'My observation', interpretation: 'A tradeoff',
    sources: [{ source_id: 'source', url: 'https://example.com/post', title: 'Evidence' }] },
    artifact: { segments: ['  Pasted draft\nsecond line  '] } })
  const flow = { item: { item_id: 'one', format: 'linkedin_post' }, draft, updateDraft,
    busy: false, dirty: false, review: null, continueToDraft: () => setStage('draft'), save: vi.fn(), skip: vi.fn() }
  return <>{stage === 'idea' ? <IdeaStage flow={flow} isActive /> : <DraftStage flow={flow} isActive />}
    <button onClick={() => setStage('idea')}>Return to idea</button></>
}

describe('shared idea and draft context', () => {
  it('edits the same optional context from the draft without changing pasted text', async () => {
    render(<Example />)
    await userEvent.click(screen.getByRole('button', { name: 'Continue to draft' }))
    expect(screen.getByRole('textbox', { name: 'Draft text' })).toHaveValue('  Pasted draft\nsecond line  ')
    await userEvent.click(screen.getByText('Idea and source context'))
    expect(screen.getByRole('textbox', { name: 'Your notes' })).toHaveValue('  Original notes\n')
    fireEvent.change(screen.getByRole('textbox', { name: 'Your notes' }), { target: { value: '  Updated notes\n' } })
    await userEvent.click(screen.getByText('Add your experience and perspective'))
    expect(screen.getByRole('textbox', { name: 'Your experience' })).toHaveValue('My observation')
    fireEvent.change(screen.getByRole('textbox', { name: 'Your interpretation' }), { target: { value: 'New interpretation' } })
    expect(screen.getByText('Evidence')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Return to idea' }))
    expect(screen.getByRole('textbox', { name: 'Your notes' })).toHaveValue('  Updated notes\n')
    await userEvent.click(screen.getByText('Add your experience and perspective'))
    expect(screen.getByRole('textbox', { name: 'Your interpretation' })).toHaveValue('New interpretation')
    await userEvent.click(screen.getByRole('button', { name: 'Continue to draft' }))
    expect(screen.getByRole('textbox', { name: 'Draft text' })).toHaveValue('  Pasted draft\nsecond line  ')
  })
})
