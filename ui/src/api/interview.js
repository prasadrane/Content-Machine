import { fetchJson } from './client'

export function getBrief(payload) {
  return fetchJson('/api/interview/brief', { method: 'POST', body: payload })
}

export function synthesizeDraft(payload) {
  return fetchJson('/api/interview/synthesize', { method: 'POST', body: payload })
}

export async function transcribeAudio(blob, filename = 'recording.webm') {
  const formData = new FormData()
  formData.append('audio', blob, filename)
  const res = await fetch('/api/interview/transcribe', {
    method: 'POST',
    body: formData,
  })
  if (!res.ok) throw new Error(`Transcription failed (${res.status})`)
  return res.json()
}
