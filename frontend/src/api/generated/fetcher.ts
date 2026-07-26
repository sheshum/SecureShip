export async function customFetcher<T>(url: string, options: RequestInit): Promise<T> {
  const method = options.method ?? 'GET'
  const isSessionRequest = url.includes('/api/sessions')
  const debugEnabled = import.meta.env.DEV && isSessionRequest
  const startedAt = Date.now()

  if (debugEnabled) {
    console.info('[chat-sessions-fetcher] request started', {
      method,
      url,
    })
  }

  let response: Response
  try {
    response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(options.headers ?? {}),
      },
    })
  } catch (error) {
    if (debugEnabled) {
      const isAbortError = error instanceof DOMException && error.name === 'AbortError'
      console.info('[chat-sessions-fetcher] request failed before response', {
        method,
        url,
        durationMs: Date.now() - startedAt,
        isAbortError,
        errorMessage: error instanceof Error ? error.message : null,
      })
    }
    throw error
  }

  if (debugEnabled) {
    console.info('[chat-sessions-fetcher] response received', {
      method,
      url,
      status: response.status,
      durationMs: Date.now() - startedAt,
    })
  }

  if (!response.ok) {
    const text = await response.text()
    throw new Error(text || `HTTP ${response.status}`)
  }

  return (await response.json()) as T
}
