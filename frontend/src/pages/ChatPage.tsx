import { useState } from 'react'
import { ChatPanel } from '../components/ChatPanel'
import { OtpVerificationModal } from '../components/OtpVerificationModal'
import { Toast } from '../components/Toast'
import { useChatApiChatPost, useVerifyCodeApiAuthVerifyCodePost } from '../api/generated/client'
import type { ChatSessionState } from '../api/generated/schemas/chatSessionState'

export function ChatPage() {
  const [draft, setDraft] = useState('')
  const [messages, setMessages] = useState<Array<{ role: 'user' | 'assistant'; content: string }>>([])
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [_sessionState, setSessionState] = useState<ChatSessionState>('anonymous')
  const [isOtpModalOpen, setIsOtpModalOpen] = useState(false)
  const [otpError, setOtpError] = useState<string | null>(null)
  const [attemptsRemaining, setAttemptsRemaining] = useState<number | null>(null)
  const [toastMessage, setToastMessage] = useState<string | null>(null)
  const chatMutation = useChatApiChatPost()
  const verifyCodeMutation = useVerifyCodeApiAuthVerifyCodePost()

  const handleSubmit = async () => {
    const trimmedMessage = draft.trim()
    if (!trimmedMessage || chatMutation.isPending) return

    // Add user message to display
    setMessages((prev) => [...prev, { role: 'user', content: trimmedMessage }])
    setDraft('')

    try {
      const response = await chatMutation.mutateAsync({
        data: {
          prompt: trimmedMessage,
          session_id: sessionId || undefined,
        }
      })

      if (response.status === 200) {
        setMessages((prev) => [...prev, { role: 'assistant', content: response.data.reply }])
        setSessionId(response.data.session_id)
        setSessionState(response.data.state)

        // Open OTP modal if verification is required
        if (response.data.verification_required) {
          setIsOtpModalOpen(true)
          setOtpError(null)
          setAttemptsRemaining(null)
        }
      }
    } catch (error) {
      console.error('Chat request failed:', error)
      setMessages((prev) => [...prev, { role: 'assistant', content: 'Sorry, I encountered an error. Please try again.' }])
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

  return (
    <main className="relative min-h-screen overflow-hidden bg-[url('/secure-ship-background.jpeg')] bg-cover bg-fixed bg-center px-2 py-3 sm:px-4 sm:py-4">
      <div className="pointer-events-none absolute inset-0 bg-slate-950/38" aria-hidden="true" />

      <div className="relative mx-auto flex min-h-[calc(100svh-1.5rem)] w-full max-w-6xl flex-col gap-4 rounded-[2rem] border border-white/35 bg-slate-100/72 p-3 shadow-[0_30px_90px_rgba(15,23,42,0.34)] backdrop-blur-2xl sm:min-h-[calc(100svh-2rem)] sm:gap-5 sm:p-5">
        <ChatPanel
          draft={draft}
          messages={messages}
          isLoading={chatMutation.isPending}
          onDraftChange={setDraft}
          onSubmit={handleSubmit}
        />
      </div>

      <OtpVerificationModal
        isOpen={isOtpModalOpen}
        isSubmitting={verifyCodeMutation.isPending}
        errorMessage={otpError}
        helperMessage={null}
        remainingAttempts={attemptsRemaining}
        onSubmit={handleVerifyCode}
        onClose={handleCloseOtpModal}
      />

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

