import { describe, expect, it, vi } from 'vitest'
import { createAuthService, resolveWorkspaceMode } from './auth'

describe('workspace auth service', () => {
  it('requires explicit hosted mode and rejects missing hosted configuration', () => {
    expect(resolveWorkspaceMode({})).toBe('local')
    expect(() => createAuthService({ mode: 'hosted', url: '', anonKey: '' })).toThrow(/configuration/i)
  })

  it('uses the SDK for PKCE sign in, guest sessions, tokens and sign out', async () => {
    const auth = {
      signInWithOAuth: vi.fn().mockResolvedValue({ data: {}, error: null }),
      signInAnonymously: vi.fn().mockResolvedValue({ data: {}, error: null }),
      getSession: vi.fn().mockResolvedValue({ data: { session: { access_token: 'token' } }, error: null }),
      signOut: vi.fn().mockResolvedValue({ error: null }),
    }
    const createClient = vi.fn(() => ({ auth }))
    const service = createAuthService({ mode: 'hosted', url: 'https://example.supabase.co', anonKey: 'public-key', createClient })
    expect(createClient.mock.calls[0][2].auth).toMatchObject({ flowType: 'pkce', persistSession: true, autoRefreshToken: true })
    await service.signInWithGoogle('https://app.example/')
    expect(auth.signInWithOAuth).toHaveBeenCalledWith({ provider: 'google', options: { redirectTo: 'https://app.example/' } })
    await service.signInAsGuest()
    expect(auth.signInAnonymously).toHaveBeenCalled()
    expect(await service.getAccessToken()).toBe('token')
    await service.signOut()
    expect(auth.signOut).toHaveBeenCalled()
  })

  it('propagates SDK errors and provides no token in local mode', async () => {
    expect(await createAuthService({ mode: 'local' }).getAccessToken()).toBeNull()
    const service = createAuthService({ mode: 'hosted', url: 'https://example.test', anonKey: 'key', createClient: () => ({ auth: { signInAnonymously: async () => ({ error: new Error('unavailable') }) } }) })
    await expect(service.signInAsGuest()).rejects.toThrow('unavailable')
  })
})
