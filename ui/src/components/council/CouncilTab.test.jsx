import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
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
      <CouncilTab draft="Seed draft" setDraft={vi.fn()} spikeId="spike-1" setSpikeId={vi.fn()} onSendToDistribute={vi.fn()} />,
    )
    await waitFor(() => expect(councilApi.getCouncilSpikes).toHaveBeenCalledTimes(1))
    expect(councilApi.getCouncilHistory).toHaveBeenCalledWith('spike-1')
    expect(screen.getByDisplayValue('Seed draft')).toBeInTheDocument()
  })
})
