import { useEffect, useRef, useState } from 'react'
import { type ChatMessage } from '../components/ChatMessageList'
import { ChatPanel } from '../components/ChatPanel'
import { SideBar } from '../components/SideBar'
import { useChatStream } from '../features/chat/useChatStream'
import { useChatSessions } from '../features/chat/useChatSessions'
import type { ChatRequest } from '../api/generated/schemas'

function toChatRequest(sessionId: string | null, messages: ChatMessage[]): ChatRequest {
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
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)
  const nextMessageIdRef = useRef(1)
  const { isStreaming, error, send, cancel } = useChatStream()
  const {
    sessions,
    selectedSessionId,
    selectedMessages,
    isLoadingSelectedSession,
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
    bindEmptySessionToCreatedSession,
    hasPersistedSessions,
  } = useChatSessions({ isStreaming })

  useEffect(() => {
    const highestMessageId = selectedMessages.reduce((maxId, message) => Math.max(maxId, message.id), 0)
    if (highestMessageId >= nextMessageIdRef.current) {
      nextMessageIdRef.current = highestMessageId + 1
    }
  }, [selectedMessages])

  const handleSubmit = async () => {
    const trimmedMessage = draft.trim()

    if (!trimmedMessage || isStreaming) {
      return
    }

    const currentSessionId = await ensureSession()

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

    const request = toChatRequest(currentSessionId, requestMessages)
    let streamSessionId: string | null = currentSessionId

    void send(request, {
      onSession: (sessionId) => {
        if (streamSessionId === null) {
          bindEmptySessionToCreatedSession(sessionId)
        }

        streamSessionId = sessionId
        void invalidateSessions()
      },
      onToken: (token) => {
        appendAssistantToken(streamSessionId, assistantMessageId, token)
      },
      onError: (message) => {
        setAssistantError(streamSessionId, assistantMessageId, message)
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
  const activeSessionTitle = sessions.find((session) => session.id === selectedSessionId)?.title ?? null

  const handleSelectSession = (sessionId: string) => {
    selectSession(sessionId)
    setIsSidebarOpen(false)
  }

  return (
    <main className="relative min-h-screen overflow-hidden bg-[url('/secure-ship-background.jpeg')] bg-cover bg-fixed bg-center px-2 py-3 sm:px-4 sm:py-4">
      <div className="pointer-events-none absolute inset-0 bg-slate-950/38" aria-hidden="true" />

      <div className="relative mx-auto flex min-h-[calc(100svh-1.5rem)] w-full max-w-6xl flex-col gap-4 rounded-[2rem] border border-white/35 bg-slate-100/72 p-3 shadow-[0_30px_90px_rgba(15,23,42,0.34)] backdrop-blur-2xl sm:min-h-[calc(100svh-2rem)] sm:gap-5 sm:p-5 lg:flex-row">
        <div className="flex items-center justify-between rounded-2xl border border-white/65 bg-white/80 px-3 py-2.5 shadow-sm lg:hidden">
          <button
            type="button"
            onClick={() => setIsSidebarOpen(true)}
            className="inline-flex min-h-11 items-center justify-center rounded-xl border border-slate-300 bg-white px-3.5 text-sm font-medium text-slate-800 transition hover:border-sky-300 hover:bg-sky-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500 focus-visible:ring-offset-2"
            aria-haspopup="dialog"
            aria-expanded={isSidebarOpen}
            aria-controls="mobile-sessions-drawer"
          >
            Sessions
          </button>
          <p className="max-w-[60%] truncate text-sm font-semibold text-slate-800">{activeSessionTitle ?? 'New chat'}</p>
        </div>

        <SideBar
          sessions={sessions}
          selectedSessionId={selectedSessionId}
          isStreaming={isStreaming}
          isLoadingSessions={isLoadingSessions}
          isCreatingSession={isCreatingSession}
          isDeletingSession={isDeletingSession}
          hasPersistedSessions={hasPersistedSessions}
          onCreateSession={() => {
            void handleCreateSession()
          }}
          onDeleteSession={() => {
            void handleDeleteSession()
          }}
          onSelectSession={handleSelectSession}
          className="hidden lg:flex"
        />

        <ChatPanel
          messages={selectedMessages}
          sessionTitle={activeSessionTitle}
          draft={draft}
          isStreaming={isStreaming}
          isLoadingHistory={isLoadingSelectedSession}
          errorMessage={activeError}
          isRefreshingSessions={isRefetchingSessions}
          onDraftChange={handleChange}
          onSubmit={handleSubmit}
          onCancel={handleCancel}
        />
      </div>

      {isSidebarOpen ? (
        <div className="fixed inset-0 z-40 lg:hidden" role="dialog" aria-modal="true" id="mobile-sessions-drawer">
          <button
            type="button"
            className="absolute inset-0 bg-slate-950/45"
            onClick={() => setIsSidebarOpen(false)}
            aria-label="Close sessions panel"
          />
          <div className="absolute inset-y-3 left-3 w-[min(88vw,360px)]">
            <SideBar
              sessions={sessions}
              selectedSessionId={selectedSessionId}
              isStreaming={isStreaming}
              isLoadingSessions={isLoadingSessions}
              isCreatingSession={isCreatingSession}
              isDeletingSession={isDeletingSession}
              hasPersistedSessions={hasPersistedSessions}
              onCreateSession={() => {
                void handleCreateSession()
                setIsSidebarOpen(false)
              }}
              onDeleteSession={() => {
                void handleDeleteSession()
              }}
              onSelectSession={handleSelectSession}
              className="h-full"
              onRequestClose={() => setIsSidebarOpen(false)}
            />
          </div>
        </div>
      ) : null}
    </main>
  )
}