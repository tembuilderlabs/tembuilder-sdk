// A fresh consumer app: e2e/run.sh installs @tembuilder/sdk into an empty
// project (from the packed tarball or from npm) and runs this file, so it
// proves the package as users get it: exports, version, webhooks and, with
// TEMBUILDER_API_KEY/TEMBUILDER_BASE_URL/TEMBUILDER_SMOKE_TEMPLATE, a real render.
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

import { APIError, Tembuilder, VERSION, verifyWebhook } from '@tembuilder/sdk'

const step = (name) => console.log(`- ${name}`)

step(`installed version ${VERSION}`)
if (process.env.EXPECTED_VERSION) assert.equal(VERSION, process.env.EXPECTED_VERSION)

step('CommonJS entry point')
const { createRequire } = await import('node:module')
assert.equal(createRequire(import.meta.url)('@tembuilder/sdk').VERSION, VERSION)

step('webhook signature vectors')
const contract = JSON.parse(readFileSync(process.env.WEBHOOK_VECTORS, 'utf8'))
for (const vector of contract.vectors) {
  const verify = () =>
    verifyWebhook({
      payload: vector.body,
      headers: { 'tembuilder-timestamp': vector.timestamp, 'tembuilder-signature': vector.signature },
      secret: contract.secret,
      now: new Date(vector.now * 1000),
    })
  if (vector.valid) assert.equal(verify().type !== undefined, true, vector.name)
  else assert.throws(verify, vector.name)
}

const live = ['TEMBUILDER_API_KEY', 'TEMBUILDER_BASE_URL', 'TEMBUILDER_SMOKE_TEMPLATE'].every((name) => process.env[name])
if (!live) {
  assert.ok(process.env.REQUIRE_LIVE !== '1', 'REQUIRE_LIVE=1 but the live environment is not set')
  console.log('live API: skipped (TEMBUILDER_API_KEY, TEMBUILDER_BASE_URL, TEMBUILDER_SMOKE_TEMPLATE not set)')
  console.log('node e2e ok')
  process.exit(0)
}

const client = new Tembuilder()

step('account')
assert.ok((await client.account.get()).project.id)

step('template detail and input contract')
const template = await client.templates.get(process.env.TEMBUILDER_SMOKE_TEMPLATE)
assert.ok(template.published_versions.length > 0, 'smoke template has no published version')
const version = template.published_versions.at(-1)
const detail = await client.templates.get(template.id, { version })
assert.equal(detail.input.version, version)

step('template list contains it')
const listed = []
for await (const item of client.templates.listAll({ search: template.slug })) listed.push(item.id)
assert.ok(listed.includes(template.id))

step('render, wait and download')
const status = await client.renders.createAndWait(
  { template_id: template.id, version, parameters: detail.input.example_parameters },
  { timeoutMs: 180_000, pollIntervalMs: 2_000 },
)
const file = await client.renders.download(status.render_id)
assert.equal(new TextDecoder().decode(file.bytes.slice(0, 5)), '%PDF-')

step('render log contains it')
const page = await client.renders.list({ template_id: template.id, per_page: 20 })
assert.ok(page.data.some((render) => render.id === status.render_id))

step('typed errors: unknown template is 404, bad key is 401')
await assert.rejects(client.templates.get('e2e-template-that-does-not-exist'), (error) => error instanceof APIError && error.status === 404)
await assert.rejects(
  new Tembuilder({ apiKey: 'invalid' }).account.get(),
  (error) => error instanceof APIError && error.status === 401 && error.code === 'COMMON_UNAUTHENTICATED',
)

console.log('node e2e ok (live)')
