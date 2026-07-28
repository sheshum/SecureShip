import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { type SessionItem } from '../../api/generated/schemas'
import { resolveApiUrl } from '../../api/url'
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

type SessionTranscriptEvent = {
  type: string
  role?: string | null
  content?: string | null
}

type SessionDetailResponse = {
  transcript?: {
    events?: SessionTranscriptEvent[]
  }
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
  const [emptySessionMessages, setEmptySessionMessages] = useState<ChatMessage[]>([])
  const [sessionError, setSessionError] = useState<string | null>(null)
  const [loadingSessionId, setLoadingSessionId] = useState<string | null>(null)
  const hydratedSessionIdsRef = useRef<Set<string>>(new Set())
  const pendingDeletedSessionIdsRef = useRef<Set<string>>(new Set())

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

  const allSessions = useMemo(() => unwrapSessionList(sessionsResponse)?.sessions ?? [], [sessionsResponse])
  const sessions = useMemo(
    () =>
      allSessions.filter((session) => {
        if (pendingDeletedSessionIdsRef.current.has(session.id)) {
          return false
        }

        return true
      }),
    [allSessions],
  )
  const selectedMessages = selectedSessionId
    ? (messagesBySession[selectedSessionId] ?? [])
    : emptySessionMessages

  useEffect(() => {
    logChatSessionsDebug('sessions query state changed', {
      sessionsStatus,
      sessionsFetchStatus,
      isLoadingSessions,
      isRefetchingSessions,
      totalSessionCount: allSessions.length,
      visibleSessionCount: sessions.length,
      selectedSessionId,
      hasError: Boolean(sessionsError),
      errorMessage: sessionsError instanceof Error ? sessionsError.message : null,
    })
  }, [
    allSessions.length,
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

  const applySessionMessages = useCallback((sessionId: string | null, updater: (current: ChatMessage[]) => ChatMessage[]) => {
    if (!sessionId) {
      setEmptySessionMessages((currentMessages) => updater(currentMessages))
      return
    }

    setMessagesBySession((currentBySession) => {
      const currentMessages = currentBySession[sessionId] ?? []
      return {
        ...currentBySession,
        [sessionId]: updater(currentMessages),
      }
    })
  }, [])

  const mapTranscriptToMessages = useCallback((events: SessionTranscriptEvent[] | undefined): ChatMessage[] => {
    if (!events || events.length === 0) {
      return []
    }

    let nextId = 1
    const messages: ChatMessage[] = []

    for (const event of events) {
      if (event.type !== 'message') {
        continue
      }

      if (event.role !== 'user' && event.role !== 'assistant') {
        continue
      }

      const content = (event.content ?? '').trim()
      if (!content) {
        continue
      }

      messages.push({
        id: nextId,
        role: event.role,
        content,
      })
      nextId += 1
    }

    return messages
  }, [])

  const loadSessionHistory = useCallback(
    async (sessionId: string): Promise<boolean> => {
      if (hydratedSessionIdsRef.current.has(sessionId)) {
        return true
      }

      try {
        setLoadingSessionId(sessionId)
        const response = await fetch(resolveApiUrl(`/api/sessions/${sessionId}`), {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
        })

        if (!response.ok) {
          const text = await response.text()
          throw new Error(text || `HTTP ${response.status}`)
        }

        const payload = (await response.json()) as SessionDetailResponse
        const hydratedMessages = mapTranscriptToMessages(payload.transcript?.events)
        hydratedSessionIdsRef.current.add(sessionId)
        setMessagesBySession((currentBySession) => ({
          ...currentBySession,
          [sessionId]: hydratedMessages,
        }))
        return true
      } catch (error) {
        console.error('Failed to load session transcript', error)
        setSessionError('Unable to load chat history for this session. Please try again.')
        return false
      } finally {
        setLoadingSessionId((currentSessionId) => (currentSessionId === sessionId ? null : currentSessionId))
      }
    },
    [mapTranscriptToMessages],
  )

  const ensureSession = useCallback(async (): Promise<string | null> => {
    if (selectedSessionId) {
      logChatSessionsDebug('ensureSession reused selected session', { selectedSessionId })
      return selectedSessionId
    }

    logChatSessionsDebug('ensureSession returning frontend-only empty session')
    return null
  }, [selectedSessionId])

  const createBackendSession = useCallback(async (): Promise<string | null> => {
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
    hydratedSessionIdsRef.current.add(createdSessionId)
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

  const bindEmptySessionToCreatedSession = useCallback(
    (sessionId: string) => {
      hydratedSessionIdsRef.current.add(sessionId)
      setEmptySessionMessages((currentEmptyMessages) => {
        setMessagesBySession((currentBySession) => {
          if (currentBySession[sessionId]) {
            return currentBySession
          }

          return {
            ...currentBySession,
            [sessionId]: currentEmptyMessages,
          }
        })

        return []
      })
      setSelectedSessionId(sessionId)
      setSessionError(null)
      void invalidateSessions().catch((error) => {
        console.error('Failed to refresh sessions after first chat turn', error)
      })
    },
    [invalidateSessions],
  )

  useEffect(() => {
    const availableSessions = allSessions.filter((session) => !pendingDeletedSessionIdsRef.current.has(session.id))

    logChatSessionsDebug('auto-selection effect tick', {
      isLoadingSessions,
      isCreatePending: createSessionMutation.isPending,
      sessionCount: allSessions.length,
      availableSessionCount: availableSessions.length,
      selectedSessionId,
      isRefetchingSessions,
    })

    if (isLoadingSessions || createSessionMutation.isPending) {
      logChatSessionsDebug('auto-selection paused due to loading or create pending')
      return
    }

    if (availableSessions.length === 0) {
      if (selectedSessionId !== null) {
        setSelectedSessionId(null)
      }
      return
    }

    if (!selectedSessionId) {
      logChatSessionsDebug('selecting first available session', { nextSessionId: availableSessions[0].id })
      setSelectedSessionId(availableSessions[0].id)
      return
    }

    const selectedSessionStillPresent = availableSessions.some((session) => session.id === selectedSessionId)
    if (!selectedSessionStillPresent && !isRefetchingSessions) {
      logChatSessionsDebug('selected session missing after refetch; falling back to first session', {
        previousSessionId: selectedSessionId,
        nextSessionId: availableSessions[0].id,
      })
      setSelectedSessionId(availableSessions[0].id)
    }
  }, [
    allSessions,
    createSessionMutation.isPending,
    isLoadingSessions,
    isRefetchingSessions,
    selectedSessionId,
  ])

  useEffect(() => {
    if (!selectedSessionId || isStreaming) {
      return
    }

    if (pendingDeletedSessionIdsRef.current.has(selectedSessionId)) {
      return
    }

    if (hydratedSessionIdsRef.current.has(selectedSessionId)) {
      return
    }

    const selectedSession = allSessions.find((session) => session.id === selectedSessionId)

    let isCancelled = false

    if (selectedSession) {
      console.log(`Loading chat history for session "${selectedSession.title}" (${selectedSession.id})...`)
      void loadSessionHistory(selectedSessionId).then((loaded) => {
        if (isCancelled || !loaded) {
          return
        }

        setSessionError(null)
      })
    }

    return () => {
      isCancelled = true
    }
  }, [allSessions, isStreaming, loadSessionHistory, selectedSessionId])

  const createNewSession = useCallback(async () => {
    if (isStreaming || allSessions.length === 0) {
      return null
    }

    setSessionError(null)
    return createBackendSession()
  }, [allSessions.length, createBackendSession, isStreaming])

  const deleteSelectedSession = useCallback(async () => {
    if (!selectedSessionId || isStreaming) {
      return
    }

    const deletingSessionId = selectedSessionId

    try {
      await deleteSessionMutation.mutateAsync({ sessionId: deletingSessionId })
      pendingDeletedSessionIdsRef.current.add(deletingSessionId)
      hydratedSessionIdsRef.current.delete(deletingSessionId)
      setMessagesBySession((currentBySession) => {
        const { [deletingSessionId]: _removed, ...remaining } = currentBySession
        return remaining
      })

      const remainingSessions = allSessions.filter(
        (session) =>
          session.id !== deletingSessionId && !pendingDeletedSessionIdsRef.current.has(session.id),
      )
      setSelectedSessionId(remainingSessions.length > 0 ? remainingSessions[0].id : null)
      setSessionError(null)
      await invalidateSessions()
    } catch {
      setSessionError('Unable to delete this session. Please try again.')
    }
  }, [allSessions, deleteSessionMutation, invalidateSessions, isStreaming, selectedSessionId])

  const selectSession = useCallback(
    (sessionId: string) => {
      if (!isStreaming) {
        setSelectedSessionId(sessionId)
      }
    },
    [isStreaming],
  )

  const addPendingTurn = useCallback(
    (sessionId: string | null, userMessage: ChatMessage, assistantMessage: ChatMessage) => {
      applySessionMessages(sessionId, (currentMessages) => [...currentMessages, userMessage, assistantMessage])
      setSessionError(null)
    },
    [applySessionMessages],
  )

  const appendAssistantToken = useCallback(
    (sessionId: string | null, assistantMessageId: number, token: string) => {
      applySessionMessages(sessionId, (currentMessages) =>
        currentMessages.map((message) =>
          message.id === assistantMessageId ? { ...message, content: `${message.content}${token}` } : message,
        ),
      )
    },
    [applySessionMessages],
  )

  const setAssistantError = useCallback(
    (sessionId: string | null, assistantMessageId: number, message: string) => {
      applySessionMessages(sessionId, (currentMessages) =>
        currentMessages.map((chatMessage) =>
          chatMessage.id === assistantMessageId ? { ...chatMessage, content: message } : chatMessage,
        ),
      )
    },
    [applySessionMessages],
  )

  const removeTrailingEmptyAssistant = useCallback(() => {
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
  const isLoadingSelectedSession = Boolean(selectedSessionId) && loadingSessionId === selectedSessionId
  const hasPersistedSessions = allSessions.length > 0

  return {
    sessions,
    selectedSessionId,
    selectedMessages,
    hasMessages,
    hasPersistedSessions,
    isLoadingSelectedSession,
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
    bindEmptySessionToCreatedSession,
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