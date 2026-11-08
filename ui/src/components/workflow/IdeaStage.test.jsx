import { useState } from 'react'
import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import IdeaStage from './IdeaStage'
import { refreshDiscovery } from '../../api/discovery'

vi.mock('../../api/discovery', () => ({ refreshDiscovery: vi.fn() }))
vi.mock('../../hooks/useVoiceRecording', () => ({
  useVoiceRecording: () => ({ isRecording: false, isTranscribing: false, error: '' }),
}))

const source = {
  source_id: 'feed-1', source_name: 'Engineering feed', title: 'A real source',
  url: 'https://example.com/story', excerpt: 'Source excerpt', fetched_at: '2026-11-06T10:00:00.000Z',
}
function Example({ onManageSources = () => {} }) {
  const [draft, updateDraft] = useState({ context: { notes: 'My own notes', sources: [] }, artifact: { segments: [] } })
  const flow = { item: { item_id: 'item-1' }, draft, updateDraft, busy: false, continueToDraft: vi.fn() }
  return <><IdeaStage flow={flow} isActive onManageSources={onManageSources} />
    <output data-testid="draft">{JSON.stringify(draft)}</output></>
}
describe('idea source integration', () => {
  it('attaches and removes the selected source while preserving the creator’s notes', async () => {
    refreshDiscovery.mockResolvedValue({ status: 'ok', items: [source], errors: [], unchanged_sources: [] })
    render(<Example />)
    expect(screen.getByRole('button', { name: 'Your idea' })).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Discover ideas' }))
    await userEvent.click(screen.getByRole('button', { name: 'Find ideas' }))
    await userEvent.click(await screen.findByRole('button', { name: 'Use A real source' }))
    const draft = JSON.parse(screen.getByTestId('draft').textContent)
    expect(draft.context.notes).toBe('My own notes')
    expect(draft.context.sources).toEqual([{ source_id: source.source_id, title: source.title,
      url: source.url, excerpt: source.excerpt, fetched_at: source.fetched_at }])
    await userEvent.click(screen.getByRole('button', { name: 'Remove A real source' }))
    expect(JSON.parse(screen.getByTestId('draft').textContent).context).toEqual({ notes: 'My own notes', sources: [] })
  })
  it('offers source settings from discovery', async () => {
    const onManageSources = vi.fn()
    render(<Example onManageSources={onManageSources} />)
    await userEvent.click(screen.getByRole('button', { name: 'Discover ideas' }))
    await userEvent.click(screen.getByRole('button', { name: 'Manage sources' }))
    expect(onManageSources).toHaveBeenCalledOnce()
  })
})
