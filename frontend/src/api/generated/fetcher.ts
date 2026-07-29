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

  const data = await response.json()
  
  // Wrap in Orval-expected format for mutations
  return {
    data,
    status: response.status,
    headers: response.headers,
  } as T
}
