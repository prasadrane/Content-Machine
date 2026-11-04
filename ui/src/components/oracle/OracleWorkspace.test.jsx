import { beforeEach, expect, it, vi } from 'vitest'
import { act, fireEvent, render, screen } from '@testing-library/react'
import OracleTab from './OracleTab'
import { getOracleHistory } from '../../api/oracle'

vi.mock('../../api/oracle', () => ({ getOracleHistory: vi.fn(), runOracleScan: vi.fn() }))
vi.mock('../../api/linkedin', () => ({ getLinkedInStatus: vi.fn().mockResolvedValue({ connected: false }), syncLinkedIn: vi.fn() }))

beforeEach(() => { vi.clearAllMocks(); getOracleHistory.mockResolvedValue({ items: [], total: 0, topics: [] }) })

it('starts with available archived signals instead of empty scanner configuration', async () => {
  getOracleHistory.mockResolvedValue({ items: [{ title: 'Existing engineering signal', source: 'RSS', verdict: 'pass', score: 9 }], total: 1, topics: [] })
  await act(async () => { render(<OracleTab />) })
  expect(screen.getByText('Existing engineering signal')).toBeVisible()
  expect(screen.queryByRole('button', { name: 'Scan & Score Candidates' })).not.toBeInTheDocument()
})

it('keeps scanning available while source settings are collapsed', async () => {
  await act(async () => { render(<OracleTab />) })
  expect(screen.getByRole('button', { name: 'Scan & Score Candidates' })).toBeVisible()
  const disclosure = screen.getByText(/edit sources and limits/i)
  expect(disclosure.closest('details')).not.toHaveAttribute('open')
  fireEvent.click(disclosure)
  expect(screen.getByLabelText('RSS / Atom Feeds')).toBeVisible()
})

it('does not replace the scanner after the author explicitly chooses to scan', async () => {
  let resolveHistory
  const pending = new Promise(resolve => { resolveHistory = resolve })
  getOracleHistory.mockReturnValue(pending)
  render(<OracleTab />)
  fireEvent.click(screen.getByRole('button', { name: 'Scan & Score Candidates' }))
  await act(async () => { resolveHistory({ items: [{ title: 'Saved signal', source: 'RSS', score: 9 }], total: 1, topics: [] }) })
  expect(screen.getByRole('button', { name: 'Scan & Score Candidates' })).toBeVisible()
})

it('clears only the session credential when the retained panel becomes inactive', async () => {
  const { rerender } = render(<OracleTab isActive />)
  await act(async () => {})
  fireEvent.click(screen.getByText(/edit sources and limits/i))
  fireEvent.click(screen.getByRole('button', { name: /^LinkedIn\s*0$/i }))
  const credential = screen.getByPlaceholderText(/Paste li_at cookie/i)
  fireEvent.change(credential, { target: { value: 'private-session-cookie' } })
  await act(async () => { rerender(<OracleTab isActive={false} />) })
  await act(async () => { rerender(<OracleTab isActive />) })
  expect(credential).toHaveValue('')
})
