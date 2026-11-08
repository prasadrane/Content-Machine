import { getFormat } from '../../lib/platforms'

export function formatLabel(pair) {
  return getFormat(pair.destination, pair.format)?.label || `${pair.destination} · ${pair.format}`
}

export async function artifactDigest(item) {
  if (!globalThis.crypto?.subtle) {
    throw new Error('This browser cannot calculate the approval digest.')
  }
  const content = JSON.stringify({
    destination: item.destination,
    format: item.format,
    segments: item.artifact.segments,
  })
  const digest = await globalThis.crypto.subtle.digest('SHA-256', new TextEncoder().encode(content))
  const hex = Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, '0')).join('')
  return `sha256:${hex}`
}
