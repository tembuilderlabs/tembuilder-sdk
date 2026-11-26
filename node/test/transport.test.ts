import { describe, expect, it } from 'vitest'

import { APIError, ConnectionError, TimeoutError } from '../src/index.js'
import { backoff, createTransport, sleep } from '../src/transport.js'
import { client, fakeFetch, json } from './helpers.js'

const unavailable = () => json(503, { code: 'COMMON_UNAVAILABLE', description: 'busy', details: [] })
const ok = () => json(200, { api_key_id: 'k' })
const fast = { maxRetries: 2, retryBaseDelayMs: 1, maxRetryDelayMs: 2 }

describe('retries', () => {
  it('retries a GET on 503 and succeeds', async () => {
    const { fetch, requests } = fakeFetch(unavailable, ok)
    await expect(client(fetch, fast).account.get()).resolves.toEqual({ api_key_id: 'k' })
    expect(requests).toHaveLength(2)
  })

  it.each([429, 502, 504])('retries a GET on %i', async (code) => {
    const { fetch, requests } = fakeFetch(() => json(code, {}), ok)
    await client(fetch, fast).account.get()
    expect(requests).toHaveLength(2)
  })

  it('honours Retry-After, capped by maxRetryDelayMs', async () => {
    const { fetch, requests } = fakeFetch(() => json(503, {}, { 'retry-after': '120' }), ok)
    const started = Date.now()
    await client(fetch, fast).account.get()
    expect(Date.now() - started).toBeLessThan(1_000)
    expect(requests).toHaveLength(2)
  })

  it('resends a POST body when the render endpoint was busy (503)', async () => {
    const { fetch, requests } = fakeFetch(unavailable, () => json(202, { render_id: 'r', status: 'queued', status_url: '/v1/renders/r' }))
    await client(fetch, fast).renders.create({ template_id: 't', parameters: { a: 1 } })
    expect(requests).toHaveLength(2)
    expect(await requests[1].json()).toEqual({ template_id: 't', parameters: { a: 1 } })
  })

  it('never resends a POST after a 502', async () => {
    const { fetch, requests } = fakeFetch(() => json(502, {}))
    await expect(client(fetch, fast).renders.create({ template_id: 't' })).rejects.toBeInstanceOf(APIError)
    expect(requests).toHaveLength(1)
  })

  it('returns the last response once retries are exhausted', async () => {
    const { fetch, requests } = fakeFetch(unavailable)
    const error = await client(fetch, fast).account.get().catch((e: unknown) => e)
    expect((error as APIError).code).toBe('COMMON_UNAVAILABLE')
    expect(requests).toHaveLength(3)
  })

  it('retries a GET after a network error', async () => {
    let calls = 0
    const fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
      calls++
      if (calls === 1) throw new TypeError('socket hang up')
      return ok()
    }) as typeof globalThis.fetch
    await client(fetch, fast).account.get()
    expect(calls).toBe(2)
  })

  it('does not resend a POST after a network error and reports ConnectionError', async () => {
    let calls = 0
    const fetch = (async () => {
      calls++
      throw new TypeError('reset')
    }) as typeof globalThis.fetch
    const error = await client(fetch, fast).renders.create({ template_id: 't' }).catch((e: unknown) => e)
    expect(error).toBeInstanceOf(ConnectionError)
    expect((error as Error).message).toContain('reset')
    expect(calls).toBe(1)
  })

  it('reports TimeoutError when an attempt exceeds timeoutMs', async () => {
    const fetch = ((input: RequestInfo | URL, init?: RequestInit) =>
      new Promise<Response>((_resolve, reject) => {
        const signal = (input as Request).signal
        signal.addEventListener('abort', () => reject(signal.reason))
      })) as typeof globalThis.fetch
    const error = await client(fetch, { timeoutMs: 5 }).account.get().catch((e: unknown) => e)
    expect(error).toBeInstanceOf(TimeoutError)
  })

  it('propagates a caller abort without retrying', async () => {
    const controller = new AbortController()
    let calls = 0
    const fetch = (async () => {
      calls++
      controller.abort(new Error('caller gave up'))
      throw new DOMException('aborted', 'AbortError')
    }) as typeof globalThis.fetch
    const transport = createTransport({ fetch, timeoutMs: 1_000, retry: { maxRetries: 3, baseDelayMs: 1, maxDelayMs: 1 } })
    await expect(transport(new Request('https://api.test/v1/me', { signal: controller.signal }))).rejects.toThrow('caller gave up')
    expect(calls).toBe(1)
  })
})

describe('backoff', () => {
  const policy = { maxRetries: 5, baseDelayMs: 100, maxDelayMs: 1_000 }

  it('uses full jitter under an exponential ceiling', () => {
    expect(backoff(policy, 0, undefined, () => 0.5)).toBe(50)
    expect(backoff(policy, 3, undefined, () => 0.999)).toBe(799)
    expect(backoff(policy, 10, undefined, () => 1)).toBe(1_000)
  })

  it('prefers Retry-After within the cap', () => {
    expect(backoff(policy, 0, 0, () => 1)).toBe(0)
    expect(backoff(policy, 0, 30, () => 1)).toBe(1_000)
  })

  it('uses Math.random by default', async () => {
    const { fetch } = fakeFetch(unavailable, ok)
    const transport = createTransport({ fetch, timeoutMs: 1_000, retry: { maxRetries: 1, baseDelayMs: 1, maxDelayMs: 1 } })
    expect((await transport(new Request('https://api.test/v1/me'))).status).toBe(200)
  })
})

describe('sleep', () => {
  it('resolves after the delay', async () => {
    await expect(sleep(1)).resolves.toBeUndefined()
  })

  it('rejects immediately for an aborted signal', async () => {
    await expect(sleep(1_000, AbortSignal.abort(new Error('stop')))).rejects.toThrow('stop')
  })

  it('rejects when aborted while waiting and clears the timer', async () => {
    const controller = new AbortController()
    const pending = sleep(10_000, controller.signal)
    controller.abort(new Error('later'))
    await expect(pending).rejects.toThrow('later')
  })

  it('resolves with a signal that is never aborted', async () => {
    await expect(sleep(1, new AbortController().signal)).resolves.toBeUndefined()
  })
})
