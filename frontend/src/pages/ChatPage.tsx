import { useState } from 'react'
import { ChatInput } from '../components/ChatInput'
import { ChatMessageList, type ChatMessage } from '../components/ChatMessageList'

const echoResponse = (message: string) => `You asked: ${message}`

export function ChatPage() {
  const [draft, setDraft] = useState('')
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const hasMessages = messages.length > 0

  const handleSubmit = () => {
    const trimmedMessage = draft.trim()

    if (!trimmedMessage) {
      return
    }

    setMessages((currentMessages) => [
      ...currentMessages,
      {
        id: currentMessages.length * 2 + 1,
        role: 'user',
        content: trimmedMessage,
      },
      {
        id: currentMessages.length * 2 + 2,
        role: 'assistant',
        content: echoResponse(trimmedMessage),
      },
    ])
    setDraft('')
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
              <ChatMessageList messages={messages} />
              <div className="mt-6 w-full">
                <ChatInput value={draft} onChange={setDraft} onSubmit={handleSubmit} />
              </div>
            </>
          ) : (
            <div className="mx-auto w-full max-w-3xl">
              <ChatInput value={draft} onChange={setDraft} onSubmit={handleSubmit} />
            </div>
          )}
        </section>
      </div>
    </main>
  )
}