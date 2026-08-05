import { resolveApiUrl } from '../url'
import { getAccessToken } from '../authToken'

export async function customFetcher<T>(url: string, options: RequestInit): Promise<T> {
  const requestUrl = resolveApiUrl(url)
  const token = await getAccessToken()

  let response: Response
  response = await fetch(requestUrl, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers ?? {}),
    },
  })

  if (!response.ok) {
    const text = await response.text()
    let message = text || `HTTP ${response.status}`
    try {
      const parsed = JSON.parse(text)
      if (typeof parsed?.detail === 'string') {
        message = parsed.detail
      }
    } catch {
      // response body wasn't JSON; fall back to raw text
    }
    throw new Error(message)
  }

  const data = response.status === 204 ? undefined : await response.json()

  // Wrap in Orval-expected format for mutations
  return {
    data,
    status: response.status,
    headers: response.headers,
  } as T
}
