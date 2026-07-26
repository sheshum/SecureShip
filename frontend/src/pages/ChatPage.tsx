import { useRef, useState } from 'react'
import { ChatInput } from '../components/ChatInput'
import { ChatMessageList, type ChatMessage } from '../components/ChatMessageList'
import { useChatStream } from '../features/chat/useChatStream'
import type { ChatRequest } from '../api/generated/schemas'

function toChatRequest(messages: ChatMessage[]): ChatRequest {
  return {
    messages: messages.map((message) => ({
      role: message.role,
      content: message.content,
    })),
  }
}

export function ChatPage() {
  const [draft, setDraft] = useState('')
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const nextMessageIdRef = useRef(1)
  const { isStreaming, error, send, cancel } = useChatStream()
  const hasMessages = messages.length > 0

  const handleSubmit = async () => {
    const trimmedMessage = draft.trim()

    if (!trimmedMessage || isStreaming) {
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

    setMessages((currentMessages) => [
      ...currentMessages,
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
    ])
    setDraft('')

    const request = toChatRequest(requestMessages)

    void send(request, {
      onToken: (token) => {
        setMessages((currentMessages) =>
          currentMessages.map((message) =>
            message.id === assistantMessageId
              ? { ...message, content: `${message.content}${token}` }
              : message,
          ),
        )
      },
      onError: (message) => {
        setMessages((currentMessages) =>
          currentMessages.map((chatMessage) =>
            chatMessage.id === assistantMessageId
              ? { ...chatMessage, content: message }
              : chatMessage,
          ),
        )
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
    setMessages((currentMessages) => {
      const lastMessage = currentMessages.at(-1)

      if (!lastMessage || lastMessage.role !== 'assistant' || lastMessage.content.trim().length > 0) {
        return currentMessages
      }

      return currentMessages.slice(0, -1)
    })
  }

  return (
    <main className="min-h-screen bg-[url('/secure-ship-background.jpeg')] bg-cover bg-fixed bg-center px-4 py-6 sm:px-6 sm:py-8">
      <div className="mx-auto flex min-h-[calc(100svh-3rem)] w-full max-w-5xl">
        <section
          className={[
            'flex w-full flex-col rounded-[2rem] border border-white/60 bg-white/70 p-4 shadow-[0_24px_80px_rgba(15,23,42,0.14)] backdrop-blur-xl sm:p-6',
            hasMessages ? 'h-[min(80svh,760px)]' : 'min-h-[calc(100svh-3rem)] justify-center',
          ].join(' ')}
        >
          {hasMessages ? (
            <>
              <ChatMessageList messages={messages} isStreaming={isStreaming} />
              <div className="mt-6 w-full">
                <ChatInput
                  value={draft}
                  onChange={handleChange}
                  onSubmit={handleSubmit}
                  onCancel={handleCancel}
                  isStreaming={isStreaming}
                />
              </div>
            </>
          ) : (
            <div className="mx-auto w-full max-w-3xl">
              <ChatInput
                value={draft}
                onChange={handleChange}
                onSubmit={handleSubmit}
                onCancel={handleCancel}
                isStreaming={isStreaming}
              />
            </div>
          )}
          {error ? <p className="mt-4 text-sm text-red-600">{error}</p> : null}
        </section>
      </div>
    </main>
  )
}