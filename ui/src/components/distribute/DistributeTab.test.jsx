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

  it('blocks generation until the exact text is approved', async () => {
    distributeApi.getDistributeHistory.mockResolvedValue({ items: [], total: 0 })
    distributeApi.runDistribute.mockResolvedValue({ linkedin: 'LI out' })
    render(<DistributeTab initialText="Unapproved draft" initialSlug="p" />)
    const generate = await screen.findByRole('button', { name: /generate platform bundle/i })
    expect(generate).toBeDisabled()
    fireEvent.click(screen.getByRole('checkbox'))
    fireEvent.click(screen.getByRole('button', { name: /approve this text/i }))
    expect(generate).toBeEnabled()
    fireEvent.click(generate)
    await waitFor(() => expect(distributeApi.runDistribute).toHaveBeenCalledTimes(1))
  })

  it('is enabled for text approved upstream, and re-locks when edited', async () => {
    distributeApi.getDistributeHistory.mockResolvedValue({ items: [], total: 0 })
    render(<DistributeTab initialText="Approved text" initialSlug="p" approvedText="Approved text" />)
    const generate = await screen.findByRole('button', { name: /generate platform bundle/i })
    expect(generate).toBeEnabled()
    fireEvent.change(screen.getByDisplayValue('Approved text'), { target: { value: 'Approved text, tweaked' } })
    expect(generate).toBeDisabled()
  })

  it('does not restore approval after whitespace changes or editing back', async () => {
    distributeApi.getDistributeHistory.mockResolvedValue({ items: [] })
    render(<DistributeTab initialText="Approved text" initialSlug="p" approvedText="Approved text" />)
    const generate = await screen.findByRole('button', { name: /generate platform bundle/i })
    fireEvent.change(screen.getByRole('textbox', { name: /^anchor post$/i }), { target: { value: 'Approved text ' } })
    expect(generate).toBeDisabled()
    fireEvent.change(screen.getByRole('textbox', { name: /^anchor post$/i }), { target: { value: 'Approved text' } })
    expect(generate).toBeDisabled()
  })

  it('uses canonical approval authority rather than a legacy matching string', async () => {
    distributeApi.getDistributeHistory.mockResolvedValue({ items: [] })
    render(<DistributeTab initialText="Text" initialSlug="p" approvedText="Text" approval={null} />)
    expect(await screen.findByRole('button', { name: /generate platform bundle/i })).toBeDisabled()
  })

  it('requires the canonical item and version and invalidates on identifier edits', async () => {
    distributeApi.getDistributeHistory.mockResolvedValue({ items: [] })
    const anchor = { itemId: 'item-a', version: 4, text: 'Same text', slug: 'a' }
    const onInvalidateApproval = vi.fn()
    const { rerender } = render(<DistributeTab anchorIdentity={anchor} approval={{ ...anchor, itemId: 'other' }} onInvalidateApproval={onInvalidateApproval} />)
    const generate = await screen.findByRole('button', { name: /generate platform bundle/i })
    expect(generate).toBeDisabled()
    rerender(<DistributeTab anchorIdentity={anchor} approval={anchor} onInvalidateApproval={onInvalidateApproval} />)
    expect(generate).toBeEnabled()
    fireEvent.change(screen.getByRole('textbox', { name: /post identifier/i }), { target: { value: 'b' } })
    expect(generate).toBeDisabled()
    expect(onInvalidateApproval).toHaveBeenCalledTimes(1)
  })

  it('associates delayed derivatives with the original anchor after editing', async () => {
    distributeApi.getDistributeHistory.mockResolvedValue({ items: [] })
    let resolve
    distributeApi.runDistribute.mockImplementation(() => new Promise(done => { resolve = done }))
    render(<DistributeTab initialText="Original anchor" initialSlug="original" approvedText="Original anchor" />)
    fireEvent.click(await screen.findByRole('button', { name: /generate platform bundle/i }))
    fireEvent.change(screen.getByRole('textbox', { name: /^anchor post$/i }), { target: { value: 'New working anchor' } })
    resolve({ linkedin: 'Original derivative' })
    expect(await screen.findByText('Original derivative')).toBeInTheDocument()
    expect(screen.getByText(/earlier anchor version/i)).toBeInTheDocument()
    expect(screen.getByText('Original anchor')).toBeInTheDocument()
    expect(screen.getByRole('textbox', { name: /^anchor post$/i })).toHaveValue('New working anchor')
  })
  it('does not label submitted custom input as the source of a replay', async () => {
    distributeApi.getDistributeHistory.mockResolvedValue({ items: [] })
    distributeApi.runDistribute.mockResolvedValue({ linkedin: 'Stored sample derivative', replayed: true })
    render(<DistributeTab initialText="My custom input" initialSlug="custom" approvedText="My custom input" />)
    fireEvent.click(await screen.findByRole('button', { name: /generate platform bundle/i }))
    expect(await screen.findByText('Stored sample derivative')).toBeInTheDocument()
    expect(screen.getByText(/submitted input \(not the source of this replay\)/i)).toBeInTheDocument()
    expect(screen.queryByText(/outputs for this anchor version/i)).not.toBeInTheDocument()
  })
  it('closes transient dialogs when inactive while retaining the working anchor', async () => {
    distributeApi.getDistributeHistory.mockResolvedValue({ items: [] })
    const { rerender } = render(<DistributeTab initialText="Working anchor" isActive />)
    fireEvent.click(await screen.findByRole('button', { name: /platforms \(/i }))
    expect(screen.getByRole('dialog', { name: /platform distribution formats/i })).toBeInTheDocument()
    rerender(<DistributeTab initialText="Working anchor" isActive={false} />)
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(screen.getByRole('textbox', { name: /^anchor post$/i })).toHaveValue('Working anchor')
  })
})
