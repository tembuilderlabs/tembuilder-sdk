import { describe, expect, it } from 'vitest'

import { APIError, type Tembuilder } from '../src/index.js'
import { client, fakeFetch, loadJSON } from './helpers.js'

interface ContractCase {
  name: string
  operation: string
  args: Record<string, any>
  request: { method: string; path: string; query: Record<string, string>; body: unknown }
  response: { status: number; headers: Record<string, string>; body?: unknown; text?: string; bodyBase64?: string }
  expect: { result?: unknown; error?: { status: number; code: string }; file?: { base64: string; filename: string; content_type: string } }
}

const suite = loadJSON<{ api_key: string; cases: ContractCase[] }>('cases.json')

function call(sdk: Tembuilder, operation: string, args: Record<string, any>): Promise<unknown> {
  switch (operation) {
    case 'getAccount':
      return sdk.account.get()
    case 'listTemplates':
      return sdk.templates.list(args)
    case 'getTemplate': {
      const { template_id, ...query } = args
      return sdk.templates.get(template_id, query)
    }
    case 'createRender':
      return sdk.renders.create(args.request)
    case 'listRenders':
      return sdk.renders.list(args)
    case 'getRender':
      return sdk.renders.get(args.render_id)
    case 'downloadRender':
      return sdk.renders.download(args.render_id)
    default:
      throw new Error(`unknown contract operation ${operation}`)
  }
}

function stubResponse(response: ContractCase['response']): Response {
  const body =
    response.bodyBase64 !== undefined
      ? Buffer.from(response.bodyBase64, 'base64')
      : response.text !== undefined
        ? response.text
        : JSON.stringify(response.body)
  return new Response(body, { status: response.status, headers: response.headers })
}

describe('shared HTTP contract', () => {
  it.each(suite.cases.map((c) => [c.name, c] as const))('%s', async (_name, testCase) => {
    const { fetch, requests } = fakeFetch(() => stubResponse(testCase.response))
    const sdk = client(fetch, { apiKey: suite.api_key })

    const outcome = await call(sdk, testCase.operation, testCase.args).then(
      (value) => ({ value }),
      (error: unknown) => ({ error }),
    )

    expect(requests).toHaveLength(1)
    const sent = requests[0]
    const url = new URL(sent.url)
    expect(sent.method).toBe(testCase.request.method)
    expect(url.pathname).toBe(testCase.request.path)
    expect(Object.fromEntries(url.searchParams)).toEqual(testCase.request.query)
    expect(sent.headers.get('apikey')).toBe(suite.api_key)
    if (testCase.request.body === null) {
      expect(await sent.text()).toBe('')
    } else {
      expect(await sent.json()).toEqual(testCase.request.body)
    }

    if (testCase.expect.error) {
      expect('error' in outcome).toBe(true)
      const error = (outcome as { error: APIError }).error
      expect(error).toBeInstanceOf(APIError)
      expect(error.status).toBe(testCase.expect.error.status)
      expect(error.code).toBe(testCase.expect.error.code)
    } else if (testCase.expect.file) {
      const file = (outcome as { value: { bytes: Uint8Array; filename: string; contentType: string } }).value
      expect(Buffer.from(file.bytes).toString('base64')).toBe(testCase.expect.file.base64)
      expect(file.filename).toBe(testCase.expect.file.filename)
      expect(file.contentType).toBe(testCase.expect.file.content_type)
    } else {
      expect((outcome as { value: unknown }).value).toEqual(testCase.response.body)
    }
  })

  it('rejects an unknown operation in the runner itself', () => {
    expect(() => call(client(fakeFetch().fetch), 'nope', {})).toThrow('unknown contract operation')
  })
})
