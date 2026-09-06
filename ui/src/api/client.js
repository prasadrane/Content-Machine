export class ApiError extends Error {
  constructor(message, status, body) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.body = body
  }
}

export async function fetchJson(url, { method = 'GET', body, headers } = {}) {
  const hasBody = body !== undefined
  const res = await fetch(url, {
    method,
    headers: hasBody ? { 'Content-Type': 'application/json', ...headers } : headers,
    body: hasBody ? JSON.stringify(body) : undefined,
  })
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
