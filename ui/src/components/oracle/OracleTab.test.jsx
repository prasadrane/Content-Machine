import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import OracleTab from './OracleTab'
import * as oracleApi from '../../api/oracle'
import * as linkedinApi from '../../api/linkedin'

vi.mock('../../api/oracle', () => ({
  runOracleScan: vi.fn(),
  getOracleHistory: vi.fn(),
}))
vi.mock('../../api/linkedin', () => ({
  getLinkedInStatus: vi.fn(),
  syncLinkedIn: vi.fn(),
}))

describe('OracleTab', () => {
  it('loads linkedin status + archive on mount', async () => {
    linkedinApi.getLinkedInStatus.mockResolvedValue({ connected: false })
    oracleApi.getOracleHistory.mockResolvedValue({ items: [], total: 0, topics: [] })
    render(<OracleTab onSendToCouncil={vi.fn()} onSendToCouncilWithDraft={vi.fn()} />)
    await waitFor(() => expect(linkedinApi.getLinkedInStatus).toHaveBeenCalledTimes(1))
    expect(oracleApi.getOracleHistory).toHaveBeenCalled()
  })
  it('renders source cockpit sub-tabs', async () => {
    linkedinApi.getLinkedInStatus.mockResolvedValue({ connected: false })
    render(<OracleTab onSendToCouncil={vi.fn()} onSendToCouncilWithDraft={vi.fn()} />)
    expect(await screen.findByText('RSS Feeds')).toBeInTheDocument()
  })
  it('does not leak debug global', () => {
    expect(window.__CM_SET_CANDIDATES__).toBeUndefined()
  })
})
