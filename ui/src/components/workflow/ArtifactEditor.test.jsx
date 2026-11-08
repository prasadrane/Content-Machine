import { useState } from 'react'
import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ArtifactEditor from './ArtifactEditor'

vi.mock('../../hooks/useVoiceRecording', () => ({
  useVoiceRecording: () => ({ isRecording: false, isTranscribing: false, error: '' }),
}))
function Editor() {
  const [draft, updateDraft] = useState({ artifact: { segments: ['first', 'second'] } })
  return <ArtifactEditor flow={{ item: { format: 'x_thread' }, draft, updateDraft, busy: false }} isActive />
}
describe('thread editor identity', () => {
  it('keeps each remaining field mounted when an earlier post is removed', async () => {
    render(<Editor />)
    const second = screen.getByRole('textbox', { name: 'Post 2' })
    await userEvent.click(screen.getByRole('button', { name: 'Remove post 1' }))
    expect(screen.getByRole('textbox', { name: 'Post 1' })).toBe(second)
    expect(second).toHaveValue('second')
  })
})
