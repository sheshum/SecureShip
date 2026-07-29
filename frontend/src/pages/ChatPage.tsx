import { useCallback, useRef, useState } from 'react'
import { ChatPanel } from '../components/ChatPanel'
import { OtpVerificationModal } from '../components/OtpVerificationModal'
import { useChatStream } from '../features/chat/useChatStream'
import { useChatSessions } from '../features/chat/useChatSessions'
import { useAuthFlow } from '../features/chat/useAuthFlow'
import type { ChatRequest } from '../api/generated/schemas'

function toChatRequest(sessionId: string, prompt: string): ChatRequest {
  return { session_id: sessionId, prompt }
}

export function ChatPage() {
  const [draft, setDraft] = useState('')
  const nextMessageIdRef = useRef(1)
  const { isStreaming, error, send, continuePending, cancel } = useChatStream()
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

  const auth = useAuthFlow(sessionId)

  const resumePendingTurn = useCallback(
    (turnId: string | null) => {
      if (!turnId || !sessionId) return
      const assistantMessageId = nextMessageIdRef.current++
      appendAssistantPlaceholder({ id: assistantMessageId, role: 'assistant', content: '' })
      void continuePending(
        { session_id: sessionId, pending_turn_id: turnId },
        {
          onToken: (token) => appendAssistantToken(assistantMessageId, token),
          onError: (message) => setAssistantError(assistantMessageId, message),
          onDone: () => removeTrailingEmptyAssistant(),
        },
      )
    },
    [sessionId, continuePending, appendAssistantPlaceholder, appendAssistantToken, setAssistantError, removeTrailingEmptyAssistant],
  )

  const handleSubmit = async () => {
    const trimmedMessage = draft.trim()
    if (!trimmedMessage || isStreaming) return

    const currentSessionId = await ensureSession()
    if (!currentSessionId) return

    const userMessageId = nextMessageIdRef.current++
    const assistantMessageId = nextMessageIdRef.current++
    addPendingTurn(
      { id: userMessageId, role: 'user', content: trimmedMessage },
      { id: assistantMessageId, role: 'assistant', content: '' },
    )
    setDraft('')
    clearSessionError()

    void send(toChatRequest(currentSessionId, trimmedMessage), {
      onSession: bindSessionId,
      onAuthState: auth.onAuthState,
      onAuthRequired: (event) => {
        removeTrailingEmptyAssistant()
        const nextTurnId = event.pending_turn_id ?? null
        if (event.message && nextTurnId !== auth.pendingTurnId) {
          appendAssistantMessage({ id: nextMessageIdRef.current++, role: 'assistant', content: event.message })
        }
        auth.onAuthRequired(event)
      },
      onShowCodeModal: auth.onShowCodeModal,
      onToken: (token) => appendAssistantToken(assistantMessageId, token),
      onError: (message) => setAssistantError(assistantMessageId, message),
      onDone: () => removeTrailingEmptyAssistant(),
    })
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
          authRequiredMessage={auth.authRequiredMessage}
          authRequiredInfoMessage={auth.authInfoMessage}
          onDraftChange={(value) => { if (!isStreaming) setDraft(value) }}
          onSubmit={handleSubmit}
          onCancel={() => { cancel(); removeTrailingEmptyAssistant() }}
        />
      </div>

      <OtpVerificationModal
        isOpen={auth.otpModalOpen}
        isSubmitting={auth.isVerifyPending}
        helperMessage={auth.otpHelperMessage}
        errorMessage={auth.otpErrorMessage}
        remainingAttempts={auth.otpRemainingAttempts}
        onSubmit={(code) => auth.handleVerifyCode(code, resumePendingTurn)}
        onClose={auth.closeModal}
      />
    </main>
  )
}
