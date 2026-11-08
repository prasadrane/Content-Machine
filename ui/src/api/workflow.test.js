import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from './client'
import * as workflow from './workflow'
import { setAccessTokenProvider } from './session'

const digest = `sha256:${'a'.repeat(64)}`
const exactText = '  Exact café\r\nsecond line  \n'

const stub = res => {
  const fetchMock = vi.fn().mockResolvedValue(res)
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

const jsonResponse = (payload, status = 200) => ({
  ok: status >= 200 && status < 300,
  status,
  headers: new Headers({ 'Content-Type': 'application/json' }),
  json: async () => payload,
})

// Headers.set refuses CR/LF values, so a plain accessor stands in for a real
// response: the parser must see exactly what a malformed header could carry.
const headerBag = values => {
  const normalized = Object.fromEntries(
    Object.entries(values).map(([name, value]) => [name.toLowerCase(), value]),
  )
  return { get: name => normalized[String(name).toLowerCase()] ?? null }
}

const downloadResponse = ({
  disposition = 'attachment; filename="server-chosen-r9.txt"',
  artifactDigest = digest,
  text = exactText,
  status = 200,
  blob,
} = {}) => {
  const values = {}
  if (disposition !== null) values['Content-Disposition'] = disposition
  if (artifactDigest !== null) values['X-Artifact-Digest'] = artifactDigest
  const body = new Blob([new TextEncoder().encode(text)], { type: 'text/plain; charset=utf-8' })
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: headerBag(values),
    blob: blob === undefined ? async () => body : blob,
    json: async () => { throw new SyntaxError('not json') },
  }
}

afterEach(() => { vi.unstubAllGlobals(); setAccessTokenProvider(null) })

it('loads a read-only snapshot using encoded identifiers and workspace authentication', async () => {
  const fetchMock = stub(jsonResponse({ version: { version_id: 'old', artifact: { segments: [exactText] } } }))
  setAccessTokenProvider(async () => 'workspace-token')
  const result = await workflow.getVersion('item/one', 'version/old')
  expect(fetchMock.mock.calls[0][0]).toBe('/api/workflow/items/item%2Fone/versions/version%2Fold')
  expect(fetchMock.mock.calls[0][1].headers.Authorization).toBe('Bearer workspace-token')
  expect(result.version.artifact.segments).toEqual([exactText])
})

it('authenticates an exact download using the refreshed workspace token', async () => {
  const fetchMock = stub(downloadResponse())
  setAccessTokenProvider(async () => 'fresh-workspace-token')
  const result = await workflow.getDownload('one', 'v1')
  expect(fetchMock.mock.calls[0][1].headers.Authorization).toBe('Bearer fresh-workspace-token')
  expect(await result.blob.text()).toBe(exactText)
})

it('does not request a download when session refresh fails', async () => {
  const fetchMock = stub(downloadResponse())
  setAccessTokenProvider(async () => { throw new Error('Session expired') })
  await expect(workflow.getDownload('one', 'v1')).rejects.toThrow('Session expired')
  expect(fetchMock).not.toHaveBeenCalled()
})

describe('workflow API mutations', () => {
  it('rejects missing or blank request ids before any network call', async () => {
    const fetchMock = stub(jsonResponse({}))
    const attempts = [
      () => workflow.createItem({ title: 'A' }, undefined),
      () => workflow.createItem({ title: 'A' }, '   '),
      () => workflow.saveItem('id', { expected_revision: 1 }, ''),
      () => workflow.skipReview('id', { expected_revision: 1 }, null),
      () => workflow.approveItem('id', {}, undefined),
      () => workflow.restoreVersion('id', {}, ' \n '),
      () => workflow.adaptVersion('id', {}, ''),
    ]
    for (const attempt of attempts) {
      const error = await Promise.resolve().then(attempt).catch(caught => caught)
      expect(error).toBeInstanceOf(ApiError)
      expect(error.message).toMatch(/Idempotency-Key/)
      expect(error.status).toBe(0)
      expect(error.body).toBeNull()
    }
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('sends exact endpoints, methods, bodies and stable keys', async () => {
    const fetchMock = stub(jsonResponse({ item: { item_id: 'one' } }))
    const body = { expected_revision: 2, artifact: { segments: ['  exact \r\ntext  '] } }

    await workflow.saveItem('one/two?#', body, 'stable-key-1')
    const [url, options] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/workflow/items/one%2Ftwo%3F%23')
    expect(options.method).toBe('PATCH')
    expect(options.headers['Idempotency-Key']).toBe('stable-key-1')
    expect(options.headers['Content-Type']).toBe('application/json')
    expect(options.body).toBe(JSON.stringify(body))
    expect(JSON.parse(options.body)).toEqual(body)

    const routes = [
      [workflow.skipReview, 'skip-review'],
      [workflow.approveItem, 'approve'],
      [workflow.restoreVersion, 'restore'],
      [workflow.adaptVersion, 'adapt'],
    ]
    for (const [call, name] of routes) {
      await call(' itm 1 ', { expected_revision: 3 }, `key-${name}`)
    }
    routes.forEach(([, name], index) => {
      const [routeUrl, routeOptions] = fetchMock.mock.calls[index + 1]
      expect(routeUrl).toBe(`/api/workflow/items/%20itm%201%20/${name}`)
      expect(routeOptions.method).toBe('POST')
      expect(routeOptions.headers['Idempotency-Key']).toBe(`key-${name}`)
    })
  })

  it('propagates conflicts rather than presenting an empty list', async () => {
    stub(jsonResponse({ detail: 'Revision changed', working_revision: 5 }, 409))
    await expect(workflow.getItems()).rejects.toMatchObject({
      message: 'Revision changed',
      status: 409,
      body: { working_revision: 5 },
    })
  })

  it('keeps json export for clipboard and per-thread-post copy', async () => {
    const payload = {
      version_id: 'ver_1',
      destination: 'x',
      format: 'x_thread',
      artifact_digest: digest,
      segments: [' first \r\n', 'second  '],
    }
    const fetchMock = stub(jsonResponse(payload))
    await expect(workflow.getExport('itm', 'ver/1')).resolves.toEqual(payload)
    expect(fetchMock.mock.calls[0][0]).toBe('/api/workflow/items/itm/exports/ver%2F1?as=json')
    expect(fetchMock.mock.calls[0][1].method).toBe('GET')
  })
})

describe('workflow binary download', () => {
  it('returns the exact approved bytes with the server filename and digest', async () => {
    const fetchMock = stub(downloadResponse())
    const result = await workflow.getDownload('itm/1', 'ver 2')
    const [url, options] = fetchMock.mock.calls[0]

    expect(url).toBe('/api/workflow/items/itm%2F1/exports/ver%202')
    expect(options.method).toBe('GET')
    expect(options.credentials).toBe('same-origin')
    expect(options.headers).toEqual({ Accept: 'text/plain' })
    expect(result.filename).toBe('server-chosen-r9.txt')
    expect(result.artifactDigest).toBe(digest)
    expect(result.blob).toBeInstanceOf(Blob)
    expect(result.blob.type).toBe('text/plain; charset=utf-8')
    expect(result.blob.size).toBe(new TextEncoder().encode(exactText).length)
  })

  it('accepts quoted or bare server filenames verbatim', async () => {
    for (const [disposition, expected] of [
      ['attachment; filename="thread-r4.txt"', 'thread-r4.txt'],
      ['attachment; filename=plain-r1.txt', 'plain-r1.txt'],
    ]) {
      stub(downloadResponse({ disposition }))
      await expect(workflow.getDownload('itm', 'ver')).resolves.toMatchObject({ filename: expected })
    }
  })

  it('rejects an unusable filename instead of inventing one', async () => {
    const unusable = [
      null,
      '',
      'inline',
      'attachment',
      'attachment; filename=""',
      'attachment; filename="../../etc/passwd"',
      'attachment; filename="a\r\nb.txt"',
      `attachment; filename="${'x'.repeat(260)}.txt"`,
    ]
    for (const disposition of unusable) {
      stub(downloadResponse({ disposition }))
      const error = await workflow.getDownload('itm', 'ver').catch(caught => caught)
      expect(error).toBeInstanceOf(ApiError)
      expect(error.message).toMatch(/Content-Disposition/)
      expect(error.body).toBeNull()
    }
  })

  it('rejects a missing or malformed artifact digest', async () => {
    for (const artifactDigest of [null, '', 'sha256:short', `md5:${'a'.repeat(32)}`, `SHA256:${'a'.repeat(64)}`]) {
      stub(downloadResponse({ artifactDigest }))
      const error = await workflow.getDownload('itm', 'ver').catch(caught => caught)
      expect(error).toBeInstanceOf(ApiError)
      expect(error.message).toMatch(/X-Artifact-Digest/)
    }
  })

  it('rejects an empty or unreadable body rather than returning a hollow success', async () => {
    stub(downloadResponse({ blob: async () => new Blob([]) }))
    await expect(workflow.getDownload('itm', 'ver')).rejects.toThrow(/empty/i)

    stub(downloadResponse({ blob: null }))
    await expect(workflow.getDownload('itm', 'ver')).rejects.toThrow(/file body/i)
  })

  it('propagates download failures through the ApiError contract', async () => {
    const detail = {
      detail: 'A matching approval for this exact version is required',
      code: 'approval_required',
      working_revision: 4,
    }
    stub({ ok: false, status: 409, headers: new Headers(), json: async () => detail })
    const conflict = await workflow.getDownload('itm', 'ver').catch(caught => caught)
    expect(conflict).toBeInstanceOf(ApiError)
    expect(conflict.message).toBe(detail.detail)
    expect(conflict.status).toBe(409)
    expect(conflict.body).toEqual(detail)

    stub({
      ok: false,
      status: 502,
      headers: new Headers(),
      json: async () => { throw new SyntaxError('Unexpected token <') },
    })
    const providerError = await workflow.getDownload('itm', 'ver').catch(caught => caught)
    expect(providerError).toBeInstanceOf(ApiError)
    expect(providerError.message).toBe('GET /api/workflow/items/itm/exports/ver failed (502)')
    expect(providerError.status).toBe(502)
    expect(providerError.body).toBeNull()
  })
})
