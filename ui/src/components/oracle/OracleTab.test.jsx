import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent, act } from '@testing-library/react'
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
  beforeEach(() => vi.clearAllMocks())
  const setupScan = async () => {
    linkedinApi.getLinkedInStatus.mockResolvedValue({ connected: false })
    oracleApi.getOracleHistory.mockResolvedValue({ items: [], total: 0, topics: [] })
    oracleApi.runOracleScan.mockResolvedValue(undefined)
    await act(async () => { render(<OracleTab onSendToCouncil={vi.fn()} onSendToCouncilWithDraft={vi.fn()} />) })
    fireEvent.click(screen.getByText(/edit sources and limits/i))
  }

  it('shows actual line breaks in the default feeds', async () => {
    await setupScan()
    expect(screen.getByRole('textbox')).toHaveValue('https://dev.to/feed\nhttps://news.ycombinator.com/rss')
  })

  it('counts and submits pasted multiline feeds separately', async () => {
    await setupScan()
    fireEvent.change(screen.getByRole('textbox'), { target: { value: ' https://one.example/rss\r\n\nhttps://two.example/feed ' } })
    expect(screen.getByText('2 sources configured')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Scan & Score Candidates' }))
    await waitFor(() => expect(oracleApi.runOracleScan).toHaveBeenCalledWith(
      expect.objectContaining({ rss_urls: ['https://one.example/rss', 'https://two.example/feed'] }), expect.any(Function),
    ))
  })

  it('supports existing literal separators and appends presets as separate feeds', async () => {
    await setupScan()
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'https://one.example/rss\\nhttps://two.example/feed' } })
    fireEvent.click(screen.getByRole('button', { name: /r\/LocalLLaMA/i }))
    fireEvent.click(screen.getByRole('button', { name: 'Scan & Score Candidates' }))
    await waitFor(() => expect(oracleApi.runOracleScan).toHaveBeenCalledWith(
      expect.objectContaining({ rss_urls: ['https://one.example/rss', 'https://two.example/feed', 'https://www.reddit.com/r/LocalLLaMA/top/.rss?t=week'] }), expect.any(Function),
    ))
  })

  it('blocks invalid feed URLs with an actionable error before scanning', async () => {
    await setupScan()
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'https://one.example/rss\nnot-a-url' } })
    fireEvent.click(screen.getByRole('button', { name: 'Scan & Score Candidates' }))
    expect(oracleApi.runOracleScan).not.toHaveBeenCalled()
    expect(screen.getByRole('alert')).toHaveTextContent('RSS feed 2: enter a valid http or https URL.')
    expect(screen.getByLabelText('RSS / Atom Feeds')).toHaveAttribute('aria-invalid', 'true')
  })

  it('validates a GitHub repository without clearing the inputs', async () => {
    await setupScan()
    fireEvent.click(screen.getByRole('button', { name: /^GitHub\s*0$/i }))
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'https://github.com/facebook/react' } })
    fireEvent.click(screen.getByRole('button', { name: 'Scan & Score Candidates' }))
    expect(oracleApi.runOracleScan).not.toHaveBeenCalled()
    expect(screen.getByRole('alert')).toHaveTextContent('GitHub repository 1: use owner/repo, for example facebook/react.')
    expect(screen.getByRole('textbox')).toHaveValue('https://github.com/facebook/react')
  })

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
