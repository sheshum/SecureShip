const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, '') ?? ''

export function resolveApiUrl(url: string): string {
  if (/^https?:\/\//.test(url)) {
    return url
  }

  if (!apiBaseUrl) {
    return url
  }

  return `${apiBaseUrl}${url}`
}
