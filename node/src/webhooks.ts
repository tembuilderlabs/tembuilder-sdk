import { createHmac, timingSafeEqual } from 'node:crypto'

import { WebhookVerificationError } from './errors.js'
import type { WebhookEvent } from './types.js'

export const SIGNATURE_HEADER = 'tembuilder-signature'
export const TIMESTAMP_HEADER = 'tembuilder-timestamp'
export const DEFAULT_TOLERANCE_SECONDS = 300

type HeaderBag = Headers | Record<string, string | string[] | undefined>

export interface VerifyWebhookOptions {
  /** The raw request body, exactly as received. Never a re-serialized object. */
  payload: string | Uint8Array
  /** Request headers (Fetch Headers or a Node IncomingHttpHeaders object). */
  headers: HeaderBag
  /** The endpoint's signing secret as shown in the app (unpadded base64url). */
  secret: string
  /** Accepted clock difference. Default 300 s. */
  toleranceSeconds?: number
  /** Override "now", e.g. in tests. */
  now?: Date
}

/**
 * Verifies a webhook request and returns the parsed event.
 *
 * The signature is `v1=` + hex(HMAC-SHA256(secret, `${timestamp}.${rawBody}`)).
 * Throws WebhookVerificationError when a header is missing, the timestamp is
 * outside the tolerance, the signature does not match or the body is not JSON.
 */
export function verifyWebhook(options: VerifyWebhookOptions): WebhookEvent {
  const timestamp = header(options.headers, TIMESTAMP_HEADER)
  const signatures = header(options.headers, SIGNATURE_HEADER)
  if (!timestamp || !signatures) {
    throw new WebhookVerificationError('missing Tembuilder-Timestamp or Tembuilder-Signature header')
  }
  if (!/^\d+$/.test(timestamp)) {
    throw new WebhookVerificationError('Tembuilder-Timestamp is not a unix timestamp')
  }
  const tolerance = options.toleranceSeconds ?? DEFAULT_TOLERANCE_SECONDS
  const nowSeconds = Math.floor((options.now ?? new Date()).getTime() / 1000)
  if (Math.abs(nowSeconds - Number(timestamp)) > tolerance) {
    throw new WebhookVerificationError('webhook timestamp is outside the accepted tolerance')
  }

  const key = Buffer.from(options.secret, 'base64url')
  if (key.length === 0) {
    throw new WebhookVerificationError('webhook secret is empty or not base64url')
  }
  const body = typeof options.payload === 'string' ? Buffer.from(options.payload, 'utf8') : Buffer.from(options.payload)
  const expected = Buffer.from('v1=' + createHmac('sha256', key).update(`${timestamp}.`).update(body).digest('hex'))
  const matches = signatures
    .split(',')
    .map((candidate) => Buffer.from(candidate.trim()))
    .some((candidate) => candidate.length === expected.length && timingSafeEqual(candidate, expected))
  if (!matches) {
    throw new WebhookVerificationError('webhook signature does not match')
  }

  let event: unknown
  try {
    event = JSON.parse(body.toString('utf8'))
  } catch (error) {
    throw new WebhookVerificationError('webhook body is not valid JSON', { cause: error })
  }
  if (typeof event !== 'object' || event === null || Array.isArray(event)) {
    throw new WebhookVerificationError('webhook body is not a JSON object')
  }
  return event as WebhookEvent
}

function header(headers: HeaderBag, name: string): string | undefined {
  if (headers instanceof Headers) return headers.get(name) ?? undefined
  for (const [key, value] of Object.entries(headers)) {
    if (key.toLowerCase() === name) return Array.isArray(value) ? value.join(',') : value
  }
  return undefined
}
