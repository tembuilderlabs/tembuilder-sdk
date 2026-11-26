// Mirrors the README quickstart; typechecked in CI so the docs stay correct.
import { writeFile } from 'node:fs/promises'

import { Tembuilder, verifyWebhook } from '../src/index.js'

export async function quickstart(): Promise<void> {
  const tembuilder = new Tembuilder({ apiKey: process.env.TEMBUILDER_API_KEY })

  const template = await tembuilder.templates.get('invoice')
  console.log(template.input.parameters_schema, template.input.example_parameters)

  const render = await tembuilder.renders.createAndWait({
    template_id: template.id,
    parameters: { ...template.input.example_parameters, customer: 'Acme Corp' },
  })
  const pdf = await tembuilder.renders.download(render.render_id)
  await writeFile(pdf.filename ?? 'output.pdf', pdf.bytes)
}

export function handleWebhook(rawBody: Buffer, headers: Record<string, string | string[] | undefined>): void {
  const event = verifyWebhook({ payload: rawBody, headers, secret: process.env.TEMBUILDER_WEBHOOK_SECRET ?? '' })
  if (event.type === 'renders.status') {
    console.log(event.data.render_id, event.data.status, event.data.output?.download_url)
  }
}
