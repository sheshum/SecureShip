import { useRef, useState } from 'react'
import { type IdentityInput } from '../components/AuthRequiredMessage'
import { type ChatMessage } from '../components/ChatMessageList'
import { ChatPanel } from '../components/ChatPanel'
import { OtpVerificationModal } from '../components/OtpVerificationModal'
import {
  useStartVerificationApiAuthStartVerificationPost,
  useVerifyCodeApiVerifyCodePost,
} from '../api/generated/client'
import { useChatStream } from '../features/chat/useChatStream'
import { useChatSessions } from '../features/chat/useChatSessions'
import type {
  ChatRequest,
  StartVerificationResponse,
  VerifyCodeResponse,
} from '../api/generated/schemas'

function toChatRequest(sessionId: string, messages: ChatMessage[]): ChatRequest {
  return {
    session_id: sessionId,
    messages: messages.map((message) => ({
      role: message.role,
      content: message.content,
    })),
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
  const nextMessageIdRef = useRef(1)
  const { isStreaming, error, send, cancel } = useChatStream()
  const startVerificationMutation = useStartVerificationApiAuthStartVerificationPost()
  const verifyCodeMutation = useVerifyCodeApiVerifyCodePost()
  const {
    sessionId,
    messages,
    sessionError,
    isInitializingSession,
    ensureSession,
    bindSessionId,
    addPendingTurn,
    appendAssistantToken,
    setAssistantError,
    removeTrailingEmptyAssistant,
    clearSessionError,
  } = useChatSessions()

  const unwrapStartVerificationResponse = (response: unknown): StartVerificationResponse | null => {
    if (response && typeof response === 'object' && 'data' in response) {
      const data = (response as { data?: unknown }).data
      if (data && typeof data === 'object' && 'state' in data) {
        return data as StartVerificationResponse
      }
    }

    if (response && typeof response === 'object' && 'state' in response) {
      return response as StartVerificationResponse
    }

    return null
  }

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
    const requestMessages = [
      ...messages,
      {
        id: userMessageId,
        role: 'user' as const,
        content: trimmedMessage,
      },
    ]

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

    const request = toChatRequest(currentSessionId, requestMessages)

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
        setAuthRequiredMessage(event.message)
      },
      onShowCodeModal: (event) => {
        if (!event.open) {
          return
        }

        setCodeModalHint(true)
        setAuthInfoMessage('A verification code was already issued for this session.')
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

  const handleAuthenticate = async (input: IdentityInput) => {
    if (!sessionId) {
      return
    }

    setOtpErrorMessage(null)
    setOtpHelperMessage(null)
    setOtpRemainingAttempts(null)

    try {
      const response = await startVerificationMutation.mutateAsync({
        data: {
          session_id: sessionId,
          first_name: input.firstName,
          last_name: input.lastName,
          phone_number: input.phoneNumber,
        },
      })
      const payload = unwrapStartVerificationResponse(response)
      if (!payload) {
        setOtpErrorMessage('Unexpected verification response. Please try again.')
        return
      }

      setAuthInfoMessage(payload.message)

      if (payload.started && payload.show_code_modal) {
        setOtpModalOpen(true)
        setOtpHelperMessage(payload.message)
        setOtpErrorMessage(null)
        return
      }

      if (payload.error_code) {
        setOtpErrorMessage(payload.message)
      }
    } catch (verificationError) {
      const message =
        verificationError instanceof Error
          ? verificationError.message
          : 'Unable to start verification right now. Please try again.'
      setOtpErrorMessage(message)
    }
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
          isStartingVerification={startVerificationMutation.isPending}
          onAuthenticate={handleAuthenticate}
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
