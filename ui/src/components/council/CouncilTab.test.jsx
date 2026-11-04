import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import CouncilTab from './CouncilTab'
import * as councilApi from '../../api/council'

vi.mock('../../api/council', () => ({
  runCouncil: vi.fn(),
  getCouncilHistory: vi.fn(),
  getCouncilSpikes: vi.fn(),
}))
vi.mock('../../api/humanize', () => ({ runHumanize: vi.fn() }))

describe('CouncilTab', () => {
  it.each([
    ['edited wording', 'My edited wording', 'item-1', 2],
    ['a new item with identical wording', 'Reviewed wording', 'item-2', 1],
  ])('allows explicit approval of %s without borrowing the previous verdict', async (_, text, itemId, version) => {
    councilApi.getCouncilSpikes.mockResolvedValue([])
    councilApi.getCouncilHistory.mockResolvedValue({ history: [] })
    councilApi.runCouncil.mockResolvedValue({ verdict: 'pass', score: 9.3, iteration: 1, draft: 'Reviewed wording', actions: [] })
    const onApprove = vi.fn()
    const props = { draft: 'Reviewed wording', spikeId: 'story', setDraft: vi.fn(), setSpikeId: vi.fn(), onApprove, councilIdentity: { itemId: 'item-1', version: 1 } }
    const { rerender } = render(<CouncilTab {...props} />)
    fireEvent.click(screen.getByRole('button', { name: /submit to council/i }))
    await screen.findByRole('button', { name: /approve & distribute/i })
    rerender(<CouncilTab {...props} draft={text} councilIdentity={{ itemId, version }} />)
    fireEvent.click(screen.getByRole('button', { name: /approve & distribute/i }))
    const dialog = screen.getByRole('dialog', { name: /approve draft/i })
    expect(dialog).toHaveTextContent(text)
    expect(dialog).toHaveTextContent('unreviewed')
    expect(onApprove).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('checkbox'))
    fireEvent.click(screen.getByRole('button', { name: /approve & send to distribute/i }))
    expect(onApprove).toHaveBeenCalledWith(text, 'story')
    expect(councilApi.runCouncil).toHaveBeenCalledTimes(1)
  })
  it('compares a historical replacement before changing the working draft', async () => {
    councilApi.getCouncilSpikes.mockResolvedValue([])
    councilApi.getCouncilHistory.mockResolvedValue({ best: { iteration: 1, score: 9.3, draft: 'Earlier reviewed wording' }, history: [] })
    const setDraft = vi.fn()
    render(<CouncilTab draft="My current wording" setDraft={setDraft} spikeId="story" setSpikeId={vi.fn()} />)
    fireEvent.click(await screen.findByRole('button', { name: /load peak draft/i }))
    expect(setDraft).not.toHaveBeenCalled()
    expect(screen.getByText('My current wording', { selector: 'pre' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /keep current|cancel/i }))
    expect(setDraft).not.toHaveBeenCalled()
  })
  it('loads spikes + history on mount, seeds draft from props', async () => {
    councilApi.getCouncilSpikes.mockResolvedValue([])
    councilApi.getCouncilHistory.mockResolvedValue({ spike_id: 'spike-1', history: [] })
    render(
      <CouncilTab draft="Seed draft" setDraft={vi.fn()} spikeId="spike-1" setSpikeId={vi.fn()} onApprove={vi.fn()} />,
    )
    await waitFor(() => expect(councilApi.getCouncilSpikes).toHaveBeenCalledTimes(1))
    expect(councilApi.getCouncilHistory).toHaveBeenCalledWith('spike-1')
    expect(screen.getByDisplayValue('Seed draft')).toBeInTheDocument()
  })

  it('routes the peak post through the approval gate before onApprove fires', async () => {
    councilApi.getCouncilSpikes.mockResolvedValue([])
    councilApi.getCouncilHistory.mockResolvedValue({
      spike_id: 'spike-1',
      best: { id: 1, iteration: 1, score: 9.3, verdict: 'pass', threshold_met: true, draft: 'Peak draft text', actions: [], scores: {} },
      history: [{ id: 1, iteration: 1, score: 9.3, verdict: 'pass', threshold_met: true, draft: 'Peak draft text', actions: [], scores: {} }],
    })
    const onApprove = vi.fn()
    render(<CouncilTab draft="d" setDraft={vi.fn()} spikeId="spike-1" setSpikeId={vi.fn()} onApprove={onApprove} />)
    fireEvent.click(await screen.findByRole('button', { name: /approve peak post/i }))
    expect(onApprove).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('checkbox'))
    fireEvent.click(screen.getByRole('button', { name: /approve & send to distribute/i }))
    expect(onApprove).toHaveBeenCalledWith('Peak draft text', 'spike-1')
  })
})
