import { useEffect, useMemo, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { HttpError } from '../api/generated/fetcher'
import {
  getRestoreSessionApiChatSessionGetQueryKey,
  useRestoreSessionApiChatSessionGet,
} from '../api/generated/client'
import type { ChatSessionState } from '../api/generated/schemas/chatSessionState'

export type DisplayMessage = { id: string; role: 'user' | 'assistant'; content: string }

export interface UseSessionPersistenceReturn {
  // Kept for building the close-session URL; null until first chat response or restore
  sessionId: string | null
  sessionState: ChatSessionState
  verificationRequired: boolean
  displayMessages: DisplayMessage[]
  appendLocalMessage(msg: DisplayMessage): void
  onChatResponse(sid: string, state: ChatSessionState): void
  onVerified(): void
  onSessionExpired(): void
  onSessionClosed(): void
}

export function useSessionPersistence(): UseSessionPersistenceReturn {
  const queryClient = useQueryClient()
  const [localMessages, setLocalMessages] = useState<DisplayMessage[]>([])
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [localSessionState, setLocalSessionState] = useState<ChatSessionState>('anonymous')
  const [localStateInitialized, setLocalStateInitialized] = useState(false)
  const [sessionInvalidated, setSessionInvalidated] = useState(false)

  // The API owns the session cookie; it may not be visible to JS on the frontend origin.
  // Probe unconditionally — 404 = no session, 410 = session expired.
  const restoreQuery = useRestoreSessionApiChatSessionGet({
    query: { retry: false },
  })

  useEffect(() => {
    if (!restoreQuery.isError) return

    if (restoreQuery.error instanceof HttpError) {
      console.error(
        `Session restore failed with status ${restoreQuery.error.status}: ${restoreQuery.error.message}`,
      )
      return
    }

    console.error('Session restore failed:', restoreQuery.error)
  }, [restoreQuery.error, restoreQuery.isError])

  const restorationData =
    !sessionInvalidated &&
    restoreQuery.isSuccess &&
    restoreQuery.data != null &&
    restoreQuery.data.status === 200
      ? restoreQuery.data.data
      : null

  // Seed sessionId from restore so the close-session URL is available after a refresh
  const effectiveSessionId = sessionId ?? (restorationData ? restorationData.session_id : null)

  // Use restored state until onChatResponse or onVerified has been called
  const sessionState: ChatSessionState =
    restorationData && !localStateInitialized ? restorationData.state : localSessionState
  const verificationRequired =
    restorationData && !localStateInitialized
      ? restorationData.verification_required
      : localSessionState === 'code_sent'

  const restoredMessages = useMemo<DisplayMessage[]>(() => {
    if (sessionInvalidated || !restorationData) return []
    return restorationData.messages.flatMap((m, i) => {
      if (m.role !== 'user' && m.role !== 'assistant') return []
      return [{ id: `restored-${i}`, role: m.role, content: m.content }]
    })
  }, [sessionInvalidated, restorationData])

  const displayMessages = useMemo(
    () => [...restoredMessages, ...localMessages],
    [restoredMessages, localMessages],
  )

  return {
    sessionId: effectiveSessionId,
    sessionState,
    verificationRequired,
    displayMessages,
    appendLocalMessage(msg) {
      setLocalMessages((prev) => [...prev, msg])
    },
    onChatResponse(sid, state) {
      setSessionId(sid)
      setLocalStateInitialized(true)
      setLocalSessionState(state)
    },
    onVerified() {
      setLocalStateInitialized(true)
      setLocalSessionState('verified')
    },
    onSessionExpired() {
      setSessionInvalidated(true)
      setSessionId(null)
      setLocalMessages([])
      setLocalStateInitialized(false)
      setLocalSessionState('anonymous')
    },
    onSessionClosed() {
      setSessionInvalidated(true)
      setSessionId(null)
      setLocalMessages([])
      setLocalStateInitialized(false)
      setLocalSessionState('anonymous')
      queryClient.removeQueries({ queryKey: getRestoreSessionApiChatSessionGetQueryKey() })
    },
  }
}

