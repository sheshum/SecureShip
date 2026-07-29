import type { ChatRequest } from './generated/schemas'
import { resolveApiUrl } from './url'

export type ChatContinueRequest = {
  session_id: string
  pending_turn_id: string
}

export type ChatSseEvent =
  | { type: 'session'; session_id: string }
  | { type: 'auth_state'; state: string; auth_expires_at?: string }
  | {
      type: 'auth_required'
      message: string
      pending_turn_id?: string | null
      cta?: {
        label?: string
        action?: string
      }
    }
  | { type: 'show_code_modal'; open: boolean }
  | { type: 'token'; content: string }
  | { type: 'tool_call'; [key: string]: unknown }
  | { type: 'tool_result'; [key: string]: unknown }
  | { type: 'error'; message: string }
  | { type: 'done' }

export type ChatStreamHandlers = {
  onEvent?: (event: ChatSseEvent) => void
  onSession?: (sessionId: string) => void
  onAuthState?: (event: Extract<ChatSseEvent, { type: 'auth_state' }>) => void
  onAuthRequired?: (event: Extract<ChatSseEvent, { type: 'auth_required' }>) => void
  onShowCodeModal?: (event: Extract<ChatSseEvent, { type: 'show_code_modal' }>) => void
  onToken?: (content: string) => void
  onToolCall?: (event: Extract<ChatSseEvent, { type: 'tool_call' }>) => void
  onToolResult?: (event: Extract<ChatSseEvent, { type: 'tool_result' }>) => void
  onError?: (message: string) => void
  onDone?: () => void
}

const DATA_PREFIX = 'data:'

function safeJsonParse(raw: string): ChatSseEvent | null {
  try {
    return JSON.parse(raw) as ChatSseEvent
  } catch {
    return null
  }
}

function dispatchEvent(event: ChatSseEvent, handlers: ChatStreamHandlers) {
  handlers.onEvent?.(event)

  switch (event.type) {
    case 'session':
      handlers.onSession?.(event.session_id)
      break
    case 'auth_state':
      handlers.onAuthState?.(event)
      break
    case 'auth_required':
      handlers.onAuthRequired?.(event)
      break
    case 'show_code_modal':
      handlers.onShowCodeModal?.(event)
      break
    case 'token':
      handlers.onToken?.(event.content)
      break
    case 'tool_call':
      handlers.onToolCall?.(event)
      break
    case 'tool_result':
      handlers.onToolResult?.(event)
      break
    case 'error':
      handlers.onError?.(event.message)
      break
    case 'done':
      handlers.onDone?.()
      break
  }
}

export async function streamChat(
  payload: ChatRequest,
  handlers: ChatStreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch(resolveApiUrl('/api/chat'), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
    signal,
  })

  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `Chat request failed: HTTP ${response.status}`)
  }

  const contentType = response.headers.get('content-type') ?? ''
  if (!contentType.includes('text/event-stream')) {
    throw new Error(`Unexpected response content-type: ${contentType}`)
  }

  if (!response.body) {
    throw new Error('Response body stream is empty')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()

    if (done) {
      break
    }

    buffer += decoder.decode(value, { stream: true })

    const frames = buffer.split('\n\n')
    buffer = frames.pop() ?? ''

    for (const frame of frames) {
      for (const line of frame.split('\n')) {
        if (!line.startsWith(DATA_PREFIX)) {
          continue
        }

        const raw = line.slice(DATA_PREFIX.length).trim()
        const event = safeJsonParse(raw)
        if (!event) {
          continue
        }

        dispatchEvent(event, handlers)
      }
    }
  }

  if (buffer.trim()) {
    for (const line of buffer.split('\n')) {
      if (!line.startsWith(DATA_PREFIX)) {
        continue
      }

      const raw = line.slice(DATA_PREFIX.length).trim()
      const event = safeJsonParse(raw)
      if (!event) {
        continue
      }

      dispatchEvent(event, handlers)
    }
  }
}

export async function streamPendingChat(
  payload: ChatContinueRequest,
  handlers: ChatStreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch(resolveApiUrl('/api/chat/continue'), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
    signal,
  })

  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `Chat continuation failed: HTTP ${response.status}`)
  }

  const contentType = response.headers.get('content-type') ?? ''
  if (!contentType.includes('text/event-stream')) {
    throw new Error(`Unexpected response content-type: ${contentType}`)
  }

  if (!response.body) {
    throw new Error('Response body stream is empty')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()

    if (done) {
      break
    }

    buffer += decoder.decode(value, { stream: true })

    const frames = buffer.split('\n\n')
    buffer = frames.pop() ?? ''

    for (const frame of frames) {
      for (const line of frame.split('\n')) {
        if (!line.startsWith(DATA_PREFIX)) {
          continue
        }

        const raw = line.slice(DATA_PREFIX.length).trim()
        const event = safeJsonParse(raw)
        if (!event) {
          continue
        }

        dispatchEvent(event, handlers)
      }
    }
  }

  if (buffer.trim()) {
    for (const line of buffer.split('\n')) {
      if (!line.startsWith(DATA_PREFIX)) {
        continue
      }

      const raw = line.slice(DATA_PREFIX.length).trim()
      const event = safeJsonParse(raw)
      if (!event) {
        continue
      }

      dispatchEvent(event, handlers)
    }
  }
}
