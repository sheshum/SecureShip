import { useCallback, useEffect, useMemo, useState } from 'react'
import { useCreateSessionApiSessionsPost } from '../../api/generated/client'
import type { CreateSessionApiSessionsPostMutationResult } from '../../api/generated/client'
import type { SessionCreateResponse } from '../../api/generated/schemas'
import { type ChatMessage } from '../../components/ChatMessageList'

type UseChatSessionsOptions = {
  _reserved?: never
}

function unwrapSessionCreate(
  response: CreateSessionApiSessionsPostMutationResult,
): SessionCreateResponse | undefined {
  if ('data' in response && response.data && typeof response.data === 'object' && 'session' in response.data) {
    return response.data as SessionCreateResponse
  }

  if ('session' in response) {
    return response as unknown as SessionCreateResponse
  }

  return undefined
}

export function useChatSessions(_: UseChatSessionsOptions = {}) {
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [sessionError, setSessionError] = useState<string | null>(null)
  const createSessionMutation = useCreateSessionApiSessionsPost()

  const createBackendSession = useCallback(async (): Promise<string | null> => {
    try {
      const response = await createSessionMutation.mutateAsync()
      const normalizedResponse = unwrapSessionCreate(response)
      const createdSessionId = normalizedResponse?.session?.id

      if (!createdSessionId) {
        throw new Error('Session creation returned an unexpected response payload.')
      }

      setSessionId(createdSessionId)
      setSessionError(null)
      return createdSessionId
    } catch (error) {
      const reason = error instanceof Error ? error.message : null
      setSessionError(
        reason
          ? `Unable to start a support session right now: ${reason}`
          : 'Unable to start a support session right now. Please try again.',
      )
      return null
    }
  }, [createSessionMutation])

  const ensureSession = useCallback(async (): Promise<string | null> => {
    if (sessionId) {
      return sessionId
    }

    return createBackendSession()
  }, [createBackendSession, sessionId])

  useEffect(() => {
    if (sessionId || createSessionMutation.isPending) {
      return
    }

    void createBackendSession()
  }, [createBackendSession, createSessionMutation.isPending, sessionId])

  const addPendingTurn = useCallback((userMessage: ChatMessage, assistantMessage: ChatMessage) => {
    setMessages((currentMessages) => [...currentMessages, userMessage, assistantMessage])
    setSessionError(null)
  }, [])

  const appendAssistantToken = useCallback((assistantMessageId: number, token: string) => {
    setMessages((currentMessages) =>
      currentMessages.map((message) =>
        message.id === assistantMessageId ? { ...message, content: `${message.content}${token}` } : message,
      ),
    )
  }, [])

  const setAssistantError = useCallback((assistantMessageId: number, message: string) => {
    setMessages((currentMessages) =>
      currentMessages.map((chatMessage) =>
        chatMessage.id === assistantMessageId ? { ...chatMessage, content: message } : chatMessage,
      ),
    )
  }, [])

  const removeTrailingEmptyAssistant = useCallback(() => {
    setMessages((currentMessages) => {
      const lastMessage = currentMessages.at(-1)

      if (!lastMessage || lastMessage.role !== 'assistant' || lastMessage.content.trim().length > 0) {
        return currentMessages
      }

      return currentMessages.slice(0, -1)
    })
  }, [])

  const clearSessionError = useCallback(() => {
    setSessionError(null)
  }, [])

  const sessionTitle = useMemo(() => {
    const firstUserMessage = messages.find((message) => message.role === 'user')
    if (!firstUserMessage) {
      return null
    }

    const compact = firstUserMessage.content.trim().replace(/\s+/g, ' ')
    if (!compact) {
      return null
    }

    if (compact.length <= 60) {
      return compact
    }

    return `${compact.slice(0, 57)}...`
  }, [messages])

  const bindSessionId = useCallback((newSessionId: string) => {
    setSessionId((currentSessionId) => currentSessionId ?? newSessionId)
  }, [])

  return {
    sessionId,
    sessionTitle,
    messages,
    sessionError,
    isInitializingSession: !sessionId && createSessionMutation.isPending,
    isCreatingSession: createSessionMutation.isPending,
    ensureSession,
    bindSessionId,
    addPendingTurn,
    appendAssistantToken,
    setAssistantError,
    removeTrailingEmptyAssistant,
    clearSessionError,
  }
}

export type ChatSession = {
  id: string
  state: string
  started_at: string
  ended_at: string | null
  title: string
}

export function formatSessionTimestamp(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return 'Unknown date'
  }

  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  }).format(date)
}
