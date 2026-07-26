import { useCallback, useEffect, useRef, useState } from 'react'
import { streamChat, type ChatStreamHandlers } from '../../api/chatStream'
import type { ChatRequest } from '../../api/generated/schemas'

export function useChatStream() {
  const abortControllerRef = useRef<AbortController | null>(null)
  const [isStreaming, setIsStreaming] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const cancel = useCallback(() => {
    abortControllerRef.current?.abort()
  }, [])

  const send = useCallback(async (request: ChatRequest, handlers?: ChatStreamHandlers) => {
    abortControllerRef.current?.abort()
    const abortController = new AbortController()
    abortControllerRef.current = abortController
    setIsStreaming(true)
    setError(null)

    try {
      await streamChat(
        request,
        {
          ...handlers,
          onError: (message) => {
            setError(message)
            handlers?.onError?.(message)
          },
        },
        abortController.signal,
      )
    } catch (streamError) {
      if (streamError instanceof DOMException && streamError.name === 'AbortError') {
        return
      }

      const message = streamError instanceof Error ? streamError.message : 'Chat stream failed'
      setError(message)
    } finally {
      if (abortControllerRef.current === abortController) {
        abortControllerRef.current = null
      }
      setIsStreaming(false)
    }
  }, [])

  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort()
    }
  }, [])

  return {
    isStreaming,
    error,
    send,
    cancel,
  }
}
