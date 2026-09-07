import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import DraftingStudio from './DraftingStudio'

describe('DraftingStudio', () => {
  it('renders draft, spike input, and recent spikes', () => {
    const onDraftChange = vi.fn()
    const onSpikeChange = vi.fn()
    const onSelectSpike = vi.fn()
    const onSubmit = vi.fn((e) => e.preventDefault())

    render(
      <DraftingStudio
        draft="Sample draft"
        onDraftChange={onDraftChange}
        spikeId="spike-1"
        onSpikeChange={onSpikeChange}
        recentSpikes={[
          { spike_id: 'spike-1', peak_score: 8.5 },
          { spike_id: 'spike-2', peak_score: 7.2 },
        ]}
        onSelectSpike={onSelectSpike}
        loading={false}
        error=""
        onSubmit={onSubmit}
      />
    )

    expect(screen.getByDisplayValue('Sample draft')).toBeInTheDocument()
    expect(screen.getByDisplayValue('spike-1')).toBeInTheDocument()
    expect(screen.getByText('spike-2')).toBeInTheDocument()

    // Test spike select click
    fireEvent.click(screen.getByText('spike-2'))
    expect(onSelectSpike).toHaveBeenCalledWith('spike-2')

    // Test submit
    fireEvent.click(screen.getByRole('button', { name: /Submit to Council/i }))
    expect(onSubmit).toHaveBeenCalled()
  })

  it('renders error message when present', () => {
    render(
      <DraftingStudio
        draft=""
        onDraftChange={vi.fn()}
        spikeId=""
        onSpikeChange={vi.fn()}
        recentSpikes={[]}
        onSelectSpike={vi.fn()}
        loading={false}
        error="Draft text cannot be empty."
        onSubmit={vi.fn()}
      />
    )

    expect(screen.getByText('Draft text cannot be empty.')).toBeInTheDocument()
  })

  it('displays loading indicator when loading', () => {
    render(
      <DraftingStudio
        draft="Draft"
        onDraftChange={vi.fn()}
        spikeId=""
        onSpikeChange={vi.fn()}
        recentSpikes={[]}
        onSelectSpike={vi.fn()}
        loading={true}
        error=""
        onSubmit={vi.fn()}
      />
    )

    expect(screen.getByText('Council Deliberating & Revising...')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Council Deliberating/i })).toBeDisabled()
  })
})
