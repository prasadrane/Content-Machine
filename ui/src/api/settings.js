import { ApiError, fetchJson } from './client'

const base = '/api/workflow/settings'

function headers(requestId) {
  if (typeof requestId !== 'string' || !requestId.trim()) {
    throw new ApiError('An Idempotency-Key is required for this request', 0, null)
  }
  return { 'Idempotency-Key': requestId }
}

export function createRequestId() {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID()
  if (!globalThis.crypto?.getRandomValues) throw new Error('This browser cannot create a request ID.')
  return Array.from(globalThis.crypto.getRandomValues(new Uint8Array(16)),
    byte => byte.toString(16).padStart(2, '0')).join('')
}

export const getSettings = () => fetchJson(base)
export const saveProfile = (body, requestId) => fetchJson(`${base}/profile`, {
  method: 'PUT', body, headers: headers(requestId),
})
export const createSource = (body, requestId) => fetchJson(`${base}/sources`, {
  method: 'POST', body, headers: headers(requestId),
})
export const updateSource = (id, body, requestId) => fetchJson(`${base}/sources/${encodeURIComponent(id)}`, {
  method: 'PATCH', body, headers: headers(requestId),
})
