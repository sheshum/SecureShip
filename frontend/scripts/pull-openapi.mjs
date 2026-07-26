import { mkdir, writeFile } from 'node:fs/promises'

const OPENAPI_URL = process.env.OPENAPI_URL ?? 'http://localhost:8000/openapi.json'
const outputUrl = new URL('../src/api/openapi.json', import.meta.url)
const outputDirUrl = new URL('../src/api/', import.meta.url)

const response = await fetch(OPENAPI_URL)

if (!response.ok) {
  throw new Error(`Failed to fetch OpenAPI: ${response.status} ${response.statusText}`)
}

await mkdir(outputDirUrl, { recursive: true })
await writeFile(outputUrl, await response.text(), 'utf8')
console.log(`OpenAPI saved to ${outputUrl.pathname}`)
