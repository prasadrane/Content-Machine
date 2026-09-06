import { fetchJson } from './client'

export function generateComments(payload) {
  return fetchJson('/api/comments/generate', { method: 'POST', body: payload })
}

export function getCommentsHistory(limit = 50) {
  return fetchJson(`/api/comments/history?limit=${limit}`)
}
