import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from './App'
import * as healthApi from './api/health'
import * as profileApi from './api/profile'

vi.mock('./components/workflow/WorkflowTab', () => ({
  default: () => <textarea aria-label="Workflow draft" />,
}))

vi.mock('./api/health', () => ({ getHealth: vi.fn().mockResolvedValue({ status: 'ok' }) }))
vi.mock('./api/oracle', () => ({
  runOracleScan: vi.fn(),
  getOracleHistory: vi.fn().mockResolvedValue({ items: [], total: 0, topics: [] }),
}))
vi.mock('./api/linkedin', () => ({
  getLinkedInStatus: vi.fn().mockResolvedValue({ connected: false }),
  syncLinkedIn: vi.fn(),
}))
vi.mock('./api/profile', () => ({
  getProfile: vi.fn().mockResolvedValue({
    bio: '',
    role: '',
    company: '',
    core_themes: [],
    custom_invariants: [],
    negative_constraints: [],
  }),
  saveProfile: vi.fn().mockResolvedValue({ success: true }),
}))
vi.mock('./api/settings', () => ({
  getSettings: vi.fn().mockResolvedValue({ profile: { name: '', role: '', bio: '', revision: 0 }, sources: [] }),
  saveProfile: vi.fn(), createSource: vi.fn(), updateSource: vi.fn(), createRequestId: vi.fn(),
}))
vi.mock('./api/preferences', () => ({ getPreferences: vi.fn().mockResolvedValue({ preferences: [] }) }))

describe('App shell', () => {
  it('renders the workflow, lessons and settings navigation', () => {
    render(<App />)
    for (const label of ['Workflow', 'Lessons', 'Settings']) {
      expect(screen.getByRole('button', { name: new RegExp(label, 'i') })).toBeInTheDocument()
    }
    expect(screen.queryByRole('button', { name: /^comments$/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /^audio$/i })).not.toBeInTheDocument()
  })
  it('switches tabs on nav click', async () => {
    render(<App />)
    await userEvent.click(screen.getByRole('button', { name: /settings/i }))
    expect(await screen.findByRole('heading', { name: 'Settings' })).toBeInTheDocument()
  })
  it('preserves an unfinished draft when navigating away and back', async () => {
    render(<App />)
    await userEvent.type(screen.getByRole('textbox', { name: /workflow draft/i }), 'An unfinished engineering story')
    await userEvent.click(screen.getByRole('button', { name: /^settings$/i }))
    await userEvent.click(screen.getByRole('button', { name: /^workflow$/i }))
    expect(screen.getByRole('textbox', { name: /workflow draft/i })).toHaveValue('An unfinished engineering story')
  })
  it('opens the governed writing preferences page', async () => {
    render(<App />)
    await userEvent.click(screen.getByRole('button', { name: /^lessons$/i }))
    expect(await screen.findByRole('heading', { name: 'Writing preferences' })).toBeInTheDocument()
  })
})
