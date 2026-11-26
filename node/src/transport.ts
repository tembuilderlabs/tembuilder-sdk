import { ConnectionError, TimeoutError, parseRetryAfter } from './errors.js'

export interface RetryPolicy {
  /** Retries after the first attempt. 0 disables retries. */
  maxRetries: number
  /** Base of the exponential backoff, in milliseconds. */
  baseDelayMs: number
  /** Upper bound of any single wait, including a server Retry-After. */
  maxDelayMs: number
}

export interface TransportOptions {
  fetch: typeof globalThis.fetch
  timeoutMs: number
  retry: RetryPolicy
  random?: () => number
}

// Statuses that mean the request was not processed and can be resent. A POST
// is only resent on these: the render endpoint answers 503 before admitting a
// job and 429 comes from rate limiting in front of it. A POST that failed
// without any response is never resent, because it may have been accepted.
const RETRYABLE_STATUSES = new Set([429, 503])
// GETs are safe to resend after any transient failure.
const RETRYABLE_GET_STATUSES = new Set([429, 502, 503, 504])

/**
 * Wraps fetch with a per-attempt timeout and bounded, jittered retries. Each
 * attempt sends a clone of the request so a body can be resent.
 */
export function createTransport(options: TransportOptions): (request: Request) => Promise<Response> {
  const random = options.random ?? Math.random
  return async (request: Request) => {
    const idempotent = request.method === 'GET' || request.method === 'HEAD'
    for (let attempt = 0; ; attempt++) {
      const canRetry = attempt < options.retry.maxRetries
      let response: Response
      try {
        response = await attemptOnce(options, request)
      } catch (error) {
        if (canRetry && idempotent && (error instanceof ConnectionError || error instanceof TimeoutError)) {
          await sleep(backoff(options.retry, attempt, undefined, random), request.signal)
          continue
        }
        throw error
      }
      const retryable = idempotent ? RETRYABLE_GET_STATUSES : RETRYABLE_STATUSES
      if (canRetry && retryable.has(response.status)) {
        const retryAfter = parseRetryAfter(response.headers.get('retry-after'))
        await response.body?.cancel()
        await sleep(backoff(options.retry, attempt, retryAfter, random), request.signal)
        continue
      }
      return response
    }
  }
}

async function attemptOnce(options: TransportOptions, request: Request): Promise<Response> {
  const timeout = AbortSignal.timeout(options.timeoutMs)
  const attempt = new Request(request.clone(), { signal: AbortSignal.any([request.signal, timeout]) })
  try {
    return await options.fetch(attempt)
  } catch (error) {
    if (request.signal.aborted) throw request.signal.reason
    if (timeout.aborted) throw new TimeoutError(`request timed out after ${options.timeoutMs}ms`, { cause: error })
    throw new ConnectionError(`request to ${request.url} failed: ${(error as Error).message}`, { cause: error })
  }
}

/** Server Retry-After wins; otherwise exponential backoff with full jitter. */
export function backoff(policy: RetryPolicy, attempt: number, retryAfterSeconds: number | undefined, random: () => number): number {
  if (retryAfterSeconds !== undefined) return Math.min(retryAfterSeconds * 1000, policy.maxDelayMs)
  const ceiling = Math.min(policy.baseDelayMs * 2 ** attempt, policy.maxDelayMs)
  return Math.floor(random() * ceiling)
}

/** Resolves after `ms`, or rejects with the signal's reason when aborted. */
export function sleep(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) {
      reject(signal.reason)
      return
    }
    const timer = setTimeout(() => {
      signal?.removeEventListener('abort', onAbort)
      resolve()
    }, ms)
    const onAbort = () => {
      clearTimeout(timer)
      reject(signal?.reason)
    }
    signal?.addEventListener('abort', onAbort, { once: true })
  })
}
