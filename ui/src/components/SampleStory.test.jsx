import { render, screen, fireEvent } from '@testing-library/react'
import { vi } from 'vitest'
import SampleStory from './SampleStory'
import { getCouncilHistory } from '../api/council'
import { getDistributeHistory } from '../api/distribute'

vi.mock('../api/council', () => ({ getCouncilHistory: vi.fn() }))
vi.mock('../api/distribute', () => ({ getDistributeHistory: vi.fn() }))

test('distinguishes illustrative review from stored derivative anchor without granting approval', async () => {
  getCouncilHistory.mockResolvedValue({ best: { draft: 'Long Council sample draft', score: 9.3 } })
  getDistributeHistory.mockResolvedValue({ items: [{ slug: 'demo-cache-stampede', anchor_text: 'Short original anchor', bundle: { linkedin: 'Stored LinkedIn output', x_thread: 'Stored thread' } }] })
  const onClose = vi.fn()
  render(<SampleStory onClose={onClose} />)
  expect(await screen.findByText('Long Council sample draft')).toBeInTheDocument()
  expect(screen.getByText('Short original anchor')).toBeInTheDocument()
  expect(screen.getByText(/not approved by you/i)).toBeInTheDocument()
  expect(screen.getByText(/not the exact Council draft/i)).toBeInTheDocument()
  expect(screen.getByText('Stored LinkedIn output')).toBeInTheDocument()
  expect(screen.getByText('Stored thread')).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: /^approve/i })).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: /return to workspace/i }))
  expect(onClose).toHaveBeenCalledOnce()
})

test('reports missing sample material and load failures without inventing outputs', async () => {
  getCouncilHistory.mockRejectedValue(new Error('Sample unavailable'))
  getDistributeHistory.mockResolvedValue({ items: [] })
  render(<SampleStory onClose={vi.fn()} />)
  expect(await screen.findByRole('alert')).toHaveTextContent('Sample unavailable')
  expect(screen.queryByText('Stored LinkedIn output')).not.toBeInTheDocument()
})
