import createClient, { type Client } from 'openapi-fetch'

import { APIError, RenderFailedError, RenderTimeoutError, TembuilderError } from './errors.js'
import type { paths } from './generated/schema.js'
import { createTransport, sleep } from './transport.js'
import type {
  Account,
  GetTemplateParams,
  ListRendersParams,
  ListTemplatesParams,
  Render,
  RenderPage,
  RenderQueued,
  RenderRequest,
  RenderStatus,
  Template,
  TemplateDetail,
  TemplatePage,
} from './types.js'
import { VERSION } from './version.js'

export const DEFAULT_BASE_URL = 'https://api.tembuilder.com'

export interface TembuilderOptions {
  /** Project API key. Defaults to the TEMBUILDER_API_KEY environment variable. */
  apiKey?: string
  /** API origin. Defaults to TEMBUILDER_BASE_URL, then https://api.tembuilder.com. */
  baseUrl?: string
  /** Per-attempt HTTP timeout. Default 30 000 ms. */
  timeoutMs?: number
  /** Retries of transient failures (see README). Default 2. */
  maxRetries?: number
  /** Base of the exponential retry backoff. Default 500 ms. */
  retryBaseDelayMs?: number
  /** Upper bound of a single retry wait. Default 8 000 ms. */
  maxRetryDelayMs?: number
  /** Custom fetch implementation (proxies, instrumentation, tests). */
  fetch?: typeof globalThis.fetch
}

export interface WaitOptions {
  /** Delay between status checks. Default 1 000 ms. */
  pollIntervalMs?: number
  /** Overall deadline for the render to finish. Default 120 000 ms. */
  timeoutMs?: number
  /**
   * How long a 404 is treated as "job row not written yet" after queueing.
   * Default 15 000 ms. A 404 after that is a real error.
   */
  notFoundGraceMs?: number
  signal?: AbortSignal
}

export interface RenderFile {
  bytes: Uint8Array
  contentType: string
  /** Filename suggested by Content-Disposition, when present. */
  filename: string | null
}

type FetchResult<T> = Promise<{ data?: T; error?: unknown; response: Response }>

/**
 * Tembuilder API client.
 *
 * ```ts
 * const tembuilder = new Tembuilder({ apiKey: process.env.TEMBUILDER_API_KEY })
 * const render = await tembuilder.renders.createAndWait({ template_id, parameters })
 * const pdf = await tembuilder.renders.download(render.render_id)
 * ```
 */
export class Tembuilder {
  readonly account: AccountResource
  readonly templates: TemplatesResource
  readonly renders: RendersResource

  constructor(options: TembuilderOptions = {}) {
    const env = typeof process === 'undefined' ? {} : process.env
    const apiKey = options.apiKey ?? env.TEMBUILDER_API_KEY
    if (!apiKey) {
      throw new TembuilderError('An API key is required: pass { apiKey } or set TEMBUILDER_API_KEY.')
    }
    const baseUrl = (options.baseUrl ?? env.TEMBUILDER_BASE_URL ?? DEFAULT_BASE_URL).replace(/\/+$/, '')
    const transport = createTransport({
      fetch: options.fetch ?? globalThis.fetch,
      timeoutMs: options.timeoutMs ?? 30_000,
      retry: {
        maxRetries: options.maxRetries ?? 2,
        baseDelayMs: options.retryBaseDelayMs ?? 500,
        maxDelayMs: options.maxRetryDelayMs ?? 8_000,
      },
    })
    const client = createClient<paths>({
      baseUrl,
      fetch: transport,
      headers: { ApiKey: apiKey, 'User-Agent': `tembuilder-node/${VERSION}` },
    })
    this.account = new AccountResource(client)
    this.templates = new TemplatesResource(client)
    this.renders = new RendersResource(client)
  }
}

class AccountResource {
  constructor(private readonly client: Client<paths>) {}

  /** The project, workspace and scopes of the API key in use. */
  get(): Promise<Account> {
    return unwrap(this.client.GET('/v1/me'))
  }
}

class TemplatesResource {
  constructor(private readonly client: Client<paths>) {}

  /** One page of templates, most recently updated first. */
  list(params: ListTemplatesParams = {}): Promise<TemplatePage> {
    return unwrap(this.client.GET('/v1/templates', { params: { query: params } }))
  }

  /** Iterates every template across pages. */
  async *listAll(params: Omit<ListTemplatesParams, 'page'> = {}): AsyncGenerator<Template> {
    yield* paginate((page) => this.list({ ...params, page }))
  }

  /** A template (by UUID or slug) with its versions and render input contract. */
  get(templateId: string, params: GetTemplateParams = {}): Promise<TemplateDetail> {
    return unwrap(this.client.GET('/v1/templates/{template_id}', { params: { path: { template_id: templateId }, query: params } }))
  }
}

class RendersResource {
  constructor(private readonly client: Client<paths>) {}

  /** Queues a render. Resolves with the queued job, not the PDF. */
  create(request: RenderRequest): Promise<RenderQueued> {
    return unwrap(this.client.POST('/v1/pdf/render', { body: request }))
  }

  /** Current status of a render. */
  get(renderId: string): Promise<RenderStatus> {
    return unwrap(this.client.GET('/v1/renders/{render_id}', { params: { path: { render_id: renderId } } }))
  }

  /** One page of the render log, newest first. */
  list(params: ListRendersParams = {}): Promise<RenderPage> {
    return unwrap(this.client.GET('/v1/renders', { params: { query: params } }))
  }

  /** Iterates every render across pages. */
  async *listAll(params: Omit<ListRendersParams, 'page'> = {}): AsyncGenerator<Render> {
    yield* paginate((page) => this.list({ ...params, page }))
  }

  /** Downloads the PDF of a successful render. */
  async download(renderId: string): Promise<RenderFile> {
    const { data, response } = await unwrapWithResponse(
      this.client.GET('/v1/renders/{render_id}/download', {
        params: { path: { render_id: renderId } },
        parseAs: 'arrayBuffer',
      }),
    )
    return {
      bytes: new Uint8Array(data as ArrayBuffer),
      contentType: response.headers.get('content-type') ?? 'application/pdf',
      filename: filenameFromDisposition(response.headers.get('content-disposition')),
    }
  }

  /**
   * Polls a render until it is terminal. Resolves on `success`; rejects with
   * RenderFailedError on `failed`/`quota_exceeded` and RenderTimeoutError
   * when the deadline passes.
   */
  async waitFor(renderId: string, options: WaitOptions = {}): Promise<RenderStatus> {
    const pollIntervalMs = options.pollIntervalMs ?? 1_000
    const started = Date.now()
    const deadline = started + (options.timeoutMs ?? 120_000)
    const notFoundUntil = started + (options.notFoundGraceMs ?? 15_000)
    let last: RenderStatus | undefined
    for (;;) {
      options.signal?.throwIfAborted()
      try {
        last = await this.get(renderId)
        if (last.status === 'success') return last
        if (last.status === 'failed' || last.status === 'quota_exceeded') throw new RenderFailedError(last)
      } catch (error) {
        const transitional = error instanceof APIError && error.status === 404 && last === undefined && Date.now() < notFoundUntil
        if (!transitional) throw error
      }
      const remaining = deadline - Date.now()
      if (remaining <= 0) throw new RenderTimeoutError(renderId, last)
      await sleep(Math.min(pollIntervalMs, remaining), options.signal)
    }
  }

  /** Queues a render and waits for it to finish (see waitFor). */
  async createAndWait(request: RenderRequest, options: WaitOptions = {}): Promise<RenderStatus> {
    const queued = await this.create(request)
    return this.waitFor(queued.render_id, options)
  }
}

async function unwrap<T>(request: FetchResult<T>): Promise<T> {
  return (await unwrapWithResponse(request)).data
}

async function unwrapWithResponse<T>(request: FetchResult<T>): Promise<{ data: T; response: Response }> {
  const { data, error, response } = await request
  if (!response.ok) throw APIError.from(response, error)
  return { data: data as T, response }
}

async function* paginate<T>(fetchPage: (page: number) => Promise<{ data: T[]; has_more: boolean }>): AsyncGenerator<T> {
  for (let page = 1; ; page++) {
    const result = await fetchPage(page)
    yield* result.data
    if (!result.has_more) return
  }
}

/** Extracts filename / filename* from a Content-Disposition header. */
export function filenameFromDisposition(header: string | null): string | null {
  if (!header) return null
  const extended = /filename\*\s*=\s*(?:UTF-8|utf-8)''([^;]+)/.exec(header)
  if (extended) {
    try {
      return decodeURIComponent(extended[1].trim())
    } catch {
      return extended[1].trim()
    }
  }
  const plain = /filename\s*=\s*"([^"]*)"|filename\s*=\s*([^;]+)/.exec(header)
  if (!plain) return null
  return (plain[1] ?? plain[2]).trim()
}
