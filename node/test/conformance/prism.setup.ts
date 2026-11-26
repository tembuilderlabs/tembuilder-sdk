import { spawn, type ChildProcess } from 'node:child_process'
import { fileURLToPath } from 'node:url'

const root = fileURLToPath(new URL('../../../', import.meta.url))
export const PRISM_PORT = 4010

let prism: ChildProcess | undefined

export async function setup(): Promise<void> {
  prism = spawn('pnpm', ['exec', 'prism', 'mock', '--errors', '--port', String(PRISM_PORT), 'openapi/tembuilder.yaml'], {
    cwd: root,
    stdio: ['ignore', 'pipe', 'pipe'],
  })
  const deadline = Date.now() + 45_000
  while (Date.now() < deadline) {
    try {
      await fetch(`http://127.0.0.1:${PRISM_PORT}/v1/me`, { headers: { ApiKey: 'probe' } })
      return
    } catch {
      await new Promise((resolve) => setTimeout(resolve, 250))
    }
  }
  throw new Error('Prism mock did not start')
}

export async function teardown(): Promise<void> {
  prism?.kill('SIGTERM')
}
