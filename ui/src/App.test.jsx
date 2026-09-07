import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from './App'
import * as healthApi from './api/health'
import * as profileApi from './api/profile'

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

describe('App shell', () => {
  it('renders all 7 nav buttons from registry', () => {
    render(<App />)
    for (const label of ['Oracle', 'Council', 'Distribute', 'Lessons', 'Audio', 'Comments', 'Profile']) {
      expect(screen.getByRole('button', { name: new RegExp(label, 'i') })).toBeInTheDocument()
    }
  })
  it('switches tabs on nav click', async () => {
    render(<App />)
    await userEvent.click(screen.getByRole('button', { name: /profile/i }))
    expect(await screen.findByText(/Author Voice & Profile/i)).toBeInTheDocument()
  })
})
