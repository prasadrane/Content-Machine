import { fetchJson } from './client'

export function getLessons() {
  return fetchJson('/api/lessons')
}

export function addCustomLesson(payload) {
  return fetchJson('/api/lessons/custom', { method: 'POST', body: payload })
}

export function diffLessons(payload) {
  return fetchJson('/api/lessons/diff', { method: 'POST', body: payload })
}

export function approveLesson(ruleId) {
  return fetchJson(`/api/lessons/${ruleId}/approve`, { method: 'POST' })
}

export function rejectLesson(ruleId) {
  return fetchJson(`/api/lessons/${ruleId}/reject`, { method: 'POST' })
}
