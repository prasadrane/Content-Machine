import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from './client'
import { setAccessTokenProvider } from './session'
import { bootstrapGuest, previewGuestTransfer, transferGuest, getGuestTransfer } from './guests'

afterEach(() => { vi.unstubAllGlobals(); setAccessTokenProvider(null) })

it('uses distinct verified destination and source proofs with explicit copy consent', async () => {
  const request = vi.fn().mockResolvedValue({ ok: true, json: async () => ({}) })
  vi.stubGlobal('fetch', request)
  setAccessTokenProvider(async () => 'creator-proof')
  await previewGuestTransfer('guest-proof')
  await transferGuest('guest-proof', 'sha256:abc', 'key-1')
  await getGuestTransfer('receipt/one')
  expect(request.mock.calls[0]).toEqual(['/api/workflow/guest/transfer/preview', expect.objectContaining({
    method: 'POST', body: '{}', headers: { 'Content-Type': 'application/json', Authorization: 'Bearer creator-proof', 'X-Guest-Authorization': 'Bearer guest-proof' },
  })])
  expect(request.mock.calls[1]).toEqual(['/api/workflow/guest/transfer', expect.objectContaining({
    method: 'POST', body: JSON.stringify({ consent: true, source_fingerprint: 'sha256:abc' }),
    headers: expect.objectContaining({ 'Idempotency-Key': 'key-1', 'X-Guest-Authorization': 'Bearer guest-proof' }),
  })])
  expect(request.mock.calls[2][0]).toBe('/api/workflow/guest/transfers/receipt%2Fone')
})

describe('guest bootstrap client', () => {
  it('sends the current session token and no browser ownership claims', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ examples: [] }) })
    vi.stubGlobal('fetch', fetchMock)
    setAccessTokenProvider(async () => 'current-session')
    expect(await bootstrapGuest()).toEqual({ examples: [] })
    expect(fetchMock).toHaveBeenCalledWith('/api/workflow/guest/bootstrap', expect.objectContaining({
      method: 'POST', body: '{}', headers: { 'Content-Type': 'application/json', Authorization: 'Bearer current-session' },
    }))
  })

  it('preserves typed unavailable errors for the caller', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 503,
      json: async () => ({ detail: 'Guest setup unavailable', code: 'guest_auth_unavailable' }) }))
    const error = await bootstrapGuest().catch(failure => failure)
    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({ status: 503, message: 'Guest setup unavailable',
      body: { code: 'guest_auth_unavailable' } })
  })

  it('resolves a fresh token for retries and sends no cached token after sign-out', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ examples: [] }) })
    vi.stubGlobal('fetch', fetchMock)
    const tokens = vi.fn().mockResolvedValueOnce('initial-session').mockResolvedValueOnce('refreshed-session')
      .mockResolvedValueOnce(null)
    setAccessTokenProvider(tokens)
    await bootstrapGuest()
    await bootstrapGuest()
    await bootstrapGuest()
    expect(tokens).toHaveBeenCalledTimes(3)
    expect(fetchMock.mock.calls[0][1].headers.Authorization).toBe('Bearer initial-session')
    expect(fetchMock.mock.calls[1][1].headers.Authorization).toBe('Bearer refreshed-session')
    expect(fetchMock.mock.calls[2][1].headers).toEqual({ 'Content-Type': 'application/json' })
    expect(fetchMock.mock.calls.every(([, options]) => options.body === '{}')).toBe(true)
  })

  it('does not send a bootstrap request when session refresh fails', async () => {
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)
    const expired = new Error('Session expired')
    setAccessTokenProvider(async () => { throw expired })
    await expect(bootstrapGuest()).rejects.toBe(expired)
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('keeps concurrent token resolution independent and forwards only each call\'s own result', async () => {
    const pending = []
    const fetchMock = vi.fn().mockImplementation(async (_url, options) => ({ ok: true,
      json: async () => ({ examples: [], sessionUsed: options.headers.Authorization }),
    }))
    vi.stubGlobal('fetch', fetchMock)
    setAccessTokenProvider(() => new Promise(resolve => pending.push(resolve)))
    const first = bootstrapGuest()
    const second = bootstrapGuest()
    expect(fetchMock).not.toHaveBeenCalled()
    expect(pending).toHaveLength(2)
    pending[1]('second-session')
    await expect(second).resolves.toMatchObject({ sessionUsed: 'Bearer second-session' })
    expect(fetchMock).toHaveBeenCalledTimes(1)
    pending[0]('first-session')
    await expect(first).resolves.toMatchObject({ sessionUsed: 'Bearer first-session' })
    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(fetchMock.mock.calls.every(([url, options]) =>
      url === '/api/workflow/guest/bootstrap' && options.body === '{}')).toBe(true)
  })

  it('lets an explicit retry use a refreshed session after an unavailable response', async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce({ ok: false, status: 503,
      json: async () => ({ detail: 'Guest storage unavailable', code: 'workflow_storage_misconfigured' }),
    }).mockResolvedValueOnce({ ok: true, json: async () => ({ examples: [{ label: 'Demo example' }] }) })
    vi.stubGlobal('fetch', fetchMock)
    setAccessTokenProvider(vi.fn().mockResolvedValueOnce('before-refresh').mockResolvedValueOnce('after-refresh'))
    await expect(bootstrapGuest()).rejects.toMatchObject({ status: 503,
      body: { code: 'workflow_storage_misconfigured' } })
    expect(fetchMock).toHaveBeenCalledTimes(1)
    await expect(bootstrapGuest()).resolves.toEqual({ examples: [{ label: 'Demo example' }] })
    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(fetchMock.mock.calls[1][1].headers.Authorization).toBe('Bearer after-refresh')
  })
})
