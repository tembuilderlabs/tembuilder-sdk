import { defineConfig } from 'vitest/config'

// Runs the built-in SDK against a Prism mock of openapi/tembuilder.yaml.
// Prism rejects any request that violates the spec, so this proves the SDK
// sends what the contract describes. No coverage gate: unit tests own that.
export default defineConfig({
  test: {
    include: ['test/conformance/**/*.test.ts'],
    globalSetup: ['test/conformance/prism.setup.ts'],
    testTimeout: 30_000,
    hookTimeout: 60_000,
  },
})
