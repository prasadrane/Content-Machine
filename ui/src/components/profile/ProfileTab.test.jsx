import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import ProfileTab from './ProfileTab'
import * as profileApi from '../../api/profile'

vi.mock('../../api/profile', () => ({
  getProfile: vi.fn(),
  saveProfile: vi.fn(),
}))

describe('ProfileTab', () => {
  it('exposes named focus and domain fields without changing save behavior', async () => {
    profileApi.getProfile.mockResolvedValue({ current_focus: 'Original focus', technical_domains: [] })
    profileApi.saveProfile.mockResolvedValue({ current_focus: 'New focus', technical_domains: ['Systems'] })
    render(<ProfileTab />)
    const focus = await screen.findByRole('textbox', { name: /current operational reality/i })
    await waitFor(() => expect(focus).toHaveValue('Original focus'))
    fireEvent.change(focus, { target: { value: 'New focus' } })
    const domain = screen.getByRole('textbox', { name: /add technical domain/i })
    fireEvent.change(domain, { target: { value: 'Systems' } })
    fireEvent.keyDown(domain, { key: 'Enter' })
    fireEvent.click(screen.getByRole('button', { name: /save.*sync voice profile/i }))
    await waitFor(() => expect(profileApi.saveProfile).toHaveBeenCalledWith({ current_focus: 'New focus', technical_domains: ['Systems'] }))
  })
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
