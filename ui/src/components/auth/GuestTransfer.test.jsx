import React from 'react'
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { GuestTransfer } from './GuestTransfer'
import { retainGuestProof } from './guestProof'
import { getGuestTransfer, previewGuestTransfer, transferGuest } from '../../api/guests'

vi.mock('../../api/guests', () => ({ previewGuestTransfer: vi.fn(), transferGuest: vi.fn(), getGuestTransfer: vi.fn() }))
const session = { user: { id: 'creator' } }
const deferred = () => { let resolve, reject; const promise = new Promise((a, b) => { resolve = a; reject = b }); return { promise, resolve, reject } }
beforeEach(() => {
  vi.resetAllMocks(); sessionStorage.clear()
  retainGuestProof({ user: { id: 'guest', is_anonymous: true }, access_token: 'proof', expires_at: Date.now() / 1000 + 3600 })
  previewGuestTransfer.mockResolvedValue({ item_count: 1, source_fingerprint: 'sha256:one' })
})
afterEach(() => { sessionStorage.clear(); vi.useRealTimers() })
async function start() {
  render(<GuestTransfer session={session} />)
  await act(async () => {})
  expect(screen.getByText(/1 items/)).toBeInTheDocument()
  fireEvent.click(screen.getByRole('checkbox'))
  fireEvent.click(screen.getByRole('button', { name: /copy into my workspace/i }))
}

it('loads a bounded historical receipt only after success and explicit viewing', async () => {
  transferGuest.mockResolvedValue({ transfer_id: 'receipt-1', status: 'copied' })
  getGuestTransfer.mockResolvedValue({ transfer_id: 'receipt-1', editorial_approval: false,
    archive: { tables: { workflow_items: [{ title: 'Archived source', artifact_json: 'PRIVATE_BODY_NOT_RENDERED' }],
      workflow_versions: [{}, {}], workflow_approvals: [{}], workflow_operations: [{}], workflow_reviews: [] } },
    copy: { items: [{ source_item_id: 'source', target_item_id: 'target' }] } })
  await start()
  fireEvent.click(await screen.findByRole('button', { name: /view copied history/i }))
  expect(await screen.findByText(/2 archived versions/i)).toBeInTheDocument()
  expect(screen.getByText(/1 historical approvals/i)).toHaveTextContent(/grant no approval/i)
  expect(screen.getByText('Archived source')).toBeInTheDocument()
  expect(screen.queryByText(/PRIVATE_BODY_NOT_RENDERED/)).not.toBeInTheDocument()
  expect(getGuestTransfer).toHaveBeenCalledWith('receipt-1')
})

it('retains pending outcome UI when proof expires, then acknowledges committed success', async () => {
  const pending = deferred()
  transferGuest.mockReturnValue(pending.promise)
  vi.useFakeTimers()
  await start()
  await act(async () => { await vi.advanceTimersByTimeAsync(600001) })
  expect(screen.getByRole('button', { name: /copy into my workspace/i })).toBeDisabled()
  expect(sessionStorage.length).toBe(0)
  await act(async () => { pending.resolve({ transfer_id: 'receipt-1', status: 'copied' }); await pending.promise })
  expect(screen.getByRole('status')).toHaveTextContent(/copied/i)
})

it('shows an honest unknown outcome after proof expires during a failed response', async () => {
  const pending = deferred()
  transferGuest.mockReturnValue(pending.promise)
  vi.useFakeTimers()
  await start()
  await act(async () => { await vi.advanceTimersByTimeAsync(600001) })
  await act(async () => { pending.reject(new Error('Connection lost')); await pending.promise.catch(() => {}) })
  expect(screen.getByRole('alert')).toHaveTextContent(/outcome could not be confirmed.*saved work/i)
  expect(screen.queryByRole('button', { name: /retry guest copy/i })).not.toBeInTheDocument()
})

it('never renders stale or denied receipt data after the account view unmounts', async () => {
  transferGuest.mockResolvedValue({ transfer_id: 'receipt-1', status: 'copied' })
  const pending = deferred()
  getGuestTransfer.mockReturnValue(pending.promise)
  const view = render(<GuestTransfer session={session} />)
  await screen.findByText(/1 items/)
  fireEvent.click(screen.getByRole('checkbox'))
  fireEvent.click(screen.getByRole('button', { name: /copy into my workspace/i }))
  fireEvent.click(await screen.findByRole('button', { name: /view copied history/i }))
  view.unmount()
  await act(async () => { pending.resolve({ archive: { tables: { workflow_items: [{ title: 'Other account history' }] } } }); await pending.promise })
  expect(screen.queryByText('Other account history')).not.toBeInTheDocument()
})

it('does not show denied or mismatched receipt data and allows a safe retry', async () => {
  transferGuest.mockResolvedValue({ transfer_id: 'receipt-1', status: 'copied' })
  getGuestTransfer.mockRejectedValueOnce({ status: 404, message: 'not found' })
    .mockResolvedValueOnce({ transfer_id: 'wrong-receipt', editorial_approval: false,
      archive: { tables: { workflow_items: [{ title: 'Wrong receipt title' }] } } })
  await start()
  fireEvent.click(await screen.findByRole('button', { name: /view copied history/i }))
  expect(await screen.findByRole('alert')).toHaveTextContent(/could not load archived history/i)
  fireEvent.click(screen.getByRole('button', { name: /view copied history/i }))
  await waitFor(() => expect(getGuestTransfer).toHaveBeenCalledTimes(2))
  expect(screen.queryByText('Wrong receipt title')).not.toBeInTheDocument()
})
