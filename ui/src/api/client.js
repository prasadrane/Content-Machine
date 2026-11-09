import { authenticatedHeaders, hasSessionAuth, isWorkflowUrl, notifyUnauthorized, refreshSession } from './session'

export class ApiError extends Error {
  constructor(message, status, body) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.body = body
  }
}

// Send a request; on a hosted /api/workflow 401 refresh the session once and
// retry once, then signal sign-in. `makeInit` runs per attempt so headers get
// the fresh token. Callers must retry only before consuming any response body.
export async function fetchWithReauth(url, makeInit) {
  let res = await fetch(url, await makeInit())
  if (res.status === 401 && hasSessionAuth() && isWorkflowUrl(url)) {
    let refreshed = false
    try { refreshed = Boolean(await refreshSession()) } catch { /* fall through to sign-in */ }
    if (refreshed) res = await fetch(url, await makeInit())
    if (res.status === 401) notifyUnauthorized()
  }
  return res
}

export async function fetchJson(url, { method = 'GET', body, headers } = {}) {
  const hasBody = body !== undefined
  const res = await fetchWithReauth(url, async () => ({
    method,
    headers: await authenticatedHeaders(url, hasBody ? { 'Content-Type': 'application/json', ...headers } : headers),
    body: hasBody ? JSON.stringify(body) : undefined,
  }))
  if (!res.ok) {
    let detail = null
    try { detail = await res.json() } catch { /* non-JSON error body */ }
    throw new ApiError(
      (detail && detail.detail) || `${method} ${url} failed (${res.status})`,
      res.status,
      detail,
    )
  }
  return res.json()
}
