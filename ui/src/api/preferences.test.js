import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from './client'
import * as preferences from './preferences'

afterEach(() => vi.unstubAllGlobals())
describe('preference API', () => {
  it('sends scoped actions with the exact body and idempotency key', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ preference: {} }) })
    vi.stubGlobal('fetch', fetchMock)
    const body = { text: '  Exact preference\n', expected_revision: 4, consent: true }
    await preferences.editPreference('pref/1', body, 'stable-key')
    expect(fetchMock).toHaveBeenCalledWith('/api/workflow/preferences/pref%2F1', {
      method: 'PATCH', headers: { 'Content-Type': 'application/json', 'Idempotency-Key': 'stable-key' },
      body: JSON.stringify(body),
    })
    await preferences.rejectPreference('pref/1', { expected_revision: 4 }, 'reject-key')
    expect(fetchMock.mock.calls[1][0]).toBe('/api/workflow/preferences/pref%2F1/reject')
  })
  it('rejects missing keys locally and preserves real conflict responses', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false, status: 409, json: async () => ({ detail: 'Similar preference', code: 'preference_conflict' }),
    })
    vi.stubGlobal('fetch', fetchMock)
    expect(() => preferences.createPreference({ text: 'Example', consent: true }, '  ')).toThrow(ApiError)
    expect(fetchMock).not.toHaveBeenCalled()
    await expect(preferences.createPreference({ text: 'Example', consent: true }, 'key')).rejects.toMatchObject({
      status: 409, message: 'Similar preference', body: { code: 'preference_conflict' },
    })
  })
})
