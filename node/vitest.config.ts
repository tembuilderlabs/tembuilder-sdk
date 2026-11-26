import { defineConfig } from 'vitest/config'

// Coverage is enforced at 100% for hand-written code. Generated code
// (src/generated) is excluded: it is verified by drift and contract checks.
export default defineConfig({
  test: {
    include: ['test/**/*.test.ts'],
    exclude: ['test/conformance/**'],
    coverage: {
      provider: 'v8',
      include: ['src/**/*.ts'],
      exclude: ['src/generated/**'],
      thresholds: { lines: 100, functions: 100, branches: 100, statements: 100 },
      reporter: ['text', 'lcov'],
    },
  },
})
