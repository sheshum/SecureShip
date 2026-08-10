const rawApiBaseUrl = import.meta.env.VITE_API_BASE_URL
const apiBaseUrl = typeof rawApiBaseUrl === 'string' ? rawApiBaseUrl.replace(/\/$/, '') : ''

export function resolveApiUrl(url: string): string {
  if (/^https?:\/\//.test(url)) {
    return url
  }

  if (!apiBaseUrl) {
    return url
  }

  return `${apiBaseUrl}${url}`
}
