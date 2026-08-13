import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AppRoutes } from '../lib/routes'
import { ChatPanel } from '../components/Chat/ChatPanel'
import { ChatCloseModal } from '../components/Chat/ChatCloseModal'
import { OtpVerificationModal } from '../components/Chat/OtpVerificationModal'
import { Toast } from '../components/Toast'
import { useChatApiChatPost, useVerifyCodeApiAuthVerifyCodePost, getChatApiChatPostUrl } from '../api/generated/client'
import type { ChatSessionState } from '../api/generated/schemas/chatSessionState'
import { resolveApiUrl } from '../api/url'
import { cancelRequest } from '../api/generated/fetcher'

type MessageRole = 'user' | 'assistant' | 'melany' | 'event'

function createMessage(role: MessageRole, content: string) {
  return { id: crypto.randomUUID(), role, content }
}

const delay = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms))

const handleStopRequest = () => {
  cancelRequest(getChatApiChatPostUrl())
}

export function ChatPage() {
  const navigate = useNavigate()
  const [draft, setDraft] = useState('')
  const [messages, setMessages] = useState<Array<{ id: string; role: MessageRole; content: string }>>([])
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [sessionState, setSessionState] = useState<ChatSessionState>('anonymous')
  const [firstName, setFirstName] = useState<string | null>(null)
  const [isHandoffSequencePlaying, setIsHandoffSequencePlaying] = useState(false)
  const [isOtpModalOpen, setIsOtpModalOpen] = useState(false)
  const [isCloseModalOpen, setIsCloseModalOpen] = useState(false)
  const [otpError, setOtpError] = useState<string | null>(null)
  const [attemptsRemaining, setAttemptsRemaining] = useState<number | null>(null)
  const [toastMessage, setToastMessage] = useState<string | null>(null)
  const [closeError, setCloseError] = useState<string | null>(null)
  const [isClosingSession, setIsClosingSession] = useState(false)
  const chatMutation = useChatApiChatPost()
  const verifyCodeMutation = useVerifyCodeApiAuthVerifyCodePost()

  const handleSubmit = async (message?: string) => {
    const trimmedMessage = (message ?? draft).trim()
    if (!trimmedMessage || chatMutation.isPending) return

    // Add user message to display
    setMessages((prev) => [...prev, createMessage('user', trimmedMessage)])
    setDraft('')

    try {
      const response = await chatMutation.mutateAsync({
        data: {
          prompt: trimmedMessage,
          session_id: sessionId || undefined,
        }
      })

      if (response.status === 200) {
        const { reply, session_id, state, verification_required, escalation_handoff, customer_first_name } = response.data

        if (customer_first_name) setFirstName(customer_first_name)
        setSessionId(session_id)
        setSessionState(state)

        if (escalation_handoff) {
          // Step 1: LLM's acknowledgement message ("Thank you for your patience...")
          setMessages((prev) => [...prev, createMessage('assistant', reply)])

          // Steps 2-4: cosmetic scripted handoff — runs client-side, no network calls
          setIsHandoffSequencePlaying(true)
          try {
            await delay(700)
            setMessages((prev) => [...prev, createMessage('event', 'Melany has entered the chat')])

            await delay(1200)
            setMessages((prev) => [...prev, createMessage('melany', 'Hello, my name is Melany, let me just read through the chat...')])

            const fn = customer_first_name ?? firstName
            await delay(2000)
            setMessages((prev) => [
              ...prev,
              createMessage('melany', fn ? `Hey ${fn}, I'm up to speed, how can I help?` : "Hey, I'm up to speed, how can I help?"),
            ])
          } finally {
            setIsHandoffSequencePlaying(false)
          }
        } else {
          const role = state === 'escalated_to_human' ? 'melany' : 'assistant'
          setMessages((prev) => [...prev, createMessage(role, reply)])

          if (verification_required) {
            setIsOtpModalOpen(true)
            setOtpError(null)
            setAttemptsRemaining(null)
          }
        }
      }
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') return
      console.error('Chat request failed:', error)
      setMessages((prev) => [
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
          setSessionState('verified')
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
          messages={messages}
          isLoading={chatMutation.isPending}
          isHandoffSequencePlaying={isHandoffSequencePlaying}
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
    </main>
  )
}

