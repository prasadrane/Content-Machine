import { ApiError, fetchJson } from './client'
import { authenticatedHeaders } from './session'

const base = '/api/workflow'
const itemPath = id => `${base}/items/${encodeURIComponent(id)}`
const exportPath = (id, versionId) => `${itemPath(id)}/exports/${encodeURIComponent(versionId)}`

// Rejected locally, before any request is sent. A missing or blank key is a
// caller error, so it keeps the shared ApiError contract with status 0.
const invalidRequest = message => new ApiError(message, 0, null)

function requireRequestId(requestId) {
  if (typeof requestId !== 'string' || requestId.trim() === '') {
    throw invalidRequest('An Idempotency-Key is required for this request')
  }
  return requestId
}

function mutate(url, method, body, requestId) {
  return fetchJson(url, {
    method,
    body,
    headers: { 'Idempotency-Key': requireRequestId(requestId) },
  })
}

const DIGEST_PATTERN = /^sha256:[0-9a-f]{64}$/
// The server filename is a safe ASCII slug plus -r<revision>.txt. Anything
// else (paths, header breaks, control characters) is never guessed at.
const SAFE_FILENAME = /^[A-Za-z0-9][A-Za-z0-9._ -]*$/

function downloadFilename(disposition) {
  if (typeof disposition !== 'string') return null
  const match = /(?:^|;)\s*filename\s*=\s*(?:"([^"]*)"|([^";]+))/i.exec(disposition)
  if (!match) return null
  const filename = (match[1] ?? match[2] ?? '').trim()
  if (!filename || filename.length > 255 || !SAFE_FILENAME.test(filename)) return null
  return filename
}

const unusableResponse = (message, status) => new ApiError(message, status, null)

export const getCapabilities = () => fetchJson(`${base}/capabilities`)
export const getItems = () => fetchJson(`${base}/items`)
export const getItem = id => fetchJson(itemPath(id))
export const createItem = (body, requestId) => mutate(`${base}/items`, 'POST', body, requestId)
export const saveItem = (id, body, requestId) => mutate(itemPath(id), 'PATCH', body, requestId)
export const getHistory = id => fetchJson(`${itemPath(id)}/versions`)
export const getVersion = (id, versionId) => fetchJson(`${itemPath(id)}/versions/${encodeURIComponent(versionId)}`)
export const getOperations = id => fetchJson(`${itemPath(id)}/operations`)
export const getOperation = (id, operationId) => fetchJson(`${itemPath(id)}/operations/${encodeURIComponent(operationId)}`)
export const abandonOperation = (id, operationId) => fetchJson(`${itemPath(id)}/operations/${encodeURIComponent(operationId)}/abandon`, { method: 'POST', body: { confirm: true } })
export const generateDraft = (id, body, requestId) => mutate(`${itemPath(id)}/generate`, 'POST', body, requestId)
export const reviewDraft = (id, body, requestId) => mutate(`${itemPath(id)}/review`, 'POST', body, requestId)
export const skipReview = (id, body, requestId) => mutate(`${itemPath(id)}/skip-review`, 'POST', body, requestId)
export const approveItem = (id, body, requestId) => mutate(`${itemPath(id)}/approve`, 'POST', body, requestId)
export const restoreVersion = (id, body, requestId) => mutate(`${itemPath(id)}/restore`, 'POST', body, requestId)
export const adaptVersion = (id, body, requestId) => mutate(`${itemPath(id)}/adapt`, 'POST', body, requestId)
export const getExport = (id, versionId) => fetchJson(`${exportPath(id, versionId)}?as=json`)

/**
 * Download one approved version as the server's exact bytes.
 *
 * The current workspace token authenticates hosted requests. A response is only
 * accepted when it carries both the server's safe Content-Disposition filename
 * and its artifact digest; otherwise it rejects with ApiError rather than
 * inventing a name or returning a hollow success.
 */
export async function getDownload(itemId, versionId) {
  const url = exportPath(itemId, versionId)
  const res = await fetch(url, {
    method: 'GET',
    credentials: 'same-origin',
    headers: await authenticatedHeaders(url, { Accept: 'text/plain' }),
  })
  if (!res.ok) {
    let detail = null
    try { detail = await res.json() } catch { /* binary or empty error body */ }
    throw new ApiError(
      (detail && detail.detail) || `GET ${url} failed (${res.status})`,
      res.status,
      detail,
    )
  }

  const filename = downloadFilename(res.headers?.get?.('Content-Disposition'))
  if (!filename) {
    throw unusableResponse(
      'The export response did not provide a usable Content-Disposition filename',
      res.status,
    )
  }
  const artifactDigest = res.headers?.get?.('X-Artifact-Digest')
  if (typeof artifactDigest !== 'string' || !DIGEST_PATTERN.test(artifactDigest)) {
    throw unusableResponse(
      'The export response did not provide a usable X-Artifact-Digest',
      res.status,
    )
  }
  if (typeof res.blob !== 'function') {
    throw unusableResponse('The export response did not contain a readable file body', res.status)
  }
  const blob = await res.blob()
  if (!blob || blob.size === 0) {
    throw unusableResponse(
      'The export response was empty; no approved text was returned',
      res.status,
    )
  }
  return { blob, filename, artifactDigest }
}
