export function getApiErrorMessage(error: unknown): string {
  if (error != null && typeof error === 'object' && 'response' in error) {
    const response = (error as Record<string, unknown>)['response']
    if (response != null && typeof response === 'object' && 'data' in response) {
      const detail = (response as Record<string, unknown>)['data']
      if (detail != null && typeof detail === 'object' && 'detail' in detail) {
        const msg = (detail as Record<string, unknown>)['detail']
        if (typeof msg === 'string' || typeof msg === 'number') return String(msg)
      }
    }
  }
  return error instanceof Error ? error.message : 'Something went wrong'
}
