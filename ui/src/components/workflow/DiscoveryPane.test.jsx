import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import DiscoveryPane from './DiscoveryPane'
import { refreshDiscovery } from '../../api/discovery'

vi.mock('../../api/discovery', () => ({ refreshDiscovery: vi.fn() }))

const fetched = '2026-11-06T12:00:00.000Z'
const items = [
  { source_id: 'feed-a', source_name: 'Engineering feed', url: 'https://example.com/a', title: 'First result', excerpt: 'Exact source excerpt.', fetched_at: fetched },
  { source_id: 'feed-b', source_name: 'Other feed', url: 'https://example.com/b', title: 'Title only', excerpt: '', fetched_at: fetched },
]

beforeEach(() => vi.resetAllMocks())

describe('idea discovery', () => {
  it('returns a selected source without changing notes or inventing excerpt text', async () => {
    refreshDiscovery.mockResolvedValue({ status: 'partial', items, errors: [{ source_id: 'feed-c', source_name: 'Third feed', message: 'Could not retrieve this source.' }], history_available: false })
    const onUse = vi.fn()
    render(<DiscoveryPane attachedSources={[]} onUse={onUse} />)
    expect(refreshDiscovery).not.toHaveBeenCalled()
    await userEvent.click(screen.getByRole('button', { name: 'Find ideas' }))
    expect(await screen.findByText('Exact source excerpt.')).toBeInTheDocument()
    expect(screen.getByText('Title only', { selector: 'h3' })).toBeInTheDocument()
    expect(screen.getByText(/no excerpt available/i)).toBeInTheDocument()
    expect(screen.getByText(/Third feed.*could not retrieve/i)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Use Title only' }))
    expect(onUse).toHaveBeenCalledWith({ source_id: 'feed-b', url: 'https://example.com/b', title: 'Title only', excerpt: '', fetched_at: fetched })
  })

  it('filters and clears search while retaining exact attached-source identity', async () => {
    refreshDiscovery.mockResolvedValue({ status: 'ok', items, errors: [], history_available: false })
    render(<DiscoveryPane attachedSources={[items[0]]} onUse={vi.fn()} />)
    await userEvent.click(screen.getByRole('button', { name: 'Find ideas' }))
    expect(await screen.findByRole('button', { name: 'Already added First result' })).toBeDisabled()
    await userEvent.type(screen.getByRole('searchbox', { name: 'Search ideas' }), 'Title only')
    expect(screen.queryByText('First result', { selector: 'h3' })).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Clear search' }))
    expect(screen.getByText('First result', { selector: 'h3' })).toBeInTheDocument()
  })

  it('keeps earlier results visible when a later refresh fails', async () => {
    refreshDiscovery.mockResolvedValueOnce({ status: 'ok', items, errors: [] }).mockRejectedValueOnce(new Error('Network failed'))
    render(<DiscoveryPane attachedSources={[]} onUse={vi.fn()} />)
    await userEvent.click(screen.getByRole('button', { name: 'Find ideas' }))
    await screen.findByText('Exact source excerpt.')
    await userEvent.click(screen.getByRole('button', { name: 'Refresh ideas' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Network failed')
    expect(screen.getByText('Exact source excerpt.')).toBeInTheDocument()
  })

  it.each([
    ['no_sources', /add an enabled source/i],
    ['unavailable', /discovery is unavailable/i],
    ['empty', /no new ideas/i],
    ['history_unavailable', /previously found ideas are unavailable/i],
  ])('explains the %s outcome', async (status, message) => {
    refreshDiscovery.mockResolvedValue({ status, items: [], errors: [], history_available: false })
    render(<DiscoveryPane attachedSources={[]} onUse={vi.fn()} />)
    await userEvent.click(screen.getByRole('button', { name: 'Find ideas' }))
    expect(await screen.findByText(message)).toBeInTheDocument()
  })

  it('does not create links for non-web URLs returned by a feed', async () => {
    refreshDiscovery.mockResolvedValue({ status: 'ok', items: [{ ...items[0], url: 'javascript:alert(1)' }], errors: [] })
    render(<DiscoveryPane attachedSources={[]} onUse={vi.fn()} />)
    await userEvent.click(screen.getByRole('button', { name: 'Find ideas' }))
    expect(await screen.findByText('First result')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /open source/i })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Use First result' })).toBeDisabled()
  })

  it('identifies sources whose previous results could not be loaded', async () => {
    refreshDiscovery.mockResolvedValue({
      status: 'ok', items: [items[0]], errors: [],
      unchanged_sources: [{ source_id: 'feed-b', source_name: 'Other feed' }],
      history_available: false,
    })
    render(<DiscoveryPane attachedSources={[]} onUse={vi.fn()} />)
    await userEvent.click(screen.getByRole('button', { name: 'Find ideas' }))
    expect(await screen.findByText(/Other feed returned no new items/)).toBeInTheDocument()
    expect(screen.getByText('Exact source excerpt.')).toBeInTheDocument()
  })

  it('tells people when the time limit skipped some sources', async () => {
    refreshDiscovery.mockResolvedValue({ status: 'partial', items, errors: [], incomplete: true })
    render(<DiscoveryPane attachedSources={[]} onUse={vi.fn()} />)
    await userEvent.click(screen.getByRole('button', { name: 'Find ideas' }))
    expect(await screen.findByText('Time limit reached; some sources were skipped. Refresh again to continue.')).toBeInTheDocument()
    expect(screen.getByText(/Time limit reached/)).toHaveAttribute('role', 'status')
  })
})
