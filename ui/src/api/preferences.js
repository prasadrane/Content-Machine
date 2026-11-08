import { ApiError, fetchJson } from './client'

const base = '/api/workflow/preferences'
const pathFor = id => `${base}/${encodeURIComponent(id)}`

function mutate(path, method, body, requestId) {
  if (typeof requestId !== 'string' || !requestId.trim()) {
    throw new ApiError('An Idempotency-Key is required for this request', 0, null)
  }
  return fetchJson(path, { method, body, headers: { 'Idempotency-Key': requestId } })
}

export const getPreferences = () => fetchJson(base)
export const getPreferenceHistory = id => fetchJson(`${pathFor(id)}/history`)
export const createPreference = (body, key) => mutate(base, 'POST', body, key)
export const editPreference = (id, body, key) => mutate(pathFor(id), 'PATCH', body, key)
export const activatePreference = (id, body, key) => mutate(`${pathFor(id)}/activate`, 'POST', body, key)
export const stopPreference = (id, body, key) => mutate(`${pathFor(id)}/stop`, 'POST', body, key)
export const rejectPreference = (id, body, key) => mutate(`${pathFor(id)}/reject`, 'POST', body, key)
