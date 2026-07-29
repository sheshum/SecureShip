import { useCallback, useState } from 'react'
import { useVerifyCodeApiVerifyCodePost } from '../../api/generated/client'
import type { VerifyCodeResponse } from '../../api/generated/schemas'
import type { ChatSseEvent } from '../../api/chatStream'

export function useAuthFlow(sessionId: string | null) {
  const [authRequiredMessage, setAuthRequiredMessage] = useState<string | null>(null)
  const [authInfoMessage, setAuthInfoMessage] = useState<string | null>(null)
  const [codeModalHint, setCodeModalHint] = useState(false)
  const [otpModalOpen, setOtpModalOpen] = useState(false)
  const [otpHelperMessage, setOtpHelperMessage] = useState<string | null>(null)
  const [otpErrorMessage, setOtpErrorMessage] = useState<string | null>(null)
  const [otpRemainingAttempts, setOtpRemainingAttempts] = useState<number | null>(null)
  const [pendingTurnId, setPendingTurnId] = useState<string | null>(null)

  const verifyCodeMutation = useVerifyCodeApiVerifyCodePost()

  const reset = useCallback(() => {
    setAuthRequiredMessage(null)
    setAuthInfoMessage(null)
    setCodeModalHint(false)
    setOtpModalOpen(false)
    setOtpErrorMessage(null)
    setOtpHelperMessage(null)
    setOtpRemainingAttempts(null)
  }, [])

  const onAuthState = useCallback(
    (event: Extract<ChatSseEvent, { type: 'auth_state' }>) => {
      if (event.state === 'verified') reset()
    },
    [reset],
  )

  const onAuthRequired = useCallback((event: Extract<ChatSseEvent, { type: 'auth_required' }>) => {
    setAuthRequiredMessage(event.message)
    setPendingTurnId(event.pending_turn_id ?? null)
  }, [])

  const onShowCodeModal = useCallback((event: Extract<ChatSseEvent, { type: 'show_code_modal' }>) => {
    if (!event.open) return
    setOtpModalOpen(true)
    setCodeModalHint(true)
    setAuthInfoMessage('Verification code sent. Enter the code to continue.')
    setOtpHelperMessage('Verification code sent. Enter the code to continue.')
  }, [])

  const handleVerifyCode = useCallback(
    async (code: string, onVerified: (resolvedTurnId: string | null) => void) => {
      if (!sessionId) return
      setOtpErrorMessage(null)

      try {
        // customFetcher returns raw JSON; the orval discriminated-union type doesn't match runtime.
        const payload = (await verifyCodeMutation.mutateAsync({ data: { session_id: sessionId, code } })) as unknown as VerifyCodeResponse

        setOtpHelperMessage(payload.message)
        setOtpRemainingAttempts(payload.remaining_attempts ?? null)

        if (payload.verified) {
          reset()
          onVerified(payload.pending_turn_id ?? pendingTurnId)
          return
        }

        setOtpErrorMessage(payload.message)
        if (payload.state === 'collecting_identity') {
          setOtpModalOpen(false)
        }
      } catch (error) {
        const message = error instanceof Error ? error.message : 'Unable to verify code right now. Please try again.'
        setOtpErrorMessage(message)
      }
    },
    [sessionId, verifyCodeMutation, reset, pendingTurnId],
  )

  const closeModal = useCallback(() => {
    setOtpModalOpen(false)
    setOtpErrorMessage(null)
    setOtpHelperMessage(null)
    setOtpRemainingAttempts(null)
  }, [])

  return {
    pendingTurnId,
    authRequiredMessage,
    // When the code modal hint is active, always show a contextual message.
    authInfoMessage: codeModalHint ? (authInfoMessage ?? 'A verification code is ready for this session.') : authInfoMessage,
    otpModalOpen,
    otpHelperMessage,
    otpErrorMessage,
    otpRemainingAttempts,
    isVerifyPending: verifyCodeMutation.isPending,
    onAuthState,
    onAuthRequired,
    onShowCodeModal,
    handleVerifyCode,
    closeModal,
  }
}
