import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import DistributeHistoryDrawer from './DistributeHistoryDrawer'

const mockItems = [
  {
    slug: 'cloudflare-100tb-dns-cache',
    title: '100 TB of RAM vanished from an 8-byte struct header',
    anchor_text: '100 TB of RAM vanished from an 8-byte struct header. I spent my morning tearing down...',
    peak_score: 8.71,
    has_bundle: true,
    bundle: {
      linkedin: 'LinkedIn post content',
      x_thread: 'X thread content',
    },
    available_formats: ['linkedin', 'x_thread'],
    updated_at: '2026-09-05T18:01:35Z',
    source: 'distributed',
  },
  {
    slug: 'release-weekend',
    title: 'I killed a Friday release 4 hours before deploy',
    anchor_text: 'I killed a Friday release 4 hours before deploy. The commit held 4,200 lines...',
    peak_score: 8.58,
    has_bundle: false,
    bundle: {},
    available_formats: [],
    updated_at: '2026-09-06T04:58:09Z',
    source: 'council',
  },
]

describe('DistributeHistoryDrawer', () => {
  it('does not render when show is false', () => {
    const { container } = render(
      <DistributeHistoryDrawer
        show={false}
        onClose={vi.fn()}
        items={mockItems}
        loading={false}
        onSelect={vi.fn()}
      />
    )
    expect(container).toBeEmptyDOMElement()
  })

  it('renders history items and handles search and selection', () => {
    const onSelect = vi.fn()
    const onClose = vi.fn()

    render(
      <DistributeHistoryDrawer
        show={true}
        onClose={onClose}
        items={mockItems}
        loading={false}
        onSelect={onSelect}
      />
    )

    // Items should be displayed
    expect(screen.getByText('cloudflare-100tb-dns-cache')).toBeInTheDocument()
    expect(screen.getByText('release-weekend')).toBeInTheDocument()

    // Test filter search
    const searchInput = screen.getByPlaceholderText(/Search by slug or content/i)
    fireEvent.change(searchInput, { target: { value: 'cloudflare' } })
    expect(screen.getByText('cloudflare-100tb-dns-cache')).toBeInTheDocument()
    expect(screen.queryByText('release-weekend')).not.toBeInTheDocument()

    // Click select on the item
    fireEvent.click(screen.getByText('cloudflare-100tb-dns-cache'))
    expect(onSelect).toHaveBeenCalledWith(mockItems[0])

    // Test close button
    const closeBtn = screen.getByRole('button', { name: /close/i })
    fireEvent.click(closeBtn)
    expect(onClose).toHaveBeenCalled()
  })

  it('filters by category tab (All, Distributed, Council)', () => {
    render(
      <DistributeHistoryDrawer
        show={true}
        onClose={vi.fn()}
        items={mockItems}
        loading={false}
        onSelect={vi.fn()}
      />
    )

    // Filter to Council only
    const councilTab = screen.getByRole('button', { name: /Council Drafts/i })
    fireEvent.click(councilTab)

    expect(screen.getByText('release-weekend')).toBeInTheDocument()
    expect(screen.queryByText('cloudflare-100tb-dns-cache')).not.toBeInTheDocument()

    // Filter to Distributed only
    const distTab = screen.getByRole('button', { name: /Distributed/i })
    fireEvent.click(distTab)

    expect(screen.getByText('cloudflare-100tb-dns-cache')).toBeInTheDocument()
    expect(screen.queryByText('release-weekend')).not.toBeInTheDocument()
  })
})
