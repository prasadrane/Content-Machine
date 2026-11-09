import React from 'react'
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { AuthGate } from './AuthGate'
import { notifyUnauthorized } from '../../api/session'

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
    // Identity 'two' is not a guest and nothing signals unsaved work: no confirmation.
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

  it('drops a per-item deep link when the session ends', async () => {
    window.location.hash = '#/workflow/items/abc/draft_review'
    const service = fakeService({ user: { id: 'one' }, access_token: 'old', expires_at: 1 })
    render(<AuthGate service={service}><p>Private content</p></AuthGate>)
    await screen.findByRole('alert')
    expect(window.location.hash).toBe('#/workflow')
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

  it('confirms guest sign-out with an accessible dialog and offers Copy with Google first', async () => {
    const service = fakeService({ user: { id: 'g', is_anonymous: true }, access_token: 'a' })
    render(<AuthGate service={service}><p>Private content</p></AuthGate>)
    await screen.findByText('Private content')
    const trigger = screen.getByRole('button', { name: /^sign out$/i })
    fireEvent.click(trigger)
    const dialog = await screen.findByRole('alertdialog', { name: /sign out/i })
    expect(dialog).toHaveTextContent(/unreachable/i)
    expect(service.signOut).not.toHaveBeenCalled()
    expect(screen.getByText('Private content')).toBeInTheDocument()
    expect(dialog.querySelector('button')).toHaveTextContent(/copy guest work with google/i)
    expect(dialog).toContainElement(document.activeElement)
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument()
    expect(trigger).toHaveFocus()
    expect(service.signOut).not.toHaveBeenCalled()
    fireEvent.click(trigger)
    fireEvent.click(await screen.findByRole('button', { name: /^cancel$/i }))
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument()
    fireEvent.click(trigger)
    fireEvent.click(await screen.findByRole('button', { name: /sign out anyway/i }))
    await waitFor(() => expect(service.signOut).toHaveBeenCalledTimes(1))
  })

  it('confirms sign-out for a signed-in user only when unsaved work is signalled', async () => {
    const service = fakeService({ user: { id: 'u' }, access_token: 'a' })
    function Dirty() {
      React.useEffect(() => {
        const warn = event => event.preventDefault()
        window.addEventListener('beforeunload', warn)
        return () => window.removeEventListener('beforeunload', warn)
      }, [])
      return <p>Dirty workspace</p>
    }
    render(<AuthGate service={service}><Dirty /></AuthGate>)
    await screen.findByText('Dirty workspace')
    fireEvent.click(screen.getByRole('button', { name: /^sign out$/i }))
    expect(await screen.findByRole('alertdialog')).toHaveTextContent(/unsaved/i)
    expect(service.signOut).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: /sign out anyway/i }))
    await waitFor(() => expect(service.signOut).toHaveBeenCalled())
  })

  it('returns to sign-in when the API reports an unrecoverable 401', async () => {
    const service = fakeService({ user: { id: 'u' }, access_token: 'a' })
    render(<AuthGate service={service}><p>Private content</p></AuthGate>)
    await screen.findByText('Private content')
    act(() => notifyUnauthorized())
    expect(await screen.findByRole('alert')).toHaveTextContent(/sign in again/i)
    expect(screen.queryByText('Private content')).not.toBeInTheDocument()
  })
})
