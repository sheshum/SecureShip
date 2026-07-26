import { defineConfig } from 'orval'

export default defineConfig({
  secureShip: {
    input: {
      target: './src/api/openapi.json',
    },
    output: {
      mode: 'split',
      target: './src/api/generated/client.ts',
      schemas: './src/api/generated/schemas',
      client: 'react-query',
      override: {
        mutator: {
          path: './src/api/generated/fetcher.ts',
          name: 'customFetcher',
        },
      },
    },
  },
})
