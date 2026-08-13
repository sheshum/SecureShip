import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AppRoutes } from '../lib/routes'
import { ChatPanel } from '../components/Chat/ChatPanel'
import { ChatCloseModal } from '../components/Chat/ChatCloseModal'
import { OtpVerificationModal } from '../components/Chat/OtpVerificationModal'
import { Toast } from '../components/Toast'
import { useChatApiChatPost, useVerifyCodeApiAuthVerifyCodePost, getChatApiChatPostUrl, useRestoreSessionApiChatSessionSessionIdGet } from '../api/generated/client'
import type { ChatSessionState } from '../api/generated/schemas/chatSessionState'
import { resolveApiUrl } from '../api/url'
import { cancelRequest } from '../api/generated/fetcher'

const SESSION_STORAGE_KEY = 'secureship_session_id'

function isSessionExpiredError(error: unknown): boolean {
  return error instanceof Error && error.message.toLowerCase().includes('expired')
}

function createMessage(role: 'user' | 'assistant', content: string) {
  return {
    id: crypto.randomUUID(),
    role,
    content,
  }
}

const handleStopRequest = () => {
  cancelRequest(getChatApiChatPostUrl())
}

type DisplayMessage = { id: string; role: 'user' | 'assistant'; content: string }

export function ChatPage() {
  const navigate = useNavigate()
  const [draft, setDraft] = useState('')

  // Frozen at mount — the session ID that was persisted before this page visit
  const [initialStoredId] = useState<string | null>(() => localStorage.getItem(SESSION_STORAGE_KEY))

  // Messages added during this page visit (not from restoration)
  const [localMessages, setLocalMessages] = useState<DisplayMessage[]>([])
  // Session ID and state driven by backend responses
  const [newSessionId, setNewSessionId] = useState<string | null>(null)
  const [localSessionState, setLocalSessionState] = useState<ChatSessionState>('anonymous')
  // Set to true when the backend reports the restored session has expired mid-chat
  const [sessionInvalidated, setSessionInvalidated] = useState(false)

  const [isOtpModalOpen, setIsOtpModalOpen] = useState(false)
  const [isCloseModalOpen, setIsCloseModalOpen] = useState(false)
  const [otpError, setOtpError] = useState<string | null>(null)
  const [attemptsRemaining, setAttemptsRemaining] = useState<number | null>(null)
  const [toastMessage, setToastMessage] = useState<string | null>(null)
  const [expiredToastDismissed, setExpiredToastDismissed] = useState(false)
  const [closeError, setCloseError] = useState<string | null>(null)
  const [isClosingSession, setIsClosingSession] = useState(false)
  const chatMutation = useChatApiChatPost()
  const verifyCodeMutation = useVerifyCodeApiAuthVerifyCodePost()

  const restoreQuery = useRestoreSessionApiChatSessionSessionIdGet(initialStoredId!, {
    query: { enabled: !!initialStoredId, retry: false },
  })

  // Clear localStorage when restoration fails (no setState — storage side-effect only)
  useEffect(() => {
    if (initialStoredId && restoreQuery.isError) {
      localStorage.removeItem(SESSION_STORAGE_KEY)
    }
  }, [initialStoredId, restoreQuery.isError])

  // Non-null only when a valid restored session is available and not yet invalidated
  const restorationData =
    !sessionInvalidated &&
    restoreQuery.isSuccess &&
    restoreQuery.data != null &&
    restoreQuery.data.status === 200
      ? restoreQuery.data.data
      : null

  // Effective session ID: restored session or new session created by the backend
  const sessionId: string | null = restorationData && initialStoredId ? initialStoredId : newSessionId

  // Effective session state: restored state until the user sends a new local message
  const sessionState: ChatSessionState =
    restorationData && localMessages.length === 0 ? restorationData.state : localSessionState

  // Restored messages with stable IDs; recomputed only when query data changes
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

  // Derived from query error — no useEffect needed
  const showExpiredSessionToast = !!initialStoredId && restoreQuery.isError && !expiredToastDismissed

  const handleSubmit = async (message?: string) => {
    const trimmedMessage = (message ?? draft).trim()
    if (!trimmedMessage || chatMutation.isPending) return

    setLocalMessages((prev) => [...prev, createMessage('user', trimmedMessage)])
    setDraft('')

    try {
      const response = await chatMutation.mutateAsync({
        data: {
          prompt: trimmedMessage,
          session_id: sessionId || undefined,
        },
      })

      if (response.status === 200) {
        setLocalMessages((prev) => [...prev, createMessage('assistant', response.data.reply)])
        const sid = response.data.session_id
        setNewSessionId(sid)
        localStorage.setItem(SESSION_STORAGE_KEY, sid)
        setLocalSessionState(response.data.state)

        if (response.data.verification_required) {
          setIsOtpModalOpen(true)
          setOtpError(null)
          setAttemptsRemaining(null)
        }
      }
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') return
      if (isSessionExpiredError(error)) {
        localStorage.removeItem(SESSION_STORAGE_KEY)
        setSessionInvalidated(true)
        setNewSessionId(null)
        setLocalMessages([])
        setLocalSessionState('anonymous')
        setToastMessage('Your session has expired. Please start a new conversation.')
        return
      }
      console.error('Chat request failed:', error)
      setLocalMessages((prev) => [
        ...prev,
        createMessage('assistant', 'Sorry, I encountered an error. Please try again.'),
      ])
    }
  }

  const handleVerifyCode = async (code: string) => {
    if (!sessionId) return

    setOtpError(null)

    try {
      const response = await verifyCodeMutation.mutateAsync({
        data: {
          session_id: sessionId,
          code: code,
        }
      })

      if (response.status === 200) {
        const { result, attempts_remaining } = response.data

        if (result === 'verified') {
          setIsOtpModalOpen(false)
          setLocalSessionState('verified')
          setOtpError(null)
          setAttemptsRemaining(null)
          setToastMessage('Verification successful! You now have access to your shipment information.')
        } else if (result === 'incorrect') {
          setOtpError(`Incorrect code. ${attempts_remaining ?? 0} attempts remaining.`)
          setAttemptsRemaining(attempts_remaining ?? null)
        } else if (result === 'expired') {
          setOtpError('This verification code has expired. Please request a new one.')
          setAttemptsRemaining(null)
        }
      }
    } catch (error) {
      console.error('Code verification failed:', error)
      setOtpError('Verification failed. Please try again.')
    }
  }

  const handleCloseOtpModal = () => {
    setIsOtpModalOpen(false)
    setOtpError(null)
    setAttemptsRemaining(null)
  }

  const handleCloseSession = async () => {
    localStorage.removeItem(SESSION_STORAGE_KEY)
    if (!sessionId) {
      void navigate(AppRoutes.Home)
      return
    }

    setCloseError(null)
    setIsClosingSession(true)

    try {
      const url = resolveApiUrl(`/api/sessions/${sessionId}`)
      const response = await fetch(url, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ended_at: new Date().toISOString() }),
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }))
        throw new Error(errorData.detail || 'Failed to close session')
      }

      void navigate(AppRoutes.Home)
    } catch (error) {
      console.error('Failed to close session:', error)
      setCloseError(error instanceof Error ? error.message : 'Failed to close session. Please try again.')
    } finally {
      setIsClosingSession(false)
    }
  }

  return (
    <main className="relative min-h-screen overflow-hidden bg-[url('/secure-ship-background.jpeg')] bg-cover bg-fixed bg-center px-2 py-3 sm:px-4 sm:py-4">
      <div className="pointer-events-none absolute inset-0 bg-slate-950/38" aria-hidden="true" />

      <div className="relative mx-auto flex h-[calc(100svh-1.5rem)] w-full max-w-6xl flex-col gap-4 rounded-[2rem] border border-white/35 bg-slate-100/72 p-3 shadow-[0_30px_90px_rgba(15,23,42,0.34)] backdrop-blur-2xl sm:h-[calc(100svh-2rem)] sm:gap-5 sm:p-5">
        <ChatPanel
          draft={draft}
          messages={displayMessages}
          isLoading={chatMutation.isPending}
          sessionState={sessionState}
          onDraftChange={setDraft}
          onSubmit={handleSubmit}
          onStopRequest={handleStopRequest}
          onClose={() => setIsCloseModalOpen(true)}
        />
      </div>

      {isCloseModalOpen && (
        <ChatCloseModal
          isClosing={isClosingSession}
          errorMessage={closeError}
          onClose={() => {
            setIsCloseModalOpen(false)
            setCloseError(null)
          }}
          onConfirm={handleCloseSession}
        />
      )}

      {isOtpModalOpen && (
        <OtpVerificationModal
          isSubmitting={verifyCodeMutation.isPending}
          errorMessage={otpError}
          helperMessage={null}
          remainingAttempts={attemptsRemaining}
          onSubmit={handleVerifyCode}
          onClose={handleCloseOtpModal}
        />
      )}

      {toastMessage && (
        <Toast
          message={toastMessage}
          type="success"
          onClose={() => setToastMessage(null)}
        />
      )}

      {showExpiredSessionToast && (
        <Toast
          message="Your previous session has expired. Starting a new conversation."
          type="info"
          onClose={() => setExpiredToastDismissed(true)}
        />
      )}
    </main>
  )
}

