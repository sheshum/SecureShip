import { useState } from 'react'
import { ChatPanel } from '../components/ChatPanel'
import { useChatApiChatPost } from '../api/generated/client'

export function ChatPage() {
  const [draft, setDraft] = useState('')
  const [messages, setMessages] = useState<Array<{ role: 'user' | 'assistant'; content: string }>>([])
  const chatMutation = useChatApiChatPost()

  const handleSubmit = async () => {
    const trimmedMessage = draft.trim()
    if (!trimmedMessage || chatMutation.isPending) return

    // Add user message to display
    setMessages((prev) => [...prev, { role: 'user', content: trimmedMessage }])
    setDraft('')

    try {
      const response = await chatMutation.mutateAsync({ data: { prompt: trimmedMessage } })
      
      // Add assistant response
      if (response.status === 200) {
        setMessages((prev) => [...prev, { role: 'assistant', content: response.data.reply }])
      }
    } catch (error) {
      console.error('Chat request failed:', error)
      setMessages((prev) => [...prev, { role: 'assistant', content: 'Sorry, I encountered an error. Please try again.' }])
    }
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
    </main>
  )
}
