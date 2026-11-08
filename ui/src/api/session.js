let accessTokenProvider = null

export function setAccessTokenProvider(provider) {
  accessTokenProvider = typeof provider === 'function' ? provider : null
}

// Credentials belong only on the same-origin owned API. Resolve at request
// time so refresh and sign-out never reuse an earlier cached token.
export async function authenticatedHeaders(url, headers) {
  if (!accessTokenProvider || typeof url !== 'string' ||
      !(url === '/api/workflow' || url.startsWith('/api/workflow/'))) return headers
  const token = await accessTokenProvider()
  return token ? { ...headers, Authorization: `Bearer ${token}` } : headers
}
