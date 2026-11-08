import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from './client'
import { createSource, getSettings, saveProfile, updateSource } from './settings'

afterEach(() => vi.unstubAllGlobals())

describe('settings API client', () => {
  it('uses the creator-scoped endpoints and sends exact retry keys', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({}) })
    vi.stubGlobal('fetch', fetchMock)
    await getSettings()
    const profile = { name: '  Name  ', role: '', bio: 'line\n', expected_revision: 0 }
    await saveProfile(profile, 'same-profile-key')
    await createSource({ kind: 'rss', name: 'Feed', url: 'https://example.org/rss', enabled: true }, 'create-key')
    await updateSource('id/a?', { expected_revision: 1, enabled: false }, 'edit-key')
    expect(fetchMock.mock.calls[0][0]).toBe('/api/workflow/settings')
    expect(fetchMock.mock.calls[1][1]).toMatchObject({ method: 'PUT', body: JSON.stringify(profile),
      headers: { 'Content-Type': 'application/json', 'Idempotency-Key': 'same-profile-key' } })
    expect(fetchMock.mock.calls[2][0]).toBe('/api/workflow/settings/sources')
    expect(fetchMock.mock.calls[2][1].method).toBe('POST')
    expect(fetchMock.mock.calls[3][0]).toBe('/api/workflow/settings/sources/id%2Fa%3F')
    expect(fetchMock.mock.calls[3][1].headers['Idempotency-Key']).toBe('edit-key')
  })

  it('rejects an absent request key before network access', () => {
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)
    expect(() => saveProfile({}, undefined)).toThrow(ApiError)
    expect(() => createSource({}, '   ')).toThrow(ApiError)
    expect(() => updateSource('id', {}, '')).toThrow(ApiError)
    expect(fetchMock).not.toHaveBeenCalled()
  })
})
