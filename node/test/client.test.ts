import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  APIError,
  DEFAULT_BASE_URL,
  RenderFailedError,
  RenderTimeoutError,
  Tembuilder,
  TembuilderError,
  VERSION,
  filenameFromDisposition,
} from '../src/index.js'
import { client, fakeFetch, json } from './helpers.js'

const RENDER = '5a6b7c8d-1e2f-4a3b-8c4d-5e6f7a8b9c0d'
const notFound = () => json(404, { code: 'RENDER_NOT_FOUND', description: 'render not found', details: [] })
const status = (value: string, extra: Record<string, unknown> = {}) => () => json(200, { render_id: RENDER, status: value, ...extra })

afterEach(() => {
  vi.unstubAllEnvs()
})

describe('Tembuilder construction', () => {
  it('requires an API key', () => {
    vi.stubEnv('TEMBUILDER_API_KEY', '')
    expect(() => new Tembuilder()).toThrow(TembuilderError)
  })

  it('reads the key and base URL from the environment and sends identifying headers', async () => {
    vi.stubEnv('TEMBUILDER_API_KEY', 'env-key')
    vi.stubEnv('TEMBUILDER_BASE_URL', 'https://staging.test///')
    const { fetch, requests } = fakeFetch(() => json(200, {}))
    await new Tembuilder({ fetch }).account.get()
    expect(requests[0].url).toBe('https://staging.test/v1/me')
    expect(requests[0].headers.get('apikey')).toBe('env-key')
    expect(requests[0].headers.get('user-agent')).toBe(`tembuilder-node/${VERSION}`)
  })

  it('defaults to the production API origin', async () => {
    vi.stubEnv('TEMBUILDER_BASE_URL', undefined)
    const { fetch, requests } = fakeFetch(() => json(200, {}))
    await new Tembuilder({ apiKey: 'k', fetch }).account.get()
    expect(requests[0].url).toBe(`${DEFAULT_BASE_URL}/v1/me`)
  })

  it('works where process is undefined (browsers, edge runtimes)', async () => {
    const original = globalThis.process
    const { fetch, requests } = fakeFetch(() => json(200, {}))
    vi.stubGlobal('process', undefined)
    try {
      await new Tembuilder({ apiKey: 'k', fetch }).account.get()
    } finally {
      vi.stubGlobal('process', original)
    }
    expect(requests[0].url).toBe(`${DEFAULT_BASE_URL}/v1/me`)
  })

  it('falls back to the global fetch', async () => {
    const { fetch, requests } = fakeFetch(() => json(200, {}))
    vi.stubGlobal('fetch', fetch)
    try {
      await new Tembuilder({ apiKey: 'k', baseUrl: 'https://api.test' }).account.get()
    } finally {
      vi.unstubAllGlobals()
    }
    expect(requests).toHaveLength(1)
  })
})

describe('pagination helpers', () => {
  it('listAll walks templates until has_more is false', async () => {
    const { fetch, requests } = fakeFetch(
      () => json(200, { data: [{ id: 'a' }, { id: 'b' }], page: 1, per_page: 2, has_more: true }),
      () => json(200, { data: [{ id: 'c' }], page: 2, per_page: 2, has_more: false }),
    )
    const ids: string[] = []
    for await (const template of client(fetch).templates.listAll({ status: 'published', per_page: 2 })) ids.push(template.id)
    expect(ids).toEqual(['a', 'b', 'c'])
    expect(requests.map((r) => new URL(r.url).search)).toEqual(['?status=published&per_page=2&page=1', '?status=published&per_page=2&page=2'])
  })

  it('listAll walks renders with default parameters', async () => {
    const { fetch } = fakeFetch(() => json(200, { data: [{ id: 'r' }], page: 1, per_page: 30, has_more: false }))
    const sdk = client(fetch)
    const seen = []
    for await (const render of sdk.renders.listAll()) seen.push(render.id)
    expect(seen).toEqual(['r'])
    await expect(sdk.templates.list()).resolves.toBeDefined()
    await expect(sdk.renders.list()).resolves.toBeDefined()
    await expect(sdk.templates.get('invoice')).resolves.toBeDefined()
  })
})

describe('renders.download', () => {
  it('returns a null filename without Content-Disposition', async () => {
    const { fetch } = fakeFetch(() => new Response(new Uint8Array([37, 80]), { status: 200 }))
    const file = await client(fetch).renders.download(RENDER)
    expect(file.bytes).toEqual(new Uint8Array([37, 80]))
    expect(file.filename).toBeNull()
  })

  it('uses application/pdf when the response has no content type', async () => {
    const response = new Response(new Uint8Array([1]), { status: 200 })
    response.headers.delete('content-type')
    const { fetch } = fakeFetch(() => response)
    expect((await client(fetch).renders.download(RENDER)).contentType).toBe('application/pdf')
  })
})

describe('renders.waitFor / createAndWait', () => {
  it('treats an early 404 as transitional, then polls pending until success', async () => {
    const { fetch, requests } = fakeFetch(notFound, status('pending'), status('success', { download_url: '/d' }))
    const result = await client(fetch).renders.waitFor(RENDER, { pollIntervalMs: 1 })
    expect(result.status).toBe('success')
    expect(requests).toHaveLength(3)
  })

  it('queues then waits', async () => {
    const { fetch, requests } = fakeFetch(
      () => json(202, { render_id: RENDER, status: 'queued', status_url: `/v1/renders/${RENDER}` }),
      status('success'),
    )
    const result = await client(fetch).renders.createAndWait({ template_id: 't' })
    expect(result.render_id).toBe(RENDER)
    expect(requests[0].method).toBe('POST')
  })

  it.each(['failed', 'quota_exceeded'])('rejects with RenderFailedError on %s', async (terminal) => {
    const { fetch } = fakeFetch(status(terminal, { error_message: 'boom' }))
    const error = await client(fetch).renders.waitFor(RENDER).catch((e: unknown) => e)
    expect(error).toBeInstanceOf(RenderFailedError)
    expect((error as RenderFailedError).render.status).toBe(terminal)
    expect((error as Error).message).toContain('boom')
  })

  it('rejects with RenderTimeoutError carrying the last status', async () => {
    const { fetch } = fakeFetch(status('pending'))
    const error = await client(fetch).renders.waitFor(RENDER, { pollIntervalMs: 1, timeoutMs: 5 }).catch((e: unknown) => e)
    expect(error).toBeInstanceOf(RenderTimeoutError)
    expect((error as RenderTimeoutError).lastStatus?.status).toBe('pending')
    expect((error as RenderTimeoutError).renderId).toBe(RENDER)
  })

  it('reports an unknown last status when only 404s were seen before the deadline', async () => {
    const { fetch } = fakeFetch(notFound)
    const error = await client(fetch).renders.waitFor(RENDER, { pollIntervalMs: 1, timeoutMs: 5, notFoundGraceMs: 1_000 }).catch((e: unknown) => e)
    expect(error).toBeInstanceOf(RenderTimeoutError)
    expect((error as Error).message).toContain('unknown')
  })

  it('surfaces a 404 once the grace period is over', async () => {
    const { fetch } = fakeFetch(notFound)
    const error = await client(fetch).renders.waitFor(RENDER, { notFoundGraceMs: 0 }).catch((e: unknown) => e)
    expect(error).toBeInstanceOf(APIError)
    expect((error as APIError).status).toBe(404)
  })

  it('surfaces a 404 after a status was already seen', async () => {
    const { fetch } = fakeFetch(status('pending'), notFound)
    const error = await client(fetch).renders.waitFor(RENDER, { pollIntervalMs: 1 }).catch((e: unknown) => e)
    expect((error as APIError).code).toBe('RENDER_NOT_FOUND')
  })

  it('surfaces non-404 API errors immediately', async () => {
    const { fetch } = fakeFetch(() => json(403, { code: 'COMMON_FORBIDDEN', description: 'forbidden', details: [] }))
    const error = await client(fetch).renders.waitFor(RENDER).catch((e: unknown) => e)
    expect((error as APIError).status).toBe(403)
  })

  it('stops when the signal is aborted', async () => {
    const controller = new AbortController()
    controller.abort(new Error('cancelled'))
    const { fetch } = fakeFetch(status('pending'))
    await expect(client(fetch).renders.waitFor(RENDER, { signal: controller.signal })).rejects.toThrow('cancelled')
  })

  it('uses default timings', async () => {
    vi.useFakeTimers()
    try {
      const { fetch } = fakeFetch(status('pending'), status('success'))
      const pending = client(fetch).renders.waitFor(RENDER)
      await vi.advanceTimersByTimeAsync(1_000)
      await expect(pending).resolves.toMatchObject({ status: 'success' })
    } finally {
      vi.useRealTimers()
    }
  })
})

describe('filenameFromDisposition', () => {
  it.each([
    [null, null],
    ['inline', null],
    ['attachment; filename="report.pdf"', 'report.pdf'],
    ['attachment; filename=plain.pdf; size=3', 'plain.pdf'],
    ["attachment; filename*=UTF-8''h%C3%B3a-%C4%91%C6%A1n.pdf", 'hóa-đơn.pdf'],
    ["attachment; filename*=utf-8''bad%E0%A4%A.pdf", 'bad%E0%A4%A.pdf'],
  ])('%s -> %s', (header, expected) => {
    expect(filenameFromDisposition(header)).toBe(expected)
  })
})
