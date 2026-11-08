import { describe, expect, it, vi } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import HistoryPanel from './HistoryPanel'
import { getVersion } from '../../api/workflow'

vi.mock('../../api/workflow', () => ({ getVersion: vi.fn() }))

const history = {
  versions: [
    { version_id: 'ver-one', revision: 1, purpose: 'approval', created_at: '2026-11-05T10:00:00.000Z' },
    { version_id: 'ver-two', revision: 2, purpose: 'skip_review', created_at: '2026-11-05T11:00:00.000Z' },
  ],
  approvals: [
    { approval_id: 'approval-one', version_id: 'ver-one', status: 'historical', approved_at: '2026-11-05T10:01:00.000Z' },
  ],
}

describe('version history', () => {
  it('keeps the current comparison input when a later snapshot fails to load', async () => {
    getVersion.mockResolvedValueOnce({ version: { item_id: 'one', version_id: 'ver-one', revision: 1,
      artifact: { segments: ['Historical text'] } } }).mockRejectedValueOnce(new Error('Snapshot unavailable'))
    const props = { itemId: 'one', history, busy: false, dirty: true, onRestore: vi.fn(), onClose: vi.fn() }
    const { rerender } = render(<HistoryPanel {...props} currentArtifact={{ segments: ['Unsaved notes'] }} />)
    await userEvent.click(screen.getByRole('button', { name: 'Compare revision 1' }))
    await screen.findByText('Historical text')
    await userEvent.click(screen.getByRole('button', { name: 'Compare revision 2' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Snapshot unavailable')
    rerender(<HistoryPanel {...props} currentArtifact={{ segments: ['Newer unsaved notes'] }} />)
    expect(screen.getByText('Historical text')).toBeInTheDocument()
    expect(screen.getByText('Newer unsaved notes')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Restore revision 2' })).toBeDisabled()
    expect(props.onRestore).not.toHaveBeenCalled()
  })
  it('loads an owned snapshot read-only and compares it without restoring or approving', async () => {
    getVersion.mockResolvedValue({ version: { item_id: 'one', version_id: 'ver-one', revision: 1,
      artifact: { segments: ['  Historical text\n'] }, context: { notes: 'Old notes', sources: [] } } })
    const restore = vi.fn()
    render(<HistoryPanel itemId="one" currentArtifact={{ segments: ['Unsaved current text'] }}
      history={history} busy={false} dirty onRestore={restore} onClose={vi.fn()} />)
    await userEvent.click(screen.getByRole('button', { name: 'Compare revision 1' }))
    const comparison = await screen.findByRole('region', { name: 'Snapshot comparison' })
    expect(within(comparison).getByText('Historical text').textContent).toBe('  Historical text\n')
    expect(within(comparison).getByText('Unsaved current text')).toBeInTheDocument()
    expect(within(comparison).queryByRole('textbox')).not.toBeInTheDocument()
    expect(restore).not.toHaveBeenCalled()
    expect(getVersion).toHaveBeenCalledWith('one', 'ver-one')
  })
  it('shows the actual revisions, purposes, timestamps and recorded approval state', () => {
    const { container } = render(<HistoryPanel history={history} busy={false} dirty={false} onRestore={vi.fn()} onClose={vi.fn()} />)
    expect(screen.getByRole('region', { name: /version history/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /revision 1/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /revision 2/i })).toBeInTheDocument()
    expect(screen.getByText('Approval')).toBeInTheDocument()
    expect(screen.getByText('Review skipped')).toBeInTheDocument()
    expect(screen.getByText('Previously approved')).toBeInTheDocument()
    expect(container.querySelector('time[datetime="2026-11-05T10:00:00.000Z"]')).toBeInTheDocument()
    expect(container.querySelector('time[datetime="2026-11-05T11:00:00.000Z"]')).toBeInTheDocument()
    expect(screen.getAllByText(/approved/i)).toHaveLength(1)
  })

  it('restores only the requested version and closes on request', async () => {
    const onRestore = vi.fn()
    const onClose = vi.fn()
    render(<HistoryPanel history={history} busy={false} dirty={false} onRestore={onRestore} onClose={onClose} />)
    await userEvent.click(screen.getByRole('button', { name: 'Restore revision 2' }))
    expect(onRestore).toHaveBeenCalledOnce()
    expect(onRestore).toHaveBeenCalledWith('ver-two')
    await userEvent.click(screen.getByRole('button', { name: /close history/i }))
    expect(onClose).toHaveBeenCalledOnce()
  })

  it('keeps restore unavailable while changes are unsaved or a request is running', () => {
    const restore = vi.fn()
    const { rerender } = render(<HistoryPanel history={history} busy={false} dirty onRestore={restore} onClose={vi.fn()} />)
    expect(screen.getByText(/save.*changes.*before restoring/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Restore revision 1' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Restore revision 2' })).toBeDisabled()
    rerender(<HistoryPanel history={history} busy dirty={false} onRestore={restore} onClose={vi.fn()} />)
    expect(screen.getByRole('button', { name: 'Restore revision 1' })).toBeDisabled()
    expect(restore).not.toHaveBeenCalled()
  })

  it('offers an empty state without inventing versions or approval', () => {
    render(<HistoryPanel history={{ versions: [], approvals: [] }} busy={false} dirty={false} onRestore={vi.fn()} onClose={vi.fn()} />)
    const region = screen.getByRole('region', { name: /version history/i })
    expect(within(region).getByText(/no saved snapshots/i)).toBeInTheDocument()
    expect(within(region).queryByRole('button', { name: /restore revision/i })).not.toBeInTheDocument()
    expect(within(region).queryByText('Previously approved')).not.toBeInTheDocument()
  })
})
