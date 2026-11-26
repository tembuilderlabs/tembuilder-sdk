import { createHmac } from 'node:crypto'

import { describe, expect, it } from 'vitest'

import { WebhookVerificationError, verifyWebhook } from '../src/index.js'
import { loadJSON } from './helpers.js'

interface Vector {
  name: string
  timestamp: string | null
  signature: string | null
  body: string
  now: number
  valid: boolean
}

const suite = loadJSON<{ secret: string; tolerance_seconds: number; vectors: Vector[] }>('webhooks.json')

function headersFor(vector: Vector): Record<string, string | undefined> {
  return {
    'Tembuilder-Timestamp': vector.timestamp ?? undefined,
    'Tembuilder-Signature': vector.signature ?? undefined,
    'Content-Type': 'application/json',
  }
}

describe('verifyWebhook shared vectors', () => {
  it.each(suite.vectors.map((v) => [v.name, v] as const))('%s', (_name, vector) => {
    const verify = () =>
      verifyWebhook({
        payload: vector.body,
        headers: headersFor(vector),
        secret: suite.secret,
        toleranceSeconds: suite.tolerance_seconds,
        now: new Date(vector.now * 1000),
      })
    if (vector.valid) {
      expect(verify()).toEqual(JSON.parse(vector.body))
    } else {
      expect(verify).toThrow(WebhookVerificationError)
    }
  })
})

describe('verifyWebhook inputs', () => {
  const valid = suite.vectors[0]

  it('accepts Fetch Headers and a Uint8Array body', () => {
    const event = verifyWebhook({
      payload: new TextEncoder().encode(valid.body),
      headers: new Headers({ 'tembuilder-timestamp': valid.timestamp!, 'tembuilder-signature': valid.signature! }),
      secret: suite.secret,
      now: new Date(valid.now * 1000),
    })
    expect(event.type).toBe('renders.status')
  })

  it('accepts Node array header values', () => {
    const event = verifyWebhook({
      payload: valid.body,
      headers: { 'tembuilder-timestamp': valid.timestamp!, 'tembuilder-signature': [valid.signature!] },
      secret: suite.secret,
      now: new Date(valid.now * 1000),
    })
    expect(event.api_version).toBe('2026-09-12')
  })

  it('uses the current time and default tolerance', () => {
    const now = Math.floor(Date.now() / 1000).toString()
    const key = Buffer.from(suite.secret, 'base64url')
    const body = '{"api_version":"2026-09-12","type":"webhook.test","data":{"message":"hi"}}'
    const signature = 'v1=' + createHmac('sha256', key).update(`${now}.${body}`).digest('hex')
    const event = verifyWebhook({ payload: body, headers: { 'tembuilder-timestamp': now, 'tembuilder-signature': signature }, secret: suite.secret })
    expect(event).toEqual({ api_version: '2026-09-12', type: 'webhook.test', data: { message: 'hi' } })
  })

  it('rejects a request without Tembuilder headers', () => {
    expect(() => verifyWebhook({ payload: valid.body, headers: {}, secret: suite.secret })).toThrow('missing Tembuilder-Timestamp')
    expect(() => verifyWebhook({ payload: valid.body, headers: new Headers(), secret: suite.secret })).toThrow('missing Tembuilder-Timestamp')
  })

  it('rejects an empty secret', () => {
    expect(() =>
      verifyWebhook({ payload: valid.body, headers: headersFor(valid), secret: '', now: new Date(valid.now * 1000) }),
    ).toThrow('secret is empty')
  })
})
