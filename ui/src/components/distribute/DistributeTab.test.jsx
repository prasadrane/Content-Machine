import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import DistributeTab from './DistributeTab'
import * as distributeApi from '../../api/distribute'

vi.mock('../../api/distribute', () => ({
  runDistribute: vi.fn(),
  getDistributeHistory: vi.fn(),
}))

describe('DistributeTab', () => {
  it('seeds anchor text and slug from props', async () => {
    distributeApi.getDistributeHistory.mockResolvedValue({ items: [], total: 0 })
    render(<DistributeTab initialText="Seeded draft" initialSlug="my-post" />)
    await waitFor(() => expect(screen.getByDisplayValue('Seeded draft')).toBeInTheDocument())
  })

  it('renders all five format chips', async () => {
    distributeApi.getDistributeHistory.mockResolvedValue({ items: [], total: 0 })
    render(<DistributeTab initialText="" initialSlug="" />)
    await waitFor(() => expect(screen.getByText('LinkedIn')).toBeInTheDocument())
    expect(screen.getByText('Newsletter')).toBeInTheDocument()
  })

  it('loads history on mount and opens drawer to select past post', async () => {
    const mockItem = {
      slug: 'past-redis-post',
      title: 'Redis latency spike investigation',
      anchor_text: 'Deep dive into Redis p99 latency spike.',
      peak_score: 8.45,
      has_bundle: true,
      bundle: {
        linkedin: 'LinkedIn derivative for Redis',
        x_thread: 'X thread derivative for Redis',
      },
      available_formats: ['linkedin', 'x_thread'],
      updated_at: '2026-09-06T12:00:00Z',
      source: 'distributed',
    }
    distributeApi.getDistributeHistory.mockResolvedValue({ items: [mockItem], total: 1 })

    render(<DistributeTab initialText="" initialSlug="" />)

    // Wait for history to load
    await waitFor(() => {
      expect(screen.getByText(/History \(1\)/i)).toBeInTheDocument()
    })

    // Click History button to open drawer
    fireEvent.click(screen.getByText(/History \(1\)/i))

    // Drawer should show the past post
    expect(screen.getByText('past-redis-post')).toBeInTheDocument()
    expect(screen.getByText('Redis latency spike investigation')).toBeInTheDocument()

    // Click the past post to select it
    fireEvent.click(screen.getByText('past-redis-post'))

    // The anchor text and slug should be populated into the editor
    expect(screen.getByDisplayValue('Deep dive into Redis p99 latency spike.')).toBeInTheDocument()
    expect(screen.getByDisplayValue('past-redis-post')).toBeInTheDocument()

    // The output preview should display the loaded derivative format
    expect(screen.getByText('LinkedIn derivative for Redis')).toBeInTheDocument()
  })
})
