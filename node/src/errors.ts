import type { RenderStatus } from './types.js'

/** Base class of every error thrown by the SDK. */
export class TembuilderError extends Error {
  constructor(message: string, options?: { cause?: unknown }) {
    super(message, options)
    this.name = new.target.name
  }
}

/**
 * The API answered with a non-2xx status. Branch on `code` (stable, e.g.
 * `TEMPLATE_NOT_FOUND`); `description` is human-readable.
 */
export class APIError extends TembuilderError {
  readonly status: number
  readonly code: string
  readonly description: string
  readonly details: string[]
  /** Seconds from a `Retry-After` header, when the API sent one. */
  readonly retryAfterSeconds: number | undefined

  constructor(init: { status: number; code: string; description: string; details?: string[]; retryAfterSeconds?: number }) {
    super(`${init.code} (HTTP ${init.status}): ${init.description}`)
    this.status = init.status
    this.code = init.code
    this.description = init.description
    this.details = init.details ?? []
    this.retryAfterSeconds = init.retryAfterSeconds
  }

  /**
   * Builds an APIError from a response and its already-read body. Bodies that
   * are not the standard `{code, description, details}` shape (for example a
   * gateway error page) still yield a usable error with an `HTTP_<status>` code.
   */
  static from(response: Response, body: unknown): APIError {
    const retryAfter = parseRetryAfter(response.headers.get('retry-after'))
    if (isErrorBody(body)) {
      return new APIError({
        status: response.status,
        code: body.code,
        description: body.description,
        details: Array.isArray(body.details) ? body.details.map(String) : [],
        retryAfterSeconds: retryAfter,
      })
    }
    const text = typeof body === 'string' && body.trim() !== '' ? body.trim() : response.statusText || 'request failed'
    return new APIError({ status: response.status, code: `HTTP_${response.status}`, description: text, retryAfterSeconds: retryAfter })
  }
}

/** The request never produced a response (DNS, TLS, connection reset...). */
export class ConnectionError extends TembuilderError {}

/** A single HTTP attempt exceeded the configured `timeoutMs`. */
export class TimeoutError extends TembuilderError {}

/** A render reached the terminal `failed` or `quota_exceeded` status. */
export class RenderFailedError extends TembuilderError {
  readonly render: RenderStatus

  constructor(render: RenderStatus) {
    super(`render ${render.render_id} ended with status ${render.status}${render.error_message ? `: ${render.error_message}` : ''}`)
    this.render = render
  }
}

/** A render was still not terminal when the wait deadline passed. */
export class RenderTimeoutError extends TembuilderError {
  readonly renderId: string
  /** Last status observed, if any status response was received. */
  readonly lastStatus: RenderStatus | undefined

  constructor(renderId: string, lastStatus: RenderStatus | undefined) {
    super(`render ${renderId} did not finish before the deadline (last status: ${lastStatus?.status ?? 'unknown'})`)
    this.renderId = renderId
    this.lastStatus = lastStatus
  }
}

/** A webhook request failed signature, timestamp or payload verification. */
export class WebhookVerificationError extends TembuilderError {}

function isErrorBody(body: unknown): body is { code: string; description: string; details?: unknown[] } {
  if (typeof body !== 'object' || body === null) return false
  const candidate = body as Record<string, unknown>
  return typeof candidate.code === 'string' && typeof candidate.description === 'string'
}

/** Parses a delta-seconds Retry-After value; HTTP-dates are ignored. */
export function parseRetryAfter(value: string | null): number | undefined {
  if (value === null || !/^\d+$/.test(value.trim())) return undefined
  return Number(value.trim())
}
