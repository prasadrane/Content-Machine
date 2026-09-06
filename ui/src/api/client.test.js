import { describe, it, expect, vi, afterEach } from 'vitest'
import { fetchJson, ApiError } from './client'
import { getHealth } from './health'

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
