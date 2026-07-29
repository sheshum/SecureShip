import { useRef, useState } from 'react'
import { ChatPanel } from '../components/ChatPanel'
import { OtpVerificationModal } from '../components/OtpVerificationModal'
import {
  useVerifyCodeApiVerifyCodePost,
} from '../api/generated/client'
import { useChatStream } from '../features/chat/useChatStream'
import { useChatSessions } from '../features/chat/useChatSessions'
import type {
  ChatRequest,
  VerifyCodeResponse,
} from '../api/generated/schemas'

function toChatRequest(sessionId: string, prompt: string): ChatRequest {
  return {
    session_id: sessionId,
    prompt,
  }
}

export function ChatPage() {
  const [draft, setDraft] = useState('')
  const [authRequiredMessage, setAuthRequiredMessage] = useState<string | null>(null)
  const [authInfoMessage, setAuthInfoMessage] = useState<string | null>(null)
  const [codeModalHint, setCodeModalHint] = useState(false)
  const [otpModalOpen, setOtpModalOpen] = useState(false)
  const [otpHelperMessage, setOtpHelperMessage] = useState<string | null>(null)
  const [otpErrorMessage, setOtpErrorMessage] = useState<string | null>(null)
  const [otpRemainingAttempts, setOtpRemainingAttempts] = useState<number | null>(null)
  const [pendingTurnId, setPendingTurnId] = useState<string | null>(null)
  const nextMessageIdRef = useRef(1)
  const { isStreaming, error, send, continuePending, cancel } = useChatStream()
  const verifyCodeMutation = useVerifyCodeApiVerifyCodePost()
  const {
    sessionId,
    messages,
    sessionError,
    isInitializingSession,
    ensureSession,
    bindSessionId,
    addPendingTurn,
    appendAssistantPlaceholder,
    appendAssistantMessage,
    appendAssistantToken,
    setAssistantError,
    removeTrailingEmptyAssistant,
    clearSessionError,
  } = useChatSessions()

  const unwrapVerifyCodeResponse = (response: unknown): VerifyCodeResponse | null => {
    if (response && typeof response === 'object' && 'data' in response) {
      const data = (response as { data?: unknown }).data
      if (data && typeof data === 'object' && 'state' in data) {
        return data as VerifyCodeResponse
      }
    }

    if (response && typeof response === 'object' && 'state' in response) {
      return response as VerifyCodeResponse
    }

    return null
  }

  const handleSubmit = async () => {
    const trimmedMessage = draft.trim()

    if (!trimmedMessage || isStreaming) {
      return
    }

    const currentSessionId = await ensureSession()
    if (!currentSessionId) {
      return
    }

    const userMessageId = nextMessageIdRef.current++
    const assistantMessageId = nextMessageIdRef.current++

    addPendingTurn(
      {
        id: userMessageId,
        role: 'user',
        content: trimmedMessage,
      },
      {
        id: assistantMessageId,
        role: 'assistant',
        content: '',
      },
    )
    setDraft('')
    clearSessionError()

    const request = toChatRequest(currentSessionId, trimmedMessage)

    void send(request, {
      onSession: (streamSessionId) => {
        bindSessionId(streamSessionId)
      },
      onAuthState: (event) => {
        if (event.state === 'verified') {
          setAuthRequiredMessage(null)
          setAuthInfoMessage(null)
          setCodeModalHint(false)
          setOtpModalOpen(false)
          setOtpErrorMessage(null)
          setOtpHelperMessage(null)
          setOtpRemainingAttempts(null)
        }
      },
      onAuthRequired: (event) => {
        removeTrailingEmptyAssistant()
        const nextPendingTurnId = event.pending_turn_id ?? null
        if (event.message && nextPendingTurnId !== pendingTurnId) {
          appendAssistantMessage({
            id: nextMessageIdRef.current++,
            role: 'assistant',
            content: event.message,
          })
        }
        setAuthRequiredMessage(event.message)
        setPendingTurnId(nextPendingTurnId)
      },
      onShowCodeModal: (event) => {
        if (!event.open) {
          return
        }

        setOtpModalOpen(true)
        setCodeModalHint(true)
        setAuthInfoMessage('Verification code sent. Enter the code to continue.')
        setOtpHelperMessage('Verification code sent. Enter the code to continue.')
      },
      onToken: (token) => {
        appendAssistantToken(assistantMessageId, token)
      },
      onError: (message) => {
        setAssistantError(assistantMessageId, message)
      },
      onDone: () => {
        removeTrailingEmptyAssistant()
      },
    })
  }

  const handleVerifyCode = async (code: string) => {
    if (!sessionId) {
      return
    }

    setOtpErrorMessage(null)

    try {
      const response = await verifyCodeMutation.mutateAsync({
        data: {
          session_id: sessionId,
          code,
        },
      })
      const payload = unwrapVerifyCodeResponse(response)
      if (!payload) {
        setOtpErrorMessage('Unexpected verification response. Please try again.')
        return
      }

      setOtpHelperMessage(payload.message)
      setOtpRemainingAttempts(payload.remaining_attempts ?? null)

      if (payload.verified) {
        setAuthRequiredMessage(null)
        setAuthInfoMessage(payload.message)
        setCodeModalHint(false)
        setOtpModalOpen(false)
        setOtpErrorMessage(null)
        setOtpRemainingAttempts(null)

        const verifyPayload = payload as VerifyCodeResponse & { pending_turn_id?: string | null }
        const turnToContinue = verifyPayload.pending_turn_id ?? pendingTurnId

        if (turnToContinue) {
          const assistantMessageId = nextMessageIdRef.current++
          appendAssistantPlaceholder({
            id: assistantMessageId,
            role: 'assistant',
            content: '',
          })

          setAuthInfoMessage('Identity verified. Finishing your previous request...')

          void continuePending(
            {
              session_id: sessionId,
              pending_turn_id: turnToContinue,
            },
            {
              onToken: (token) => {
                appendAssistantToken(assistantMessageId, token)
              },
              onError: (message) => {
                setAssistantError(assistantMessageId, message)
              },
              onDone: () => {
                removeTrailingEmptyAssistant()
                setPendingTurnId(null)
              },
            },
          )
        }

        return
      }

      setOtpErrorMessage(payload.message)

      if (payload.state === 'collecting_identity') {
        setOtpModalOpen(false)
      }
    } catch (verificationError) {
      const message =
        verificationError instanceof Error
          ? verificationError.message
          : 'Unable to verify code right now. Please try again.'
      setOtpErrorMessage(message)
    }
  }

  const handleChange = (value: string) => {
    if (!isStreaming) {
      setDraft(value)
    }
  }

  const handleCancel = () => {
    cancel()
    removeTrailingEmptyAssistant()
  }

  const activeError = sessionError ?? error

  return (
    <main className="relative min-h-screen overflow-hidden bg-[url('/secure-ship-background.jpeg')] bg-cover bg-fixed bg-center px-2 py-3 sm:px-4 sm:py-4">
      <div className="pointer-events-none absolute inset-0 bg-slate-950/38" aria-hidden="true" />

      <div className="relative mx-auto flex min-h-[calc(100svh-1.5rem)] w-full max-w-6xl flex-col gap-4 rounded-[2rem] border border-white/35 bg-slate-100/72 p-3 shadow-[0_30px_90px_rgba(15,23,42,0.34)] backdrop-blur-2xl sm:min-h-[calc(100svh-2rem)] sm:gap-5 sm:p-5">
        <ChatPanel
          messages={messages}
          draft={draft}
          isStreaming={isStreaming}
          isInitializingSession={isInitializingSession}
          errorMessage={activeError}
          authRequiredMessage={authRequiredMessage}
          authRequiredInfoMessage={
            codeModalHint
              ? authInfoMessage ?? 'A verification code is ready for this session.'
              : authInfoMessage
          }
          onDraftChange={handleChange}
          onSubmit={handleSubmit}
          onCancel={handleCancel}
        />
      </div>

      <OtpVerificationModal
        isOpen={otpModalOpen}
        isSubmitting={verifyCodeMutation.isPending}
        helperMessage={otpHelperMessage}
        errorMessage={otpErrorMessage}
        remainingAttempts={otpRemainingAttempts}
        onSubmit={handleVerifyCode}
        onClose={() => {
          setOtpModalOpen(false)
          setOtpErrorMessage(null)
          setOtpHelperMessage(null)
          setOtpRemainingAttempts(null)
        }}
      />
    </main>
  )
}
