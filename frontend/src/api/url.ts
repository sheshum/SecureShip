const LOOPBACK_HOSTS = new Set(['localhost', '127.0.0.1', '[::1]'])

function normalizeLoopbackBaseUrl(baseUrl: string): string {
  try {
    const parsed = new URL(baseUrl)

    if (!LOOPBACK_HOSTS.has(parsed.hostname)) {
      return baseUrl
    }

    if (typeof window === 'undefined') {
      return baseUrl
    }

    const browserHost = window.location.hostname
    if (!LOOPBACK_HOSTS.has(browserHost) || parsed.hostname === browserHost) {
      return baseUrl
    }

    parsed.hostname = browserHost
    return parsed.toString()
  } catch {
    return baseUrl
  }
}

const rawApiBaseUrl = import.meta.env.VITE_API_BASE_URL
const apiBaseUrl =
  typeof rawApiBaseUrl === 'string'
    ? normalizeLoopbackBaseUrl(rawApiBaseUrl).replace(/\/$/, '')
    : ''

export function resolveApiUrl(url: string): string {
  if (/^https?:\/\//.test(url)) {
    return url
  }

  if (!apiBaseUrl) {
    return url
  }

  return `${apiBaseUrl}${url}`
}
