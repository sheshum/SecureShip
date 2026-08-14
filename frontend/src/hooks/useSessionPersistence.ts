import { useMemo, useState } from 'react'
import { useRestoreSessionApiChatSessionGet } from '../api/generated/client'
import { HttpError } from '../api/generated/fetcher'
import type { ChatSessionState } from '../api/generated/schemas/chatSessionState'

export type DisplayMessage = { id: string; role: 'user' | 'assistant'; content: string }

export interface UseSessionPersistenceReturn {
  // Kept for building the close-session URL; null until first chat response or restore
  sessionId: string | null
  sessionState: ChatSessionState
  displayMessages: DisplayMessage[]
  // true when the restore query returns 410 (session existed but expired)
  showExpiredSessionToast: boolean
  appendLocalMessage(msg: DisplayMessage): void
  onChatResponse(sid: string, state: ChatSessionState): void
  onVerified(): void
  onSessionExpired(): void
  onSessionClosed(): void
  dismissExpiredToast(): void
}

export function useSessionPersistence(): UseSessionPersistenceReturn {
  const [localMessages, setLocalMessages] = useState<DisplayMessage[]>([])
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [localSessionState, setLocalSessionState] = useState<ChatSessionState>('anonymous')
  const [localStateInitialized, setLocalStateInitialized] = useState(false)
  const [sessionInvalidated, setSessionInvalidated] = useState(false)
  const [expiredToastDismissed, setExpiredToastDismissed] = useState(false)

  // Frozen at mount — avoids firing the restore query for users who never had a session
  const [hasSessionCookie] = useState(() => document.cookie.includes('has_session=1'))

  // Cookie is sent automatically by the browser — no session ID needed in the URL.
  // 410 = cookie present but session expired/closed.
  const restoreQuery = useRestoreSessionApiChatSessionGet({
    query: { enabled: hasSessionCookie, retry: false },
  })

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

  // 410 = had a session cookie that is now expired or gone
  const showExpiredSessionToast =
    !sessionInvalidated &&
    restoreQuery.isError &&
    restoreQuery.error instanceof HttpError &&
    restoreQuery.error.status === 410 &&
    !expiredToastDismissed

  return {
    sessionId: effectiveSessionId,
    sessionState,
    displayMessages,
    showExpiredSessionToast,
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
      // Cookie is deleted by the backend PATCH /api/sessions/{id} response
    },
    dismissExpiredToast() {
      setExpiredToastDismissed(true)
    },
  }
}

