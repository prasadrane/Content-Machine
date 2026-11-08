import React from 'react'
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { AuthGate } from './AuthGate'
import { bootstrapGuest, previewGuestTransfer, transferGuest } from '../../api/guests'

vi.mock('../../api/guests', () => ({ bootstrapGuest: vi.fn(), previewGuestTransfer: vi.fn(), transferGuest: vi.fn() }))
let emit
function service(session) {
  return { mode: 'hosted', getSession: vi.fn().mockResolvedValue(session),
    onAuthStateChange: fn => { emit = fn; return () => {} },
    signInWithGoogle: vi.fn().mockResolvedValue(), signOut: vi.fn().mockResolvedValue() }
}
const guest = () => ({ user: { id: 'guest', is_anonymous: true }, access_token: 'guest-proof', expires_at: Date.now() / 1000 + 3600 })
beforeEach(() => { vi.resetAllMocks(); sessionStorage.clear(); bootstrapGuest.mockResolvedValue({ examples: [] }) })
afterEach(() => sessionStorage.clear())

it('blocks guest workspace until bootstrap succeeds and supports explicit retry', async () => {
  bootstrapGuest.mockRejectedValueOnce(new Error('Unavailable')).mockResolvedValueOnce({ examples: [] })
  render(<AuthGate service={service(guest())}><p>Workspace</p></AuthGate>)
  expect(await screen.findByRole('button', { name: /retry guest setup/i })).toBeInTheDocument()
  expect(screen.queryByText('Workspace')).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: /retry guest setup/i }))
  expect(await screen.findByText('Workspace')).toBeInTheDocument()
  expect(bootstrapGuest).toHaveBeenCalledTimes(2)
})

it('does not copy during OAuth and requires fresh preview plus explicit consent', async () => {
  const auth = service(guest())
  previewGuestTransfer.mockResolvedValue({ source_fingerprint: 'sha256:one', item_count: 2 })
  transferGuest.mockResolvedValue({ status: 'copied', requires_new_approval: true, items: [] })
  const copied = vi.fn()
  window.addEventListener('cm:guest-work-copied', copied, { once: true })
  render(<AuthGate service={auth}><p>Workspace</p><input aria-label="workspace-instance" defaultValue="fresh" /></AuthGate>)
  await screen.findByText('Workspace')
  fireEvent.click(screen.getByRole('button', { name: /copy guest work.*google/i }))
  await waitFor(() => expect(auth.signInWithGoogle).toHaveBeenCalledTimes(1))
  expect(transferGuest).not.toHaveBeenCalled()
  act(() => emit('SIGNED_IN', { user: { id: 'creator' }, access_token: 'creator-proof' }))
  expect(await screen.findByText(/2 items/)).toBeInTheDocument()
  fireEvent.change(screen.getByLabelText('workspace-instance'), { target: { value: 'before-copy' } })
  const copy = screen.getByRole('button', { name: /copy into my workspace/i })
  expect(copy).toBeDisabled()
  fireEvent.click(screen.getByRole('checkbox', { name: /unapproved copies/i }))
  fireEvent.click(copy)
  await waitFor(() => expect(transferGuest).toHaveBeenCalledWith('guest-proof', 'sha256:one', expect.any(String)))
  expect(await screen.findByRole('status')).toHaveTextContent(/copied.*new approval/i)
  expect(sessionStorage.length).toBe(0)
  expect(screen.getByLabelText('workspace-instance')).toHaveValue('before-copy')
  expect(copied).toHaveBeenCalledTimes(1)
})

it('clears the handoff when Google sign-in fails and never sends a copy', async () => {
  const auth = service(guest())
  auth.signInWithGoogle.mockRejectedValueOnce(new Error('Google unavailable'))
  render(<AuthGate service={auth}><p>Workspace</p></AuthGate>)
  await screen.findByText('Workspace')
  fireEvent.click(screen.getByRole('button', { name: /copy guest work.*google/i }))
  expect(await screen.findByRole('alert')).toHaveTextContent(/Google unavailable/)
  expect(sessionStorage.length).toBe(0)
  expect(transferGuest).not.toHaveBeenCalled()
})

it('clears retained proof when sign-out is requested', async () => {
  const auth = service(guest())
  render(<AuthGate service={auth}><p>Workspace</p></AuthGate>)
  await screen.findByText('Workspace')
  fireEvent.click(screen.getByRole('button', { name: /copy guest work.*google/i }))
  await waitFor(() => expect(sessionStorage.length).toBe(1))
  fireEvent.click(screen.getByRole('button', { name: /^sign out$/i }))
  expect(sessionStorage.length).toBe(0)
})
