import { describe, expect, it, vi } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ContentList from './ContentList'

const item = { item_id: 'item-11111111', title: 'Indexing', destination: 'linkedin',
  format: 'linkedin_post', stage: 'draft_review', working_revision: 3,
  updated_at: '2026-11-05T09:12:00.000Z' }
const props = changes => ({ items: [], loading: false, busy: false, error: '',
  open: vi.fn(), refresh: vi.fn(), setScreen: vi.fn(), ...changes })

describe('saved content landing', () => {
  it('labels only stored guest examples, including edited titles and later refreshes', () => {
    const demo = { ...item, title: 'My edited title', guest_example_label: 'Demo example' }
    const privateItem = { ...item, item_id: 'private', title: 'Example: Safer retries' }
    const flow = props({ items: [demo, privateItem] })
    const { rerender } = render(<ContentList flow={flow} />)
    expect(within(screen.getByText('My edited title').closest('article')).getByText('Demo example')).toBeInTheDocument()
    expect(within(screen.getByText(privateItem.title).closest('article')).queryByText('Demo example')).not.toBeInTheDocument()
    rerender(<ContentList flow={{ ...flow, items: [{ ...demo, working_revision: 4 }, privateItem] }} />)
    expect(screen.getAllByText('Demo example')).toHaveLength(1)
  })

  it('keeps same-title private items and absent provenance unlabelled', () => {
    render(<ContentList flow={props({ items: [
      { ...item, guest_example_label: 'Demo example' },
      { ...item, item_id: 'private', guest_example_label: null },
      { ...item, item_id: 'legacy' },
    ] })} />)
    expect(screen.getAllByText('Demo example')).toHaveLength(1)
  })

  it('distinguishes same-title items and resumes their actual identities', async () => {
    const flow = props({ items: [item, { ...item, item_id: 'item-22222222' }] })
    render(<ContentList flow={flow} />)
    const first = screen.getByRole('button', { name: 'Resume Indexing, reference 11111111' })
    const second = screen.getByRole('button', { name: 'Resume Indexing, reference 22222222' })
    expect(screen.getByText('Reference 11111111')).toBeInTheDocument()
    expect(screen.getByText('Reference 22222222')).toBeInTheDocument()
    await userEvent.click(first)
    await userEvent.click(second)
    expect(flow.open.mock.calls).toEqual([['item-11111111'], ['item-22222222']])
  })

  it('searches saved records, distinguishes no matches and clears the filter', async () => {
    render(<ContentList flow={props({ items: [item] })} />)
    await userEvent.type(screen.getByRole('searchbox', { name: 'Search saved content' }), 'unmatched')
    expect(screen.getByText('No saved content matches this search.')).toBeInTheDocument()
    expect(screen.queryByText(/no saved content yet/i)).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Clear search' }))
    expect(screen.getByRole('button', { name: 'Resume Indexing' })).toBeInTheDocument()
  })

  it('retains records with a stale indication after refresh fails', () => {
    render(<ContentList flow={props({ items: [item], error: 'Refresh failed' })} />)
    expect(screen.getByRole('button', { name: 'Resume Indexing' })).toBeInTheDocument()
    expect(screen.getByText(/showing previously loaded saved content/i)).toBeInTheDocument()
  })

  it('keeps loading, failed loading and a real empty workspace distinct', () => {
    const { rerender } = render(<ContentList flow={props({ items: null, loading: true })} />)
    expect(screen.getByRole('status')).toHaveTextContent('Loading saved content')
    expect(screen.queryByText(/no saved content yet/i)).not.toBeInTheDocument()
    rerender(<ContentList flow={props({ items: null, error: 'Load failed' })} />)
    expect(screen.queryByText(/no saved content yet/i)).not.toBeInTheDocument()
    rerender(<ContentList flow={props()} />)
    expect(screen.getByText(/no saved content yet/i)).toBeInTheDocument()
  })
})
