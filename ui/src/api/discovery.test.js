import { describe, expect, it, vi } from 'vitest'
import { fetchJson } from './client'
import { refreshDiscovery } from './discovery'

vi.mock('./client', () => ({ fetchJson: vi.fn() }))

describe('discovery API', () => {
  it('calls only the owner-scoped refresh route and propagates errors', async () => {
    fetchJson.mockRejectedValueOnce(new Error('Source service unavailable'))
    await expect(refreshDiscovery()).rejects.toThrow('Source service unavailable')
    expect(fetchJson).toHaveBeenCalledWith('/api/workflow/discovery/refresh', { method: 'POST' })
  })
})
