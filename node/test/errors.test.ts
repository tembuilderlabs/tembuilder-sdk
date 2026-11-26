import { describe, expect, it } from 'vitest'

import { APIError, RenderFailedError, RenderTimeoutError, TembuilderError } from '../src/index.js'
import { parseRetryAfter } from '../src/errors.js'

describe('APIError.from', () => {
  it('reads the standard error body and Retry-After', () => {
    const error = APIError.from(new Response(null, { status: 503, headers: { 'retry-after': '2' } }), {
      code: 'COMMON_UNAVAILABLE',
      description: 'busy',
      details: ['a', 3],
    })
    expect(error).toMatchObject({ status: 503, code: 'COMMON_UNAVAILABLE', description: 'busy', details: ['a', '3'], retryAfterSeconds: 2 })
    expect(error.message).toBe('COMMON_UNAVAILABLE (HTTP 503): busy')
    expect(error).toBeInstanceOf(TembuilderError)
    expect(error.name).toBe('APIError')
  })

  it('tolerates a missing details array', () => {
    expect(APIError.from(new Response(null, { status: 400 }), { code: 'X', description: 'y' }).details).toEqual([])
  })

  it('uses a text body for non-standard errors', () => {
    const error = APIError.from(new Response(null, { status: 502 }), '  bad gateway  ')
    expect(error).toMatchObject({ code: 'HTTP_502', description: 'bad gateway', retryAfterSeconds: undefined })
  })

  it('falls back to the status text, then a generic description', () => {
    expect(APIError.from(new Response(null, { status: 500, statusText: 'Internal' }), '').description).toBe('Internal')
    expect(APIError.from(new Response(null, { status: 500 }), null).description).toBe('request failed')
    expect(APIError.from(new Response(null, { status: 500 }), { message: 'x' }).code).toBe('HTTP_500')
  })
})

describe('parseRetryAfter', () => {
  it.each([
    [null, undefined],
    ['7', 7],
    [' 3 ', 3],
    ['Wed, 21 Oct 2015 07:28:00 GMT', undefined],
    ['-1', undefined],
  ])('%s -> %s', (value, expected) => {
    expect(parseRetryAfter(value)).toBe(expected)
  })
})

describe('render errors', () => {
  it('describe failures with and without a message', () => {
    expect(new RenderFailedError({ render_id: 'r', status: 'failed', error_message: 'bad' }).message).toBe('render r ended with status failed: bad')
    expect(new RenderFailedError({ render_id: 'r', status: 'quota_exceeded' }).message).toBe('render r ended with status quota_exceeded')
    expect(new RenderTimeoutError('r', undefined).lastStatus).toBeUndefined()
  })
})
