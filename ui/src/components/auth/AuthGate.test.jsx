import React from 'react'
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { AuthGate } from './AuthGate'

vi.mock('../../api/guests', () => ({ bootstrapGuest: vi.fn().mockResolvedValue({ examples: [] }),
  previewGuestTransfer: vi.fn(), transferGuest: vi.fn() }))

function fakeService(session = null) {
  let callback
  return {
    mode: 'hosted',
    getSession: vi.fn().mockResolvedValue(session),
    onAuthStateChange: vi.fn(fn => { callback = fn; return () => {} }),
    signInWithGoogle: vi.fn().mockResolvedValue(),
    signInAsGuest: vi.fn().mockResolvedValue(),
    signOut: vi.fn().mockResolvedValue(),
    emit: (event, value) => callback(event, value),
  }
}

describe('AuthGate', () => {
  it('keeps local mode available and blocks hosted mode with configuration error', () => {
    const { rerender } = render(<AuthGate service={{ mode: 'local' }}><p>Workspace</p></AuthGate>)
    expect(screen.getByText('Workspace')).toBeInTheDocument()
    rerender(<AuthGate error="Hosted configuration missing" />)
    expect(screen.queryByText('Workspace')).not.toBeInTheDocument()
    expect(screen.getByRole('alert')).toHaveTextContent('Hosted configuration missing')
  })

  it('offers explicit Google and guest sign in', async () => {
    const service = fakeService()
    render(<AuthGate service={service}><p>Private content</p></AuthGate>)
    fireEvent.click(await screen.findByRole('button', { name: /continue as guest/i }))
    expect(service.signInAsGuest).toHaveBeenCalled()
    expect(screen.queryByText('Private content')).not.toBeInTheDocument()
  })

  it('preserves unsaved work on token refresh and clears it when identity changes or signs out', async () => {
    const service = fakeService({ user: { id: 'one', is_anonymous: true }, access_token: 'a' })
    function PrivateView() { return <input aria-label="draft" defaultValue="original" /> }
    render(<AuthGate service={service}><PrivateView /></AuthGate>)
    const input = await screen.findByLabelText('draft')
    fireEvent.change(input, { target: { value: 'secret' } })
    act(() => service.emit('TOKEN_REFRESHED', { user: { id: 'one', is_anonymous: true }, access_token: 'b' }))
    expect(screen.getByLabelText('draft')).toHaveValue('secret')
    act(() => service.emit('SIGNED_IN', { user: { id: 'two' }, access_token: 'c' }))
    expect(screen.getByLabelText('draft')).toHaveValue('original')
    fireEvent.click(screen.getByRole('button', { name: /sign out/i }))
    await waitFor(() => expect(screen.queryByLabelText('draft')).not.toBeInTheDocument())
    expect(service.signOut).toHaveBeenCalled()
  })

  it('does not show the workspace for an expired session', async () => {
    const service = fakeService({ user: { id: 'one' }, access_token: 'old', expires_at: 1 })
    render(<AuthGate service={service}><p>Private content</p></AuthGate>)
    expect(await screen.findByRole('alert')).toHaveTextContent(/expired/i)
    expect(screen.queryByText('Private content')).not.toBeInTheDocument()
  })

  it('keeps the workspace hidden and offers a retry when sign-out fails', async () => {
    const service = fakeService({ user: { id: 'one' }, access_token: 'a' })
    service.signOut.mockRejectedValueOnce(new Error('Network error')).mockResolvedValueOnce()
    render(<AuthGate service={service}><p>Private content</p></AuthGate>)
    await screen.findByText('Private content')
    fireEvent.click(screen.getByRole('button', { name: /sign out/i }))
    expect(await screen.findByRole('alert')).toHaveTextContent(/still be signed in/i)
    expect(screen.queryByText('Private content')).not.toBeInTheDocument()
    act(() => service.emit('TOKEN_REFRESHED', { user: { id: 'one' }, access_token: 'b' }))
    expect(screen.queryByText('Private content')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /retry sign out/i }))
    await waitFor(() => expect(service.signOut).toHaveBeenCalledTimes(2))
    expect(await screen.findByRole('button', { name: /continue as guest/i })).toBeInTheDocument()
    expect(screen.queryByText('Private content')).not.toBeInTheDocument()
  })
})
