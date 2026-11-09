import { describe, it, expect, vi, afterEach } from 'vitest'
import { fetchJson, ApiError } from './client'
import { getHealth } from './health'
import { onUnauthorized, setAccessTokenProvider, setSessionRefresher } from './session'

afterEach(() => vi.unstubAllGlobals())

function stubFetch(res) { vi.stubGlobal('fetch', vi.fn(async () => res)) }

describe('fetchJson', () => {
  it('returns parsed json on ok response', async () => {
    stubFetch({ ok: true, status: 200, json: async () => ({ status: 'ok' }) })
    await expect(fetchJson('/api/health')).resolves.toEqual({ status: 'ok' })
  })
  it('sends JSON content-type only with body', async () => {
    stubFetch({ ok: true, status: 200, json: async () => ({}) })
    await fetchJson('/api/x', { method: 'POST', body: { a: 1 } })
    const call = fetch.mock.calls[0]
    expect(call[1].headers['Content-Type']).toBe('application/json')
    expect(call[1].body).toBe('{"a":1}')
    await fetchJson('/api/x')
    expect(fetch.mock.calls[1][1].headers).toBeUndefined()
  })
  it('throws ApiError with status and detail on !ok', async () => {
    stubFetch({ ok: false, status: 500, json: async () => ({ detail: 'boom' }) })
    const err = await fetchJson('/api/x').catch((e) => e)
    expect(err).toBeInstanceOf(ApiError)
    expect(err.status).toBe(500)
    expect(err.message).toBe('boom')
  })
})

describe('getHealth', () => {
  it('GETs /api/health', async () => {
    stubFetch({ ok: true, status: 200, json: async () => ({ status: 'ok' }) })
    await expect(getHealth()).resolves.toEqual({ status: 'ok' })
    expect(fetch.mock.calls[0][0]).toBe('/api/health')
  })
})

describe('fetchJson hosted 401 handling', () => {
  afterEach(() => { setAccessTokenProvider(null); setSessionRefresher(null) })
  const reply = (status, json = {}) => ({ ok: status < 400, status, json: async () => json })

  it('refreshes once and retries a workflow request with the new token', async () => {
    let token = 'old'
    setAccessTokenProvider(async () => token)
    const refresh = vi.fn(async () => { token = 'new'; return { access_token: 'new' } })
    setSessionRefresher(refresh)
    vi.stubGlobal('fetch', vi.fn()
      .mockResolvedValueOnce(reply(401, { detail: 'expired' })).mockResolvedValueOnce(reply(200, { ok: 1 })))
    await expect(fetchJson('/api/workflow/items')).resolves.toEqual({ ok: 1 })
    expect(refresh).toHaveBeenCalledTimes(1)
    expect(fetch).toHaveBeenCalledTimes(2)
    expect(fetch.mock.calls[1][1].headers.Authorization).toBe('Bearer new')
  })

  it('does not loop: a second 401 signals sign-in and throws', async () => {
    setAccessTokenProvider(async () => 't')
    const refresh = vi.fn(async () => ({ access_token: 't2' }))
    setSessionRefresher(refresh)
    const listener = vi.fn()
    const off = onUnauthorized(listener)
    vi.stubGlobal('fetch', vi.fn(async () => reply(401, { detail: 'nope' })))
    const err = await fetchJson('/api/workflow/items').catch(e => e)
    off()
    expect(err).toBeInstanceOf(ApiError)
    expect(err.status).toBe(401)
    expect(fetch).toHaveBeenCalledTimes(2)
    expect(refresh).toHaveBeenCalledTimes(1)
    expect(listener).toHaveBeenCalledTimes(1)
  })

  it('signals sign-in without retrying when refresh fails', async () => {
    setAccessTokenProvider(async () => 't')
    setSessionRefresher(async () => { throw new Error('refresh failed') })
    const listener = vi.fn()
    const off = onUnauthorized(listener)
    vi.stubGlobal('fetch', vi.fn(async () => reply(401)))
    await expect(fetchJson('/api/workflow/items')).rejects.toMatchObject({ status: 401 })
    off()
    expect(fetch).toHaveBeenCalledTimes(1)
    expect(listener).toHaveBeenCalledTimes(1)
  })

  it('ignores 401 from non-workflow routes and local mode', async () => {
    setAccessTokenProvider(async () => 't')
    const refresh = vi.fn()
    setSessionRefresher(refresh)
    vi.stubGlobal('fetch', vi.fn(async () => reply(401)))
    await expect(fetchJson('/api/profile')).rejects.toMatchObject({ status: 401 })
    setAccessTokenProvider(null)
    await expect(fetchJson('/api/workflow/items')).rejects.toMatchObject({ status: 401 })
    expect(refresh).not.toHaveBeenCalled()
  })
})
