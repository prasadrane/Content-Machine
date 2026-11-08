import { createClient as sdkCreateClient } from '@supabase/supabase-js'

export function resolveWorkspaceMode(env = import.meta.env) {
  return env.VITE_WORKSPACE_MODE === 'hosted' ? 'hosted' : 'local'
}

export function createAuthService({ mode = resolveWorkspaceMode(), url = import.meta.env.VITE_SUPABASE_URL,
  anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY, createClient = sdkCreateClient } = {}) {
  if (mode === 'local') return { mode, getAccessToken: async () => null }
  if (mode !== 'hosted' || !url || !anonKey) throw new Error('Hosted workspace configuration is missing.')
  const { auth } = createClient(url, anonKey, { auth: { flowType: 'pkce', persistSession: true, autoRefreshToken: true, detectSessionInUrl: true } })
  const checked = async promise => {
    const result = await promise
    if (result.error) throw result.error
    return result.data
  }
  return {
    mode,
    async getSession() { return (await checked(auth.getSession())).session },
    async getAccessToken() { return (await checked(auth.getSession())).session?.access_token ?? null },
    async signInWithGoogle(redirectTo) {
      return checked(auth.signInWithOAuth({ provider: 'google', options: { redirectTo } }))
    },
    async signInAsGuest() { return checked(auth.signInAnonymously()) },
    async signOut() { await checked(auth.signOut()) },
    onAuthStateChange(callback) {
      const { data } = auth.onAuthStateChange(callback)
      return () => data.subscription.unsubscribe()
    },
  }
}

// Initialize once and pass the same service to AuthGate and API clients.
export function createConfiguredAuth(env = import.meta.env) {
  return createAuthService({ mode: resolveWorkspaceMode(env), url: env.VITE_SUPABASE_URL, anonKey: env.VITE_SUPABASE_ANON_KEY })
}
