import { resolveApiUrl } from '../url'
import { getAccessToken } from '../authToken'

// keyed by request url so in-flight requests can be cancelled from outside the fetcher
const pendingRequests = new Map<string, AbortController>()

export function cancelRequest(url: string): boolean {
  const controller = pendingRequests.get(url)
  if (!controller) return false
  controller.abort()
  return true
}

export async function customFetcher<T>(url: string, options: RequestInit = {}): Promise<T> {
  const requestUrl = resolveApiUrl(url)
  const token = await getAccessToken()

  const controller = new AbortController()
  options.signal?.addEventListener('abort', () => controller.abort(), { once: true })
  pendingRequests.set(url, controller)

  let response: Response
  try {
    response = await fetch(requestUrl, {
      ...options,
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(options.headers ?? {}),
      },
    })
  } finally {
    if (pendingRequests.get(url) === controller) pendingRequests.delete(url)
  }

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
