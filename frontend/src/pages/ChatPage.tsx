import { useRef, useState } from 'react'
import { type ChatMessage } from '../components/ChatMessageList'
import { ChatPanel } from '../components/ChatPanel'
import { SideBar } from '../components/SideBar'
import { useChatStream } from '../features/chat/useChatStream'
import { useChatSessions } from '../features/chat/useChatSessions'
import type { ChatRequest } from '../api/generated/schemas'

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
  const nextMessageIdRef = useRef(1)
  const { isStreaming, error, send, cancel } = useChatStream()
  const {
    sessions,
    selectedSessionId,
    selectedMessages,
    sessionError,
    isLoadingSessions,
    isRefetchingSessions,
    isCreatingSession,
    isDeletingSession,
    ensureSession,
    createNewSession,
    deleteSelectedSession,
    selectSession,
    addPendingTurn,
    appendAssistantToken,
    setAssistantError,
    removeTrailingEmptyAssistant,
    invalidateSessions,
    clearSessionError,
  } = useChatSessions({ isStreaming })

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
      ...selectedMessages,
      {
        id: userMessageId,
        role: 'user' as const,
        content: trimmedMessage,
      },
    ]

    addPendingTurn(
      currentSessionId,
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

    await invalidateSessions()

    const request = toChatRequest(currentSessionId, requestMessages)

    void send(request, {
      onToken: (token) => {
        appendAssistantToken(currentSessionId, assistantMessageId, token)
      },
      onError: (message) => {
        setAssistantError(currentSessionId, assistantMessageId, message)
      },
      onDone: () => {
        void invalidateSessions()
      },
    })
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

  const handleCreateSession = async () => {
    setDraft('')
    clearSessionError()
    await createNewSession()
  }

  const handleDeleteSession = async () => {
    await deleteSelectedSession()
  }

  const activeError = sessionError ?? error

  return (
    <main className="min-h-screen bg-[url('/secure-ship-background.jpeg')] bg-cover bg-fixed bg-center px-4 py-5 sm:px-6 sm:py-8">
      <div className="mx-auto flex min-h-[calc(100svh-2.5rem)] w-full max-w-6xl gap-4 rounded-[2rem] border border-white/50 bg-slate-100/55 p-3 shadow-[0_30px_90px_rgba(15,23,42,0.28)] backdrop-blur-2xl sm:gap-5 sm:p-5">
        <SideBar
          sessions={sessions}
          selectedSessionId={selectedSessionId}
          isStreaming={isStreaming}
          isLoadingSessions={isLoadingSessions}
          isCreatingSession={isCreatingSession}
          isDeletingSession={isDeletingSession}
          onCreateSession={() => {
            void handleCreateSession()
          }}
          onDeleteSession={() => {
            void handleDeleteSession()
          }}
          onSelectSession={selectSession}
        />

        <ChatPanel
          messages={selectedMessages}
          draft={draft}
          isStreaming={isStreaming}
          errorMessage={activeError}
          isRefreshingSessions={isRefetchingSessions}
          onDraftChange={handleChange}
          onSubmit={handleSubmit}
          onCancel={handleCancel}
        />
      </div>
    </main>
  )
}