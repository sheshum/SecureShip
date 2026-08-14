import { useEffect, useMemo, useState } from 'react'
import { useRestoreSessionApiChatSessionSessionIdGet } from '../api/generated/client'
import type { ChatSessionState } from '../api/generated/schemas/chatSessionState'

export const SESSION_STORAGE_KEY = 'secureship_session_id'

export type DisplayMessage = { id: string; role: 'user' | 'assistant'; content: string }

export interface UseSessionPersistenceReturn {
  sessionId: string | null
  sessionState: ChatSessionState
  displayMessages: DisplayMessage[]
  showExpiredSessionToast: boolean
  appendLocalMessage(msg: DisplayMessage): void
  onChatResponse(sid: string, state: ChatSessionState): void
  onVerified(): void
  onSessionExpired(): void
  onSessionClosed(): void
  dismissExpiredToast(): void
}

export function useSessionPersistence(): UseSessionPersistenceReturn {
  // Frozen at mount — the session ID that was persisted before this page visit
  const [initialStoredId] = useState<string | null>(() => localStorage.getItem(SESSION_STORAGE_KEY))

  const [localMessages, setLocalMessages] = useState<DisplayMessage[]>([])
  const [newSessionId, setNewSessionId] = useState<string | null>(null)
  const [localSessionState, setLocalSessionState] = useState<ChatSessionState>('anonymous')
  // Tracks whether any local state update (chat response or OTP) has been applied
  const [localStateInitialized, setLocalStateInitialized] = useState(false)
  const [sessionInvalidated, setSessionInvalidated] = useState(false)
  const [expiredToastDismissed, setExpiredToastDismissed] = useState(false)

  const restoreQuery = useRestoreSessionApiChatSessionSessionIdGet(initialStoredId!, {
    query: { enabled: !!initialStoredId, retry: false },
  })

  // Clear localStorage when restoration fails — storage side-effect only, no state change
  useEffect(() => {
    if (initialStoredId && restoreQuery.isError) {
      localStorage.removeItem(SESSION_STORAGE_KEY)
    }
  }, [initialStoredId, restoreQuery.isError])

  const restorationData =
    !sessionInvalidated &&
    restoreQuery.isSuccess &&
    restoreQuery.data != null &&
    restoreQuery.data.status === 200
      ? restoreQuery.data.data
      : null

  const sessionId: string | null = restorationData && initialStoredId ? initialStoredId : newSessionId

  // Use restored state until onChatResponse or onVerified has been called
  const sessionState: ChatSessionState =
    restorationData && !localStateInitialized ? restorationData.state : localSessionState

  const restoredMessages = useMemo<DisplayMessage[]>(() => {
    if (
      sessionInvalidated ||
      !initialStoredId ||
      !restoreQuery.isSuccess ||
      !restoreQuery.data ||
      restoreQuery.data.status !== 200
    )
      return []
    return restoreQuery.data.data.messages.flatMap((m, i) => {
      if (m.role !== 'user' && m.role !== 'assistant') return []
      return [{ id: `restored-${i}`, role: m.role, content: m.content }]
    })
  }, [sessionInvalidated, initialStoredId, restoreQuery.isSuccess, restoreQuery.data])

  const displayMessages = useMemo(
    () => [...restoredMessages, ...localMessages],
    [restoredMessages, localMessages],
  )

  const showExpiredSessionToast = !!initialStoredId && restoreQuery.isError && !expiredToastDismissed

  return {
    sessionId,
    sessionState,
    displayMessages,
    showExpiredSessionToast,
    appendLocalMessage(msg) {
      setLocalMessages((prev) => [...prev, msg])
    },
    onChatResponse(sid, state) {
      setNewSessionId(sid)
      localStorage.setItem(SESSION_STORAGE_KEY, sid)
      setLocalStateInitialized(true)
      setLocalSessionState(state)
    },
    onVerified() {
      setLocalStateInitialized(true)
      setLocalSessionState('verified')
    },
    onSessionExpired() {
      localStorage.removeItem(SESSION_STORAGE_KEY)
      setSessionInvalidated(true)
      setNewSessionId(null)
      setLocalMessages([])
      setLocalStateInitialized(false)
      setLocalSessionState('anonymous')
    },
    onSessionClosed() {
      localStorage.removeItem(SESSION_STORAGE_KEY)
    },
    dismissExpiredToast() {
      setExpiredToastDismissed(true)
    },
  }
}
