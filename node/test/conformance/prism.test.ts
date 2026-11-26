import { describe, expect, it } from 'vitest'

import { APIError, Tembuilder } from '../../src/index.js'
import { PRISM_PORT } from './prism.setup.js'

const sdk = new Tembuilder({ apiKey: 'conformance-key', baseUrl: `http://127.0.0.1:${PRISM_PORT}`, maxRetries: 0 })
const TEMPLATE = '7d0f5a2e-1c3b-4d5e-9f80-a1b2c3d4e5f6'

// Prism answers 422 with a validation report when a request breaks the spec;
// every call below must instead get the documented success response.
async function conforms<T>(call: Promise<T>): Promise<T> {
  try {
    return await call
  } catch (error) {
    if (error instanceof APIError) throw new Error(`spec violation: ${error.status} ${error.description}`)
    throw error
  }
}

describe('SDK requests conform to openapi/tembuilder.yaml', () => {
  it('getAccount', async () => {
    expect(await conforms(sdk.account.get())).toHaveProperty('project')
  })

  it('listTemplates with every filter', async () => {
    const page = await conforms(sdk.templates.list({ status: 'published', search: 'inv', page: 1, per_page: 10 }))
    expect(page).toHaveProperty('has_more')
  })

  it('getTemplate with a version', async () => {
    expect(await conforms(sdk.templates.get('invoice', { version: 2 }))).toHaveProperty('input')
  })

  it('createRender with a full body', async () => {
    const queued = await conforms(sdk.renders.create({ template_id: TEMPLATE, version: 1, variant: 'base', parameters: { customer: 'Acme' } }))
    expect(queued.status).toBe('queued')
  })

  it('listRenders with every filter', async () => {
    const page = await conforms(
      sdk.renders.list({ status: 'success', template_id: TEMPLATE, started_after: '2026-11-01T00:00:00Z', started_before: '2026-11-30T00:00:00Z', page: 1, per_page: 5 }),
    )
    expect(page).toHaveProperty('data')
  })

  it('getRender', async () => {
    expect(await conforms(sdk.renders.get(TEMPLATE))).toHaveProperty('status')
  })

  it('downloadRender', async () => {
    const file = await conforms(sdk.renders.download(TEMPLATE))
    expect(file.bytes).toBeInstanceOf(Uint8Array)
  })

  it('a request that breaks the spec is rejected by the mock', async () => {
    const error = await sdk.renders.create({ template_id: 'not-a-uuid' }).catch((e: unknown) => e)
    expect(error).toBeInstanceOf(APIError)
    // Prism answers with the operation's documented 400 when one exists,
    // otherwise with 422.
    expect([400, 422]).toContain((error as APIError).status)
  })
})
