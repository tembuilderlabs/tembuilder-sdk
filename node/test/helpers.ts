import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

import { Tembuilder, type TembuilderOptions } from '../src/index.js'

export const contractDir = fileURLToPath(new URL('../../contract/', import.meta.url))

export function loadJSON<T>(name: string): T {
  return JSON.parse(readFileSync(contractDir + name, 'utf8')) as T
}

export type Handler = (request: Request) => Response | Promise<Response>

/** A fetch double that records every request and answers from a handler queue. */
export function fakeFetch(...handlers: Handler[]) {
  const requests: Request[] = []
  const fetch = async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    const request = new Request(input, init)
    requests.push(request)
    const handler = handlers[Math.min(requests.length - 1, handlers.length - 1)]
    return handler(request)
  }
  return { fetch: fetch as typeof globalThis.fetch, requests }
}

export function json(status: number, body: unknown, headers: Record<string, string> = {}): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json', ...headers } })
}

export function client(fetch: typeof globalThis.fetch, options: TembuilderOptions = {}): Tembuilder {
  return new Tembuilder({
    apiKey: 'test-key',
    baseUrl: 'https://api.test',
    maxRetries: 0,
    retryBaseDelayMs: 1,
    maxRetryDelayMs: 5,
    fetch,
    ...options,
  })
}
