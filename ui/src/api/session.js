let accessTokenProvider = null

export function setAccessTokenProvider(provider) {
  accessTokenProvider = typeof provider === 'function' ? provider : null
}

// Credentials belong only on the same-origin owned API. Resolve at request
// time so refresh and sign-out never reuse an earlier cached token.
export async function authenticatedHeaders(url, headers) {
  if (!accessTokenProvider || typeof url !== 'string' ||
      !isWorkflowUrl(url)) return headers
  const token = await accessTokenProvider()
  return token ? { ...headers, Authorization: `Bearer ${token}` } : headers
}

let sessionRefresher = null
const unauthorizedListeners = new Set()

export function setSessionRefresher(refresher) {
  sessionRefresher = typeof refresher === 'function' ? refresher : null
}

export function isWorkflowUrl(url) {
  return typeof url === 'string' && (url === '/api/workflow' || url.startsWith('/api/workflow/'))
}

// Hosted mode only: true when a token provider is installed.
export function hasSessionAuth() {
  return Boolean(accessTokenProvider)
}

// Force the SDK to refresh the session; returns null when none is configured.
export async function refreshSession() {
  return sessionRefresher ? sessionRefresher() : null
}

// AuthGate subscribes so an unrecoverable 401 returns the user to sign-in.
export function onUnauthorized(listener) {
  unauthorizedListeners.add(listener)
  return () => unauthorizedListeners.delete(listener)
}

export function notifyUnauthorized() {
  unauthorizedListeners.forEach(listener => listener())
}
