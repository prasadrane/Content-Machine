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
