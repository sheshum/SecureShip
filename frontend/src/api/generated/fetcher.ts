import { resolveApiUrl } from '../url'

export async function customFetcher<T>(url: string, options: RequestInit): Promise<T> {
  const requestUrl = resolveApiUrl(url)

  let response: Response
  response = await fetch(requestUrl, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers ?? {}),
    },
  })

  if (!response.ok) {
    const text = await response.text()
    throw new Error(text || `HTTP ${response.status}`)
  }

  return (await response.json()) as T
}
