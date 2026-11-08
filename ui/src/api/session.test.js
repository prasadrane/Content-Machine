import { afterEach, expect, it, vi } from 'vitest'
import { authenticatedHeaders, setAccessTokenProvider } from './session'

afterEach(() => setAccessTokenProvider(null))

it('adds the current token only to same-origin owned workflow requests', async () => {
  const provider = vi.fn().mockResolvedValue('current-session-token')
  setAccessTokenProvider(provider)
  await expect(authenticatedHeaders('/api/workflow/items', { Accept: 'text/plain' })).resolves.toEqual({
    Accept: 'text/plain', Authorization: 'Bearer current-session-token',
  })
  await expect(authenticatedHeaders('https://elsewhere.example/api/workflow/items')).resolves.toBeUndefined()
  await expect(authenticatedHeaders('/api/profile')).resolves.toBeUndefined()
  expect(provider).toHaveBeenCalledTimes(1)
})

it('leaves local requests unchanged and resolves fresh tokens for every request', async () => {
  await expect(authenticatedHeaders('/api/workflow/items')).resolves.toBeUndefined()
  const provider = vi.fn().mockResolvedValueOnce('first').mockResolvedValueOnce('second')
  setAccessTokenProvider(provider)
  expect((await authenticatedHeaders('/api/workflow/items')).Authorization).toBe('Bearer first')
  expect((await authenticatedHeaders('/api/workflow/items')).Authorization).toBe('Bearer second')
})

it('propagates session refresh errors before a request can be sent', async () => {
  setAccessTokenProvider(async () => { throw new Error('Session expired') })
  await expect(authenticatedHeaders('/api/workflow/items')).rejects.toThrow('Session expired')
})
