import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import ProfileTab from './ProfileTab'
import * as profileApi from '../../api/profile'

vi.mock('../../api/profile', () => ({
  getProfile: vi.fn(),
  saveProfile: vi.fn(),
}))

describe('ProfileTab', () => {
  it('loads and renders profile on mount', async () => {
    profileApi.getProfile.mockResolvedValue({
      current_focus: 'Modularization',
      technical_domains: ['React', 'Python'],
    })
    render(<ProfileTab />)
    await waitFor(() => expect(profileApi.getProfile).toHaveBeenCalledTimes(1))
    expect(await screen.findByText(/modularization/i)).toBeInTheDocument()
  })
  it('renders core voice invariants section', async () => {
    profileApi.getProfile.mockResolvedValue({ current_focus: '', technical_domains: [] })
    render(<ProfileTab />)
    expect(await screen.findByText(/zero company attribution/i)).toBeInTheDocument()
  })
})
