import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { type SessionItem } from '../../api/generated/schemas'
import {
  getListSessionsApiSessionsGetQueryKey,
  useCreateSessionApiSessionsPost,
  useDeleteSessionApiSessionsSessionIdDelete,
  useListSessionsApiSessionsGet,
} from '../../api/generated/client'
import type {
  CreateSessionApiSessionsPostMutationResult,
  ListSessionsApiSessionsGetQueryResult,
} from '../../api/generated/client'
import type { SessionCreateResponse, SessionListResponse } from '../../api/generated/schemas'
import { type ChatMessage } from '../../components/ChatMessageList'

type UseChatSessionsOptions = {
  isStreaming: boolean
}

const isChatSessionsDebugEnabled = import.meta.env.DEV

function logChatSessionsDebug(message: string, payload?: Record<string, unknown>) {
  if (!isChatSessionsDebugEnabled) {
    return
  }

  if (payload) {
    console.info(`[chat-sessions] ${message}`, payload)
    return
  }

  console.info(`[chat-sessions] ${message}`)
}

function unwrapSessionList(
  response: ListSessionsApiSessionsGetQueryResult | undefined,
): SessionListResponse | undefined {
  if (!response) {
    return undefined
  }

  if ('data' in response && response.data && typeof response.data === 'object' && 'sessions' in response.data) {
    return response.data as SessionListResponse
  }

  if ('sessions' in response) {
    return response as unknown as SessionListResponse
  }

  return undefined
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

export function useChatSessions({ isStreaming }: UseChatSessionsOptions) {
  const queryClient = useQueryClient()
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null)
  const [messagesBySession, setMessagesBySession] = useState<Record<string, ChatMessage[]>>({})
  const [sessionError, setSessionError] = useState<string | null>(null)
  const autoCreateAttemptedRef = useRef(false)

  const {
    data: sessionsResponse,
    error: sessionsError,
    status: sessionsStatus,
    fetchStatus: sessionsFetchStatus,
    isLoading: isLoadingSessions,
    isRefetching: isRefetchingSessions,
  } = useListSessionsApiSessionsGet()
  const createSessionMutation = useCreateSessionApiSessionsPost()
  const deleteSessionMutation = useDeleteSessionApiSessionsSessionIdDelete()

  const sessions = useMemo(() => unwrapSessionList(sessionsResponse)?.sessions ?? [], [sessionsResponse])
  const selectedMessages = selectedSessionId ? (messagesBySession[selectedSessionId] ?? []) : []

  useEffect(() => {
    logChatSessionsDebug('sessions query state changed', {
      sessionsStatus,
      sessionsFetchStatus,
      isLoadingSessions,
      isRefetchingSessions,
      sessionCount: sessions.length,
      selectedSessionId,
      hasError: Boolean(sessionsError),
      errorMessage: sessionsError instanceof Error ? sessionsError.message : null,
    })
  }, [
    isLoadingSessions,
    isRefetchingSessions,
    selectedSessionId,
    sessions.length,
    sessionsError,
    sessionsFetchStatus,
    sessionsStatus,
  ])

  const invalidateSessions = useCallback(async () => {
    await queryClient.invalidateQueries({ queryKey: getListSessionsApiSessionsGetQueryKey() })
  }, [queryClient])

  const applySessionMessages = useCallback((sessionId: string, updater: (current: ChatMessage[]) => ChatMessage[]) => {
    setMessagesBySession((currentBySession) => {
      const currentMessages = currentBySession[sessionId] ?? []
      return {
        ...currentBySession,
        [sessionId]: updater(currentMessages),
      }
    })
  }, [])

  const ensureSession = useCallback(async (): Promise<string | null> => {
    if (selectedSessionId) {
      logChatSessionsDebug('ensureSession reused selected session', { selectedSessionId })
      return selectedSessionId
    }

    logChatSessionsDebug('ensureSession creating new session', {
      selectedSessionId,
      isCreatePending: createSessionMutation.isPending,
    })

    let createdSessionId: string
    try {
      const response = await createSessionMutation.mutateAsync()
      const normalizedResponse = unwrapSessionCreate(response)
      const sessionId = normalizedResponse?.session?.id
      if (!sessionId) {
        logChatSessionsDebug('session create response shape mismatch', {
          responseKeys: Object.keys(response ?? {}),
          hasData: 'data' in response,
        })
        throw new Error('Session creation returned an unexpected response payload.')
      }
      createdSessionId = sessionId
      logChatSessionsDebug('session created successfully', {
        createdSessionId,
      })
    } catch (error) {
      console.error('Create session request failed', error)
      logChatSessionsDebug('session creation failed', {
        errorMessage: error instanceof Error ? error.message : null,
      })
      const reason = error instanceof Error ? error.message : null
      setSessionError(
        reason
          ? `Unable to create a chat session right now: ${reason}`
          : 'Unable to create a chat session right now. Please try again.',
      )
      return null
    }

    setSelectedSessionId(createdSessionId)
    setMessagesBySession((currentBySession) => {
      if (currentBySession[createdSessionId]) {
        return currentBySession
      }

      return {
        ...currentBySession,
        [createdSessionId]: [],
      }
    })
    setSessionError(null)
    void invalidateSessions().catch((error) => {
      // Keep the created session selected even if list refetch fails.
      console.error('Failed to refresh sessions after creation', error)
    })

    return createdSessionId
  }, [createSessionMutation, invalidateSessions, selectedSessionId])

  useEffect(() => {
    logChatSessionsDebug('auto-selection effect tick', {
      isLoadingSessions,
      isCreatePending: createSessionMutation.isPending,
      sessionCount: sessions.length,
      selectedSessionId,
      isRefetchingSessions,
      autoCreateAttempted: autoCreateAttemptedRef.current,
    })

    if (isLoadingSessions || createSessionMutation.isPending) {
      logChatSessionsDebug('auto-selection paused due to loading or create pending')
      return
    }

    if (sessions.length === 0) {
      if (autoCreateAttemptedRef.current) {
        logChatSessionsDebug('auto-create already attempted; waiting for next state change')
        return
      }

      autoCreateAttemptedRef.current = true
      logChatSessionsDebug('no sessions found; auto-creating first session')
      void ensureSession()
      return
    }

    autoCreateAttemptedRef.current = false

    if (!selectedSessionId) {
      logChatSessionsDebug('selecting first available session', { nextSessionId: sessions[0].id })
      setSelectedSessionId(sessions[0].id)
      return
    }

    const selectedSessionStillPresent = sessions.some((session) => session.id === selectedSessionId)
    if (!selectedSessionStillPresent && !isRefetchingSessions) {
      logChatSessionsDebug('selected session missing after refetch; falling back to first session', {
        previousSessionId: selectedSessionId,
        nextSessionId: sessions[0].id,
      })
      setSelectedSessionId(sessions[0].id)
    }
  }, [
    createSessionMutation.isPending,
    ensureSession,
    isLoadingSessions,
    isRefetchingSessions,
    selectedSessionId,
    sessions,
  ])

  const createNewSession = useCallback(async () => {
    if (isStreaming) {
      return null
    }

    setSessionError(null)
    setSelectedSessionId(null)
    return ensureSession()
  }, [ensureSession, isStreaming])

  const deleteSelectedSession = useCallback(async () => {
    if (!selectedSessionId || isStreaming) {
      return
    }

    const deletingSessionId = selectedSessionId

    try {
      await deleteSessionMutation.mutateAsync({ sessionId: deletingSessionId })
      setMessagesBySession((currentBySession) => {
        const { [deletingSessionId]: _removed, ...remaining } = currentBySession
        return remaining
      })

      const remainingSessions = sessions.filter((session) => session.id !== deletingSessionId)
      setSelectedSessionId(remainingSessions.length > 0 ? remainingSessions[0].id : null)
      setSessionError(null)
      await invalidateSessions()

      if (remainingSessions.length === 0) {
        await ensureSession()
      }
    } catch {
      setSessionError('Unable to delete this session. Please try again.')
    }
  }, [deleteSessionMutation, ensureSession, invalidateSessions, isStreaming, selectedSessionId, sessions])

  const selectSession = useCallback(
    (sessionId: string) => {
      if (!isStreaming) {
        setSelectedSessionId(sessionId)
      }
    },
    [isStreaming],
  )

  const addPendingTurn = useCallback(
    (sessionId: string, userMessage: ChatMessage, assistantMessage: ChatMessage) => {
      applySessionMessages(sessionId, (currentMessages) => [...currentMessages, userMessage, assistantMessage])
      setSessionError(null)
    },
    [applySessionMessages],
  )

  const appendAssistantToken = useCallback(
    (sessionId: string, assistantMessageId: number, token: string) => {
      applySessionMessages(sessionId, (currentMessages) =>
        currentMessages.map((message) =>
          message.id === assistantMessageId ? { ...message, content: `${message.content}${token}` } : message,
        ),
      )
    },
    [applySessionMessages],
  )

  const setAssistantError = useCallback(
    (sessionId: string, assistantMessageId: number, message: string) => {
      applySessionMessages(sessionId, (currentMessages) =>
        currentMessages.map((chatMessage) =>
          chatMessage.id === assistantMessageId ? { ...chatMessage, content: message } : chatMessage,
        ),
      )
    },
    [applySessionMessages],
  )

  const removeTrailingEmptyAssistant = useCallback(() => {
    if (!selectedSessionId) {
      return
    }

    applySessionMessages(selectedSessionId, (currentMessages) => {
      const lastMessage = currentMessages.at(-1)

      if (!lastMessage || lastMessage.role !== 'assistant' || lastMessage.content.trim().length > 0) {
        return currentMessages
      }

      return currentMessages.slice(0, -1)
    })
  }, [applySessionMessages, selectedSessionId])

  const clearSessionError = useCallback(() => {
    setSessionError(null)
  }, [])

  const hasMessages = selectedMessages.length > 0

  return {
    sessions,
    selectedSessionId,
    selectedMessages,
    hasMessages,
    sessionError,
    isLoadingSessions,
    isRefetchingSessions,
    isCreatingSession: createSessionMutation.isPending,
    isDeletingSession: deleteSessionMutation.isPending,
    ensureSession,
    createNewSession,
    deleteSelectedSession,
    selectSession,
    addPendingTurn,
    appendAssistantToken,
    setAssistantError,
    removeTrailingEmptyAssistant,
    invalidateSessions,
    clearSessionError,
  }
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

export type ChatSession = SessionItem