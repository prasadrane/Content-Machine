import { fetchJson } from './client'

export function getProfile() {
  return fetchJson('/api/profile')
}

export function saveProfile(payload) {
  return fetchJson('/api/profile', { method: 'POST', body: payload })
}
